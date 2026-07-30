# Wasl — Control Tower UI

React + Vite frontend for the Wasl agentic logistics control tower.
Talks to the FastAPI backend at http://localhost:8000.

## Setup

1. Install dependencies:
   npm install

2. Copy the env file and set your API key (must match the backend's API_KEY):
   cp .env.example .env
   # edit .env, set VITE_API_KEY=<your key>

3. Make sure the backend is running:
   # in the wasl/ project, in another terminal:
   uvicorn app.main:app --reload

4. Start the frontend:
   npm run dev

Open http://localhost:5173

## How it connects

The Vite dev server proxies /api/* to the backend on :8000 (see vite.config.js),
so there are no CORS issues in development and the frontend never hard-codes the
backend URL.
