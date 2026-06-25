"""
agent.py — Phase 4+: LangGraph ReAct multi-step agent for Blinsky.

Builds a StateGraph with nodes: think → tool → respond → END.
Supports up to 5 iterations to prevent runaway loops.
"""
from __future__ import annotations

import os
from typing import Annotated, Optional, TypedDict
import operator

from dotenv import load_dotenv
from langchain_ollama import OllamaLLM
from langgraph.graph import StateGraph, END

from blinsky.processors.ollama_processor import _strip_tool_tags, _extract_json
from blinsky.processors.tool_processor import ToolProcessor

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME      = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
MAX_ITERATIONS  = 5

# ── State ─────────────────────────────────────────────────────────────────────

class BlinskyState(TypedDict):
    user_message:   str
    messages:       Annotated[list[str], operator.add]   # accumulated context
    tool_calls:     Annotated[list[dict], operator.add]  # tool calls made so far
    final_response: str
    iteration:      int
    done:           bool


# ── Node implementations ───────────────────────────────────────────────────────

_AGENT_SYSTEM = """You are Blinsky, a helpful AI assistant with access to tools.

TOOLS AVAILABLE:
  web_search(query)            — search the internet for current information
  write_file(filename,content) — write a local file
  read_file(filename)          — read a local file

TOOL CALL FORMAT (use EXACTLY this):
  <tool>{"name": "web_search", "args": {"query": "your query"}}</tool>

RULES:
  1. Think step by step. Show your reasoning before calling a tool.
  2. If the user asks for news, facts, or current info: ALWAYS call web_search first.
  3. After a tool result, summarize it clearly for the user.
  4. When you have enough information, respond with: FINAL: <your answer>
  5. Never use <tool> unless you're actually calling a tool.
  6. Stop after at most 5 tool calls."""


def _build_llm(keys: Optional[dict] = None) -> OllamaLLM:
    keys = keys or {}
    url = keys.get("ollama_url") or OLLAMA_BASE_URL
    model = keys.get("ollama_model") or MODEL_NAME
    return OllamaLLM(model=model, base_url=url, temperature=0.1)


def think_node(state: BlinskyState) -> BlinskyState:
    """LLM decides next action: tool call or final answer."""
    keys = state.get("keys")
    llm   = _build_llm(keys)
    tavily_key = (keys or {}).get("tavily_key")
    tool_proc = ToolProcessor(tavily_key=tavily_key)

    # Build context from accumulated messages
    context = "\n".join(state["messages"][-8:])  # last 8 context lines
    prompt = (
        f"System: {_AGENT_SYSTEM}\n\n"
        f"Context so far:\n{context}\n\n"
        f"User request: {state['user_message']}\n"
        f"Iteration: {state['iteration'] + 1}/{MAX_ITERATIONS}\n"
        "Assistant: "
    )

    try:
        raw = llm.invoke(prompt)
    except Exception as exc:
        return {
            **state,
            "final_response": f"I'm having trouble connecting to Ollama: {exc}",
            "done": True,
        }

    print(f"[Agent] think_node output: {repr(raw[:120])}")

    # Check for FINAL: prefix
    if "FINAL:" in raw:
        final = raw.split("FINAL:", 1)[1].strip()
        final = _strip_tool_tags(final)
        return {
            **state,
            "messages": [f"Agent: {raw}"],
            "final_response": final,
            "done": True,
        }

    # Check for tool call
    if "<tool" in raw:
        tool_start = raw.find("<tool")
        after      = raw[tool_start:]
        brace_pos  = after.find("{")
        tool_call  = _extract_json(after[brace_pos:]) if brace_pos != -1 else None

        if tool_call and "name" in tool_call:
            result = tool_proc.execute(tool_call)
            print(f"[Agent] tool call: {tool_call.get('name')} → {repr(result[:80])}")
            new_iter = state["iteration"] + 1
            return {
                **state,
                "messages":    [f"Agent thought: {_strip_tool_tags(raw)}", f"Tool result ({tool_call['name']}): {result}"],
                "tool_calls":  [tool_call],
                "iteration":   new_iter,
                "done":        new_iter >= MAX_ITERATIONS,
                "final_response": result if new_iter >= MAX_ITERATIONS else "",
            }

    # No tool call, no FINAL — treat as final answer
    clean = _strip_tool_tags(raw).strip()
    return {
        **state,
        "messages": [f"Agent: {raw}"],
        "final_response": clean or "I wasn't able to generate a response.",
        "done": True,
    }


def respond_node(state: BlinskyState) -> BlinskyState:
    """Generate final user-facing response when loop is done."""
    if state.get("final_response"):
        return state

    keys = state.get("keys")
    llm = _build_llm(keys)
    context = "\n".join(state["messages"][-6:])
    prompt = (
        f"System: {_AGENT_SYSTEM}\n\n"
        f"You have gathered the following information:\n{context}\n\n"
        f"User request: {state['user_message']}\n\n"
        "Now give a clear, concise final answer. Do NOT use any <tool> tags.\n"
        "Assistant: "
    )
    try:
        raw = llm.invoke(prompt)
        clean = _strip_tool_tags(raw).strip()
        return {**state, "final_response": clean or "I wasn't able to generate a response."}
    except Exception as exc:
        return {**state, "final_response": f"Error generating response: {exc}"}


# ── Routing ───────────────────────────────────────────────────────────────────

def should_continue(state: BlinskyState) -> str:
    if state.get("done", False):
        return "respond"
    return "think"


# ── Graph builder ─────────────────────────────────────────────────────────────

def build_agent_graph() -> StateGraph:
    graph = StateGraph(BlinskyState)
    graph.add_node("think",   think_node)
    graph.add_node("respond", respond_node)

    graph.set_entry_point("think")
    graph.add_conditional_edges("think", should_continue, {"think": "think", "respond": "respond"})
    graph.add_edge("respond", END)

    return graph.compile()


# ── Public API ────────────────────────────────────────────────────────────────

def run_agent(
    user_message: str,
    history: Optional[list[dict]] = None,
    keys: Optional[dict] = None,
) -> dict:
    """
    Run the ReAct agent on a user message.

    Returns:
        {
            "reply":      str,       # final answer
            "steps":      list[str], # accumulated context/reasoning
            "tool_calls": list[dict] # all tools called
        }
    """
    history = history or []
    history_ctx = [f"User: {t['user']}\nBlinsky: {t['assistant']}" for t in history[-5:]]

    initial_state: BlinskyState = {
        "user_message":   user_message,
        "messages":       history_ctx,
        "tool_calls":     [],
        "final_response": "",
        "iteration":      0,
        "done":           False,
        "keys":           keys or {},
    }

    graph = build_agent_graph()
    final_state = graph.invoke(initial_state)

    return {
        "reply":      final_state.get("final_response", "No response generated."),
        "steps":      final_state.get("messages", []),
        "tool_calls": final_state.get("tool_calls", []),
    }
