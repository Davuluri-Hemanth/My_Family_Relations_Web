# My Family Relations — Global Web App

Production-oriented FastAPI + MongoDB Atlas web application for the My Family Relations project.

## Architecture

Browser → HTTPS/Render → FastAPI → MongoDB Atlas

MongoDB credentials and JWT signing secrets stay server-side as Render environment variables.

## Main files

- `backend/main.py` — FastAPI API and SPA server
- `frontend/` — browser interface
- `Dockerfile` — production container
- `render.yaml` — Render Blueprint configuration
- `.env.example` — local configuration template; contains no real secrets
- `scripts_generate_admin_hash.py` — creates the bcrypt admin password hash
- `DEPLOY_RENDER.md` — complete MongoDB Atlas + Render deployment guide

## Quick start

1. Copy `.env.example` to `.env`.
2. Put your MongoDB Atlas URI in `MONGO_URI`.
3. Generate an admin bcrypt hash with `python scripts_generate_admin_hash.py`.
4. Put the hash in `ADMIN_PASSWORD_HASH`.
5. Run the application locally:

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

6. Open `http://127.0.0.1:8000/`.

## Production deployment

Read **`DEPLOY_RENDER.md`** from start to finish. It covers secret handling, Atlas database users and network access, Docker, GitHub, Render environment variables, health checks, custom domains, and post-deployment testing.

Do not commit `.env` or any file containing real MongoDB credentials, JWT secrets, or plaintext passwords.
