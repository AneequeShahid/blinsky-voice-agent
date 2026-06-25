"""
ToolProcessor: execute tool calls (search, file read/write) from OllamaProcessor.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict

from blinsky.tools.search import web_search
from blinsky.tools.files import read_file, write_file

TOOLS = {
    "web_search": web_search,
    "write_file": write_file,
    "read_file": read_file,
}


class ToolProcessor:
    """Dispatches tool calls from OllamaProcessor and returns formatted results."""

    def __init__(self, tavily_key: Optional[str] = None) -> None:
        self.tavily_key = tavily_key

    def execute(self, tool_call: Dict[str, Any]) -> str:
        name = tool_call.get("name")
        args = tool_call.get("args", {})
        func = TOOLS.get(name)
        if func is None:
            return f"Unknown tool: {name}"

        try:
            if name == "web_search":
                result = func(**args, tavily_key=self.tavily_key)
            else:
                result = func(**args)
            if not isinstance(result, str):
                result = json.dumps(result, ensure_ascii=False)
            return result
        except Exception as exc:
            return f"Tool error: {exc}"
