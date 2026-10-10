# RedOps

RedOps is a defensive AI-agent security analysis platform. It allows security teams to run and analyze predefined scenarios against simulated AI agents to detect policy violations, missing authorization checks, and insecure tool handling.

## Features
- **Scenario Manager:** Create and manage security scenarios.
- **Security Analyzer:** Detect missing authorization checks.
- **Remediation Assistant:** Get actionable, code-level recommendations.
- **Dashboard:** A minimalist red-and-white React interface.

## Tech Stack
- Backend: Python, FastAPI, SQLite
- Frontend: React, Vite, Tailwind CSS, TypeScript

## Setup

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Entire & Neatlogs Integration
- **neatlogs:** Included in `backend/main.py`. Set your `NEATLOGS_API_KEY` environment variable.
- **Entire:** We use the Entire CLI. Install it and configure the repository context as per Entire's standard docs.
