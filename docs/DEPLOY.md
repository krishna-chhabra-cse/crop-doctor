# Deploying Crop Doctor

```
Farmer's phone ──► Vercel (Next.js website, web/) ──► Render (FastAPI API, server/) ──► Supabase (Postgres)
                                                       └─ ONNX model + treatment notes run here
```

Code: private GitHub repo `krishna-chhabra-cse/crop-doctor`. Render and Vercel both deploy from it.

## 1. Supabase: the database (you, ~3 minutes)

1. Go to https://supabase.com, sign in, **New project**. Name `crop-doctor`, a strong database password
   (save it in your password manager), region **South Asia (Mumbai)**.
2. When it's ready: click **Connect** (top bar), then **Connection string**, choose **Session pooler**
   (works from Render; the "direct" connection needs IPv6). Copy the URI. It looks like
   `postgresql://postgres.<project-ref>:[YOUR-PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:5432/postgres`.
3. Replace `[YOUR-PASSWORD]` with your database password. Keep this string private: it's the key to your data.

The API creates its tables automatically on first start.

## 2. Render: the API (you, ~5 minutes + ~10 minutes build)

1. Go to https://render.com, sign in with GitHub.
2. **New > Blueprint**, connect GitHub and give Render access to the `crop-doctor` repo, select it.
   Render reads `render.yaml` and proposes the service `crop-doctor-api` (free plan, Singapore).
3. Fill in the values it asks for:
   - `DATABASE_URL`: the Supabase string from step 1.
   - `ALLOWED_ORIGINS`: leave empty for now (Vercel addresses are already allowed by `ALLOWED_ORIGIN_REGEX`).
   - `GEMINI_API_KEY` or `ANTHROPIC_API_KEY`: optional, for AI replies. Leave both empty for sourced template replies.
4. **Apply**. The first build installs the libraries and prepares the model (~10 minutes).
5. When it's live, open `https://<your-service>.onrender.com/api/health`. It should say `{"ok":true,...}`.
6. The expert dashboard password: Render > `crop-doctor-api` > **Environment** > `EXPERT_KEY` (generated for you).

Free-plan behaviour: the API sleeps after 15 minutes without visitors; the first visit then takes about a minute
(the website shows "Waking up the server…"). Open the site a minute before a demo.

### Adding AI replies later (Gemini)
Render > `crop-doctor-api` > **Environment** > **Add Environment Variable**: name `GEMINI_API_KEY`, value your key
from Google AI Studio > **Save** (the server restarts). Check https://crop-doctor-api-fz3n.onrender.com/api/meta shows
`"llm_provider":"gemini"`. Never put the key in code, git or chat. If replies stop being AI-written, the key is
missing, wrong or out of quota: the app falls back to template replies by itself. Optional `GEMINI_MODEL` picks
another model (default `gemini-3.6-flash`).

## 3. Vercel: the website (live at https://crop-doctor-snowy.vercel.app)

Also served at https://cropdoctor.cv. The Vercel project is linked to the GitHub repo with **Root Directory = `web`**,
so **every `git push` to `main` deploys the website automatically** (like Render does for the API). Without that
setting Vercel builds the repo root, finds no Next.js app and fails ("Couldn't find any `pages` or `app`
directory"), which is what the red "Error" deployments before 6 Nov were.

`NEXT_PUBLIC_API_URL` must be the Render address: **`https://crop-doctor-api-fz3n.onrender.com`**. Careful:
`crop-doctor-api.onrender.com` (without `-fz3n`) is someone else's app; Render adds a suffix when a name is taken.

Run it on your computer (uses the live API; the file is git-ignored):

```bash
echo NEXT_PUBLIC_API_URL=https://crop-doctor-api-fz3n.onrender.com > web/.env.development.local
npm --prefix web run dev
```

Then open http://localhost:3000.

## Updating the model

```bash
.venv/Scripts/python -m crop_doctor.model.export_onnx        # writes server/assets/ (checks ONNX = PyTorch answers)
git add server/assets && git commit -m "New model" && git push   # Render redeploys automatically
```

## Local development

```bash
.venv/Scripts/python -m uvicorn server.main:app --port 8000     # API (uses PyTorch + local SQLite)
npm --prefix web run dev                                         # website on http://localhost:3000
```
