# Role-based RAG Chat (Streamlit)

Login as **admin** or **hr** — each role chats against **its own policy documents only**.

Built with **Streamlit**, **ChromaDB**, and **OpenRouter** (Gemini + embeddings).

---

## What it does

- Role-based login (`admin` vs `hr`)
- PDF policy documents per role under `data/<role>/`
- RAG pipeline: chunk → embed → store in Chroma → retrieve → answer with LLM
- Streamlit chat UI with streaming responses and source citations
- Deployable to **Streamlit Community Cloud** (free)

---

## Project structure

```
role-rag-app/
├── app.py                 # Streamlit UI (entry point)
├── auth.py                # Login from users.yaml
├── config.py              # Env vars, paths, RAG settings
├── users.yaml             # Demo usernames/passwords/roles
├── requirements.txt
├── .env.example           # Copy to .env locally
├── data/
│   ├── admin/             # Admin PDFs (laptop, hardware, trip)
│   └── hr/                # HR PDFs (leave, loan, medical)
├── index/                 # Chroma vector index (committed for Cloud deploy)
│   ├── admin/
│   └── hr/
└── rag/
    ├── ingest.py          # Build index from PDFs
    ├── store.py           # Chroma read/write (local + Cloud logic)
    ├── retrieve.py        # Vector search
    ├── answer.py          # RAG + small-talk handling
    ├── client.py          # OpenRouter embeddings + chat
    ├── chunking.py
    └── extract.py         # PDF text extraction (PyMuPDF)
```

---

## Quick start (local)

```bash
cd ~/Desktop/role-rag-app
cp .env.example .env          # add your OpenRouter key
pip install -r requirements.txt
python3 -m rag.ingest          # index both roles (or --role admin / --role hr)
streamlit run app.py
```

Open **http://localhost:8501**

### Demo logins

| Username | Password  | Role  | Documents |
|----------|-----------|-------|-----------|
| `admin`  | `admin123` | Admin | `data/admin/` — laptop, hardware & trip policies |
| `hr`     | `hr123`    | HR    | `data/hr/` — leave, loan & medical policies |

---

## Environment variables

Create `.env` locally (never commit this file):

```env
COGENT_OPRNROUTER_KEY=sk-or-v1-your-key-here
GEMINI_MODEL=google/gemini-2.5-flash
EMBED_MODEL=openai/text-embedding-3-small
```

| Variable | Purpose |
|----------|---------|
| `COGENT_OPRNROUTER_KEY` | OpenRouter API key (**exact name** — note `OPRN`, not `OPEN`) |
| `GEMINI_MODEL` | Chat model via OpenRouter |
| `EMBED_MODEL` | Embedding model via OpenRouter |

Get a key at [openrouter.ai](https://openrouter.ai).

---

## How the RAG pipeline works

1. **Ingest** (`python3 -m rag.ingest`)
   - Reads PDFs from `data/<role>/`
   - Chunks text (800 chars, 100 overlap)
   - Embeds chunks via OpenRouter
   - Stores vectors in Chroma under `index/<role>/`

2. **Retrieve** (on each question)
   - Embeds the user question
   - Finds top matching chunks in the role's Chroma collection

3. **Answer**
   - Sends retrieved passages + question to Gemini
   - Returns answer with source filenames

Each role has its own Chroma collection: `role_docs_admin`, `role_docs_hr`.

---

## Deploy to Streamlit Cloud (free)

### 1. Push to GitHub

Make sure the repo includes:

- `app.py`, `requirements.txt`, `data/`, `index/`, and all Python files
- **No** `.env` file (secrets go in Streamlit, not GitHub)

```bash
git add .
git commit -m "Deploy role-based RAG app"
git push origin main
```

### 2. Create the app on Streamlit

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub
2. Click **Create app**
3. Select your repo, branch `main`, main file **`app.py`**
4. Open **Advanced settings**:
   - **Python version:** `3.11` (recommended — avoid 3.14 on Cloud)
   - **Secrets:** paste TOML (see below)
5. Click **Deploy**

### 3. Streamlit Secrets (TOML format)

Secrets must be valid **TOML** — every string value needs **double quotes**:

```toml
COGENT_OPRNROUTER_KEY = "sk-or-v1-your-full-key-here"
GEMINI_MODEL = "google/gemini-2.5-flash"
EMBED_MODEL = "openai/text-embedding-3-small"
```

**Common mistakes:**

| Wrong | Right |
|-------|-------|
| `OPENROUTER_API_KEY=sk-or-...` (no quotes) | `COGENT_OPRNROUTER_KEY = "sk-or-..."` |
| `COGENT_OPENROUTER_KEY` | `COGENT_OPRNROUTER_KEY` |
| `.env` format | TOML with quoted values |

After saving secrets, **Reboot app** from the Streamlit dashboard.

---

## Vector DB setup on Streamlit Cloud

Streamlit Community Cloud is **not** the same as your local machine:

| | Local | Streamlit Cloud |
|---|-------|-----------------|
| Disk | Full read/write | Repo folder is **read-only** |
| `index/` in repo | Writable | Cannot write there |
| Build index in app | Works | Chroma `col.add()` often crashes |
| Persistence | Permanent | Temp storage is wiped on reboot |

Because of this, we use a **bundled pre-built index** committed to GitHub.

### How it works on Cloud

1. **`index/` is built locally** and pushed to GitHub:

   ```bash
   python3 -m rag.ingest
   git add index/
   git commit -m "Update bundled Chroma index"
   git push
   ```

2. **On deploy**, `rag/store.py`:
   - Detects Streamlit Cloud (`/mount/src/...`)
   - Copies `index/<role>/` from the repo → writable temp dir (`/tmp/role-rag-index/`)
   - Opens Chroma in read mode from that copy
   - Sidebar shows **"Pre-built index ready"**

3. **No "Build index" click needed** on Cloud — log in and chat directly.

### Local vs Cloud index behavior

| Action | Local | Streamlit Cloud |
|--------|-------|-----------------|
| Build index | Sidebar button or `python3 -m rag.ingest` | Pre-built from GitHub (recommended) |
| Index location | `index/` in project | Copied to `/tmp/role-rag-index/` |
| Survives reboot | Yes | Bundled index re-copied from repo on next run |

### Updating documents on Cloud

When you add or change PDFs:

```bash
# 1. Update PDFs in data/<role>/
# 2. Rebuild index locally
python3 -m rag.ingest

# 3. Commit and push the updated index
git add data/ index/
git commit -m "Update policies and re-index"
git push
```

Streamlit Cloud redeploys automatically (~1–2 min).


---

## Security notes (demo only)

- Passwords in `users.yaml` are plain text — fine for demos, not production
- Never commit `.env` or API keys to GitHub
- Rotate your OpenRouter key if it was exposed in screenshots or chat

---

## Commands reference

```bash
# Install dependencies
pip install -r requirements.txt

# Build index for all roles
python3 -m rag.ingest

# Build index for one role
python3 -m rag.ingest --role admin
python3 -m rag.ingest --role hr

# Run locally
streamlit run app.py
```

---

## Tech stack

- **UI:** Streamlit
- **Vector DB:** ChromaDB (local persistent / Cloud bundled copy)
- **LLM + embeddings:** OpenRouter (`google/gemini-2.5-flash`, `openai/text-embedding-3-small`)
- **PDF parsing:** PyMuPDF
- **Auth:** YAML-based demo logins
