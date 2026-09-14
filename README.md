# Role-based RAG Chat (Streamlit)

Login as **admin** or **hr** — each role chats against **its own documents only**.

## Quick start

This is a **standalone project**. All paths and config live inside this folder.

```bash
cd ~/Desktop/role-rag-app
cp .env.example .env                    # add your COGENT_OPRNROUTER_KEY
pip install -r requirements.txt
python3 -m rag.ingest                   # index both roles (or --role admin / --role hr)
streamlit run app.py
```

Browser opens at **http://localhost:8501**

### Demo logins

| Username | Password | Documents |
|---|---|---|
| `admin` | `admin123` | `data/admin/` — laptop, hardware, trip PDFs |
| `hr` | `hr123` | `data/hr/` — leave, loan, medical PDFs |

---

## Streamlit guide (first time)

### What is Streamlit?

Streamlit turns Python scripts into a web app. You run one command (`streamlit run app.py`) and get a UI in your browser — no HTML/CSS required.

### What you'll see

1. **Login page** — username + password form  
2. After login → **Chat page** — like ChatGPT, but answers come from your role's docs  
3. **Sidebar** — shows your role, build index button, sample questions  

### Streamlit basics used in this app

| Code | What it does |
|---|---|
| `st.title()` / `st.caption()` | Headings and subtitles |
| `st.form()` + `st.form_submit_button()` | Login form (submits together) |
| `st.session_state` | Remembers login + chat history while the app runs |
| `st.chat_message()` + `st.chat_input()` | Chat UI |
| `st.sidebar` | Left panel (logout, build index) |
| `st.spinner()` | "Loading..." while RAG runs |
| `st.rerun()` | Refresh page after login/logout |

### Your workflow each time

```bash
# 1) Terminal — start the app
cd role-rag-app
streamlit run app.py

# 2) Browser — log in as admin OR hr

# 3) Sidebar — click "Build index for …" once per role (first time)

# 4) Chat — ask questions

# 5) Test isolation — log out, log in as the other role, ask the same question
```

### Stop the app

In the terminal where Streamlit is running, press **Ctrl+C**.

### Add your own documents

1. Put `.pdf`, `.txt`, or `.md` files in `data/admin/` or `data/hr/`  
2. Sidebar → **Build index** (or run `python3 -m rag.ingest --role admin`)  
3. Chat again  

PDFs are parsed with **PyMuPDF** (text + hyperlink URLs appended to chunks).

---

## Layout

```
role-rag-app/
├── app.py              # Streamlit UI (login + chat)
├── auth.py             # username/password → role
├── users.yaml          # demo users
├── config.py
├── data/
│   ├── admin/          # admin-only docs
│   └── hr/             # hr-only docs
├── rag/
│   ├── extract.py      # PDF / text loading
│   ├── ingest.py
│   ├── retrieve.py
│   ├── answer.py
│   └── store.py        # Chroma per role
└── index/              # gitignored vector DB
```

## How role isolation works

- Each role has its own folder (`data/<role>/`) and Chroma path (`index/<role>/`).
- After login, `st.session_state.role` is set — every question calls `retrieve(role, question)` on **that collection only**.
- HR cannot search admin vectors even if they guess admin topics.
