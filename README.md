# NarcoVerify — Deployment Guide

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```
Opens at http://localhost:8501

## Deploy for free — Streamlit Community Cloud (recommended)
1. Create a GitHub repo and push these files (`app.py`, `requirements.txt`, `images/`).
2. Go to https://share.streamlit.io → "New app".
3. Pick your repo, branch `main`, and set the main file path to `app.py`.
4. Click Deploy. You'll get a public URL like:
   `https://<your-app-name>.streamlit.app`

## Alternative: Render.com
1. Push the repo to GitHub.
2. New "Web Service" on https://render.com, connect the repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`

## Alternative: Hugging Face Spaces
1. Create a new Space, SDK = "Streamlit".
2. Upload `app.py`, `requirements.txt`, and the `images/` folder.
3. It builds and serves automatically at `https://huggingface.co/spaces/<you>/<space-name>`.

## Notes
- `test_records.db` (SQLite) is created automatically on first run — it lives on the
  host's disk, so on most free tiers (Streamlit Cloud, HF Spaces) it resets on redeploy.
  For persistent data, swap in a hosted DB (e.g. Postgres) later.
- The `images/reference/` folder must be included in the repo for per-substance
  reference images to load.
