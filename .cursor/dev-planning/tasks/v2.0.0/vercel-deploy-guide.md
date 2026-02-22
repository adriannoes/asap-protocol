# Guide: First Vercel Deploy (Sprint M1 – Task 1.6)

This guide covers deploying the Next.js app `apps/web` to Vercel, step by step.

---

## Prerequisites

- [Vercel](https://vercel.com) account (GitHub login is the simplest).
- `asap-protocol` repository on GitHub with up-to-date code (push to `main` or the branch you want to use).
- **GitHub OAuth App** already created (for “Sign in with GitHub”):
  - GitHub → Settings → Developer settings → OAuth Apps → New OAuth App (or use an existing one).
  - Homepage URL: `https://your-domain.vercel.app` (can be adjusted later).
  - Authorization callback URL: `https://your-domain.vercel.app/api/auth/callback/github`.

---

## 1.6.1 – Connect the repository to Vercel

1. Go to [vercel.com](https://vercel.com) and sign in (recommended: **Continue with GitHub**).
2. On the dashboard, click **Add New…** → **Project**.
3. **Import** from GitHub:
   - If the repo does not appear, click **Adjust GitHub App Permissions** and authorize Vercel for the org/user where `asap-protocol` lives.
   - Select the **asap-protocol** repository and click **Import**.
4. **Project configuration (important for monorepo)**:
   - **Framework Preset**: leave **Next.js** (auto-detected).
   - **Root Directory**: click **Edit** and set to **`apps/web`**.  
     This tells Vercel that the app to build is in `apps/web`, not the repo root.
   - **Build Command**: leave default (`npm run build` or `next build`).
   - **Output Directory**: leave default (Next.js).
   - **Install Command**: leave `npm install` (runs inside `apps/web`).
5. **Do not** add environment variables in this step (we do that in 1.6.2).
6. Click **Deploy**. The first deploy may fail if `AUTH_SECRET` or GitHub credentials are missing; that is expected. We fix it in the next step.

**Checklist 1.6.1:**
- [x] Project created on Vercel
- [x] Root Directory = `apps/web`
- [x] Framework = Next.js
- [x] First deploy run (may fail due to env vars)

**Note – gh-pages excluded**: The repo has a `gh-pages` branch used by MkDocs for docs (GitHub Pages). That branch contains only built static HTML, not `apps/web`. The root `vercel.json` sets `git.deploymentEnabled.gh-pages: false` so Vercel skips deploys for that branch and avoids "Root Directory apps/web does not exist" errors.

---

## 1.6.2 – Configure environment variables on Vercel

1. In the Vercel project, go to **Settings** → **Environment Variables**.
2. Add these variables (for **Production**, and optionally Preview if you want to test on PRs):

| Name                 | Value                    | Notes |
|----------------------|--------------------------|--------|
| `AUTH_SECRET`        | `<64-char hex value>`    | Generate with: `openssl rand -hex 32` |
| `GITHUB_CLIENT_ID`   | OAuth App Client ID      | From GitHub OAuth App |
| `GITHUB_CLIENT_SECRET` | OAuth App Client Secret | From GitHub OAuth App |
| `NEXT_PUBLIC_APP_URL` | `https://your-project.vercel.app` | Actual deploy URL (e.g. `https://asap-protocol.vercel.app`) |

3. **Generate `AUTH_SECRET`** (in your terminal):
   ```bash
   openssl rand -hex 32
   ```
   Copy the output and paste it as the value of `AUTH_SECRET` on Vercel (no quotes).

4. **GitHub OAuth App**  
   If not configured yet:
   - GitHub → Settings → Developer settings → OAuth Apps → New OAuth App.
   - **Authorization callback URL** must be: `https://<your-vercel-domain>.vercel.app/api/auth/callback/github`  
   Use the URL shown in the project’s **Domains** tab (e.g. `https://asap-protocol-xxx.vercel.app`).

5. Save the variables. To apply to Production, run a **Redeploy**:
   - **Deployments** → three-dot menu on the latest deployment → **Redeploy**.

**Checklist 1.6.2:**
- [x] `AUTH_SECRET` set (openssl rand -hex 32)
- [x] `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` set
- [x] `NEXT_PUBLIC_APP_URL` = actual app URL on Vercel
- [x] Redeploy run after saving variables

---

## 1.6.3 – Verify production build

1. In **Deployments**, open the latest deployment.
2. Confirm the **Build** finished successfully (green status).
3. Click **Visit** (or the deployment URL) and verify:
   - The landing page loads.
   - “Sign in with GitHub” opens the OAuth flow and returns to the app (if callback URL is configured correctly).
4. Optional – local build (same as Vercel):
   ```bash
   cd apps/web && npm run build
   ```
   Should complete without errors.

**Checklist 1.6.3:**
- [x] Build passed on Vercel
- [x] Production URL opens and landing page responds
- [x] GitHub login works (if env vars and OAuth App are correct)

---

## 1.6.4 – Domain (optional)

- **Default domain**: Vercel already provides `https://<project-name>.vercel.app`.
- **Custom domain**: Settings → Domains → Add and follow the instructions (DNS or CNAME). Can be done later (e.g. in M4).

---

## Acceptance summary (Task 1.6)

- [x] Production URL accessible
- [x] Automatic deploy (CI/CD) on push to `main` (or configured branch)

Done. Acceptance criteria and sub-tasks 1.6.1–1.6.4 are reflected in [sprint-M1-webapp-foundation.md](./sprint-M1-webapp-foundation.md).
