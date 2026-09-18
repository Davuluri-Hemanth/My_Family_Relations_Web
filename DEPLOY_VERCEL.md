# My Family Relations — Vercel deployment (no credit card path)

This version is adapted for Vercel Hobby and keeps the MongoDB credentials on the server side.
Vercel serves the HTML/CSS/JS files and runs FastAPI under `/api/*`.

## 1. GitHub repository

Upload the contents of this folder to your GitHub repository. Keep this structure:

```
api/index.py
backend/main.py
frontend/index.html
frontend/app.js
frontend/style.css
vercel.json
requirements.txt
.env.example
.gitignore
.vercelignore
README.md
scripts_generate_admin_hash.py
```

Do NOT upload `.env` or any real secrets.

## 2. MongoDB Atlas

Create/use a dedicated MongoDB database user for this application. Give it only the permissions required for the `Family_Relations` database.

In Atlas Network Access, allow the Vercel deployment to reach the cluster according to your Atlas networking policy. For a first test, Atlas may require a broader temporary rule; tighten it for production when you have the appropriate outbound-network setup.

Collections used by this app:

- `persons`
- `relationships`
- `users`
- `counters` (created automatically for person IDs)

## 3. Generate the admin password hash

On your own computer:

```bash
python scripts_generate_admin_hash.py
```

Enter the admin password. Copy the resulting bcrypt hash only.

## 4. Deploy to Vercel

1. Open https://vercel.com/new
2. Sign in with GitHub.
3. Import `Davuluri-Hemanth/My_Family_Relations_Web` (or the repository containing these files).
4. Leave Framework Preset as the detected/default option; this project uses `vercel.json` and Python functions.
5. Before deploying, open Environment Variables.
6. Add all variables listed below.
7. Deploy.

## 5. Environment variables

Set these in Vercel, not GitHub:

```
MONGO_URI=your Atlas connection string
MONGO_DB=Family_Relations
MONGO_PERSONS_COLLECTION=persons
MONGO_RELATIONS_COLLECTION=relationships
MONGO_USERS_COLLECTION=users
JWT_SECRET=long-random-secret
JWT_EXPIRE_MINUTES=720
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=your-bcrypt-hash
MAX_UPLOAD_MB=5
ENABLE_API_DOCS=false
CORS_ORIGINS=
```

Set them for **Production** (and Preview if you want preview deployments to work).

## 6. Test

After deployment, open the Vercel URL in Chrome.

Health check:

```
https://YOUR-PROJECT.vercel.app/api/health
```

A healthy deployment should return JSON containing `"ok": true`.

## 7. MongoDB IP/network note

Vercel functions can execute from changing infrastructure. Do not permanently hard-code an assumed single Vercel IP address into Atlas. Use the networking approach supported by your Atlas plan and Vercel setup, and use the least-privilege database user.

## 8. Security

- Rotate any MongoDB password that was ever embedded in the original Tkinter source.
- Never commit `.env`.
- Never put `MONGO_URI` in browser JavaScript.
- Keep `JWT_SECRET` server-side.
- Keep the admin bcrypt hash server-side.
- Keep the Atlas database user separate from your personal Atlas account.
- Use HTTPS (Vercel provides it for the deployed URL).

## 9. Important free-plan limitation

Vercel Hobby is intended for personal/non-commercial use and has usage limits. Check Vercel's current plan terms before using the application commercially.
