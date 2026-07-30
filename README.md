# LaTeX Summary Agent

Upload a PDF, Markdown, or text file (or paste raw text), and get back a
summarized PDF styled with teal Computer Modern headers.

## Deploying to Render (free tier)

Render's free web service tier requires no credit card, supports Docker
directly, and is enough for personal use. It sleeps after 15 minutes of
inactivity and takes ~30-60s to wake up on the next request -- fine for a
tool you trigger yourself now and then.

1. Push this project to a GitHub repo (Render deploys from git).
2. Go to [render.com](https://render.com) -> New -> Web Service -> connect
   your repo.
3. Environment: **Docker** (Render auto-detects the Dockerfile).
4. Instance type: **Free**.
5. Under **Environment Variables**, add:
   - `ANTHROPIC_API_KEY` - your Anthropic API key
   - `ACCESS_CODE` - a password only you know, so strangers can't spend
     your API credits
6. Click **Create Web Service** and wait for the build to finish -> you'll
   get a public URL like `https://<service-name>.onrender.com`.

## Using it

- Browser: open the URL, upload a file or paste text, enter your access
  code, submit.
- Or from a terminal/script:
  ```bash
  curl -X POST https://<service-name>.onrender.com/summarize \
    -F "file=@notes.pdf" \
    -F "title=My Summary" \
    -F "access_code=your-secret-code" \
    -o summary.pdf
  ```
- First request after ~15 min idle will be slow (cold start); after that
  it's fast until it sleeps again.

## Local test (optional, before deploying)

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
export ACCESS_CODE=test123
uvicorn app:app --reload
# visit http://localhost:8000
```

## Cost note

Hosting is free on Render's tier above. The per-request cost is the
Anthropic API call itself -- keep the access code private if you don't
want random visitors spending your credits.
