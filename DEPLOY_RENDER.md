# Production deployment: My Family Relations on Render + MongoDB Atlas

This project is designed so the browser never receives the MongoDB URI, MongoDB password, or JWT signing secret. The FastAPI server talks to MongoDB Atlas using server-side environment variables.

## 1. Rotate the old MongoDB password first

The original desktop Python application contained a MongoDB connection credential. Treat that credential as exposed and rotate it in MongoDB Atlas before deploying this web application.

Create a **dedicated database user for the web application**. Give it only the database permissions the application needs (normally read/write on `Family_Relations`). Do not use your Atlas account password as the application password.

MongoDB Atlas requires the application's source IP/network to be present in the project's IP access list. citeturn0search3turn0search6

## 2. Prepare MongoDB Atlas

In Atlas:

1. Open your `Family_Relations` project/cluster.
2. Create a database user, for example `family_web_app`.
3. Give that database user read/write access to the `Family_Relations` database.
4. Go to **Network Access / IP Access List**.
5. Add the outbound IP addresses that your Render service will use, if your Render plan/network setup provides stable egress IPs.
6. If your Render setup does not provide fixed egress IPs, use the Atlas network configuration appropriate for your plan/provider. A temporary `0.0.0.0/0` entry can make a first connection test possible, but it allows connections from any IPv4 address and should not be treated as the preferred production restriction. MongoDB documents IP allowlists and warns about `/0` ranges. citeturn0search6turn0search4
7. Confirm your existing collections are named:
   - `persons`
   - `relationships`
   - `users` (optional for future account expansion)

The application's default database is `Family_Relations` and the default collections are `persons`, `relationships`, and `users`.

## 3. Generate the admin password hash

Do this on your own computer. Never put the plaintext admin password in GitHub.

### Windows PowerShell

```powershell
cd My_Family_Relations_Web
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts_generate_admin_hash.py
```

Copy the printed bcrypt value. It will look similar to:

```text
$2b$12$...
```

Use the complete value as `ADMIN_PASSWORD_HASH` in Render.

### Linux/macOS

```bash
cd My_Family_Relations_Web
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts_generate_admin_hash.py
```

## 4. Generate a strong JWT secret

A convenient local command is:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Do not commit this value to GitHub. Render can generate `JWT_SECRET` automatically from the included `render.yaml`, or you can set your own secret in the Render dashboard. Render recommends environment variables for secrets rather than committing credentials to source control. citeturn0search2

## 5. Create the MongoDB URI

In Atlas, choose **Connect → Drivers**, then copy the application connection string.

Use a value like:

```text
mongodb+srv://family_web_app:YOUR_PASSWORD@YOUR_CLUSTER.mongodb.net/?retryWrites=true&w=majority&appName=MyFamilyRelations
```

If the password contains special URL characters, percent-encode the password before putting it in the URI.

## 6. Put the project in GitHub

Create a **private** GitHub repository if you want the source to remain private.

From the project directory:

```bash
git init
git add .
git commit -m "Production deployment setup"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

Before pushing, verify that `.env` is not tracked:

```bash
git status
```

The repository contains `.env.example`, but not your real `.env`.

## 7. Deploy to Render

Render supports Docker-based web services and can build the Dockerfile directly from your Git repository. A Render web service must listen on `0.0.0.0`; this project does that and uses Render's `PORT` value. citeturn0search0turn0search1

### Dashboard method

1. Sign in to Render.
2. Select **New → Web Service**.
3. Connect your GitHub account.
4. Select the repository.
5. Set the runtime/environment to **Docker**.
6. Render will detect the `Dockerfile`.
7. Choose your region and plan.
8. Set the health check path to:

```text
/api/health
```

9. Add the secret environment variables:

| Key | Value |
|---|---|
| `MONGO_URI` | Your Atlas connection string |
| `ADMIN_PASSWORD_HASH` | The bcrypt hash generated above |

10. Add/confirm these non-secret variables:

| Key | Value |
|---|---|
| `MONGO_DB` | `Family_Relations` |
| `MONGO_PERSONS_COLLECTION` | `persons` |
| `MONGO_RELATIONS_COLLECTION` | `relationships` |
| `MONGO_USERS_COLLECTION` | `users` |
| `ADMIN_USERNAME` | `admin` |
| `JWT_EXPIRE_MINUTES` | `720` |
| `MAX_UPLOAD_MB` | `5` |
| `CORS_ORIGINS` | blank |
| `ENABLE_API_DOCS` | `false` |
| `WEB_CONCURRENCY` | `2` |

Render supports adding environment variables from its Environment page and can redeploy when they change. citeturn0search2

11. Click **Create Web Service**.
12. Wait for the Docker build and deployment to finish.

Render will provide an `onrender.com` URL for the service. Custom domains can also be added later. citeturn0search0

## 8. Test the deployment

Open:

```text
https://YOUR-SERVICE.onrender.com/api/health
```

Expected response:

```json
{"ok":true,"database":"Family_Relations"}
```

Then open:

```text
https://YOUR-SERVICE.onrender.com/
```

The website should load.

## 9. First admin login

Use:

```text
Name: admin
Identifier: the plaintext admin password you chose locally
```

The plaintext password is never stored in the source. The server compares it with the bcrypt hash stored in `ADMIN_PASSWORD_HASH`.

## 10. Custom domain

After the Render service works, open the service's **Settings → Custom Domains** and add your domain, for example:

```text
familyrelations.example.com
```

Then configure the DNS records Render gives you. Render provides HTTPS for its web services/custom-domain setup; follow the current Render dashboard instructions for the exact DNS values.

## 11. Security checklist before public launch

- [ ] Rotate the MongoDB password from the old Python program.
- [ ] Create a dedicated MongoDB application user.
- [ ] Do not commit `.env`.
- [ ] Do not put `MONGO_URI` in frontend JavaScript.
- [ ] Do not put `JWT_SECRET` in frontend JavaScript.
- [ ] Use a strong unique admin password.
- [ ] Use the bcrypt hash in Render, not the plaintext password.
- [ ] Keep `ENABLE_API_DOCS=false` in production unless needed.
- [ ] Restrict MongoDB Atlas network access as much as your hosting/network plan permits.
- [ ] Use HTTPS only for the public site.
- [ ] Keep Render/GitHub/MongoDB credentials separate.
- [ ] Regularly rotate secrets and remove old database users/credentials.

## 12. Docker local test

With Docker installed:

```bash
docker build -t my-family-relations .
docker run --rm -p 10000:10000 --env-file .env my-family-relations
```

Open:

```text
http://127.0.0.1:10000/
```

Health check:

```text
http://127.0.0.1:10000/api/health
```

## 13. Updating the website

After deployment, normal Git pushes can trigger Render's automatic deployment when auto-deploy is enabled:

```bash
git add .
git commit -m "Update family relations web app"
git push
```

Render documents automatic deploys for services connected to a Git repository. citeturn0search0

## 14. Important architecture note

The public browser talks to FastAPI. FastAPI talks to MongoDB Atlas:

```text
Phone / PC Browser
        |
       HTTPS
        |
        v
     Render
   FastAPI app
        |
        | server-side MONGO_URI
        v
  MongoDB Atlas
 Family_Relations
```

The MongoDB URI and JWT secret are therefore not sent to website visitors.

### Render environment variables

Render environment variables are runtime configuration and are appropriate for secrets such as database credentials and API keys. Do not use Docker `ARG` for secrets; Render's Docker documentation specifically warns that secrets used during image builds can end up in the generated image. citeturn0search1turn0search5
