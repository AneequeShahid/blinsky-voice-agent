# Blinsky Deployment Guide

Blinsky can be run entirely locally or deployed as a cloud-hosted, stateless application with dynamic key authorization.

---

## 1. Local Deployment

### Prerequisites
- Python 3.11+
- [Ollama](https://ollama.com/) running locally with the target model (e.g., `qwen2.5:7b` or `llama3.2`).
- A [Tavily API Key](https://tavily.com/) for web search tools.

### Installation
1. Clone the repository.
2. Initialize virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate   # On Windows
   source venv/bin/activate  # On Linux/macOS
   ```
3. Install both core and local dependencies:
   ```bash
   pip install -r requirements.txt -r requirements-local.txt
   ```
4. Copy `.env.example` to `.env` and fill in the keys:
   ```bash
   cp .env.example .env
   ```

### Running Locally
- **Local Web Backend**:
  ```bash
  python -m uvicorn api.app:app --port 9001
  ```
- **Local Web Frontend**: Open [ui/web/index.html](file:///C:/Users/Aneeque/blinsky-voice-agent/ui/web/index.html) in your browser.
- **Voice Agent (CLI mode)**:
  ```bash
  python main.py
  ```
- **Wake Word Agent (CLI mode)**:
  ```bash
  python main.py --wake
  ```

---

## 2. Cloud Deployment (Stateless Mode)

In cloud mode, the backend server handles requests statelessly. Keys and conversation history are managed on the client side, allowing the backend to scale easily.

### A. Deploy Backend to Railway
1. Push your repository to GitHub.
2. Log in to [Railway](https://railway.app/) and create a new project.
3. Select **Deploy from GitHub repo** and select `blinsky-voice-agent`.
4. Railway will automatically detect the configuration:
   - It will build the environment using Nixpacks (`nixpacks.toml` and `requirements.txt`).
   - It will run the start command specified in the `Procfile` (`uvicorn api.app:app --host 0.0.0.0 --port $PORT`).
5. Under service settings, generate a domain (your backend endpoint URL).

### B. Deploy Frontend to Vercel
1. Log in to [Vercel](https://vercel.com/) and import your GitHub repository.
2. Vercel will automatically read `vercel.json` and deploy the project. The configuration handles url rewriting, routing all traffic directly to the static `ui/web` directory.
3. Deploy the application to get your live frontend URL.

---

## 3. First-Time Setup & Usage

When you open the frontend (deployed on Vercel or locally), if keys are missing in `localStorage`, a **Settings Modal** will appear automatically.

Configure the following:
1. **Backend URL**: The deployed URL of your Railway backend service (e.g., `https://blinsky-backend.up.railway.app`).
2. **Tavily API Key**: Your personal Tavily search API key.
3. **Ollama Server URL**: The address of your Ollama instance (e.g., local URL `http://localhost:11434` if Ollama is running on your machine and backend CORS is enabled, or a public address mapped via `ngrok`/`localtunnel`).
4. **Ollama Model**: The model you pulled (e.g. `qwen2.5:7b`).

Click **Test Connection** to validate keys, then click **Save Settings** to persist config client-side.
