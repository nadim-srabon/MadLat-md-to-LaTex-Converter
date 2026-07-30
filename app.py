"""
LaTeX Summary Agent -- Web version
-----------------------------------
Same pipeline as the CLI agent (extract text -> summarize -> LaTeX -> PDF),
wrapped as a small FastAPI app so it can be deployed publicly (e.g. on
Hugging Face Spaces).

Env vars required:
  ANTHROPIC_API_KEY  - your Anthropic API key
  ACCESS_CODE        - a simple shared secret so random visitors can't burn
                        your API credits. Anyone using the form/API must
                        supply this. Set it to something only you know.
"""

import os
import tempfile
import subprocess
import uuid
from datetime import date
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from jinja2 import Environment, FileSystemLoader
from pypdf import PdfReader
import anthropic

from prompts import PROMPT_STYLES

APP_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = APP_DIR / "templates"
OUTPUT_DIR = APP_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
ACCESS_CODE = os.environ.get("ACCESS_CODE")  # None = no gate (not recommended publicly)

app = FastAPI(title="LaTeX Summary Agent")


def extract_text_from_upload(file: UploadFile) -> str:
    suffix = Path(file.filename).suffix.lower()
    raw = file.file.read()
    if suffix == ".pdf":
        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            tmp.write(raw)
            tmp.flush()
            reader = PdfReader(tmp.name)
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    elif suffix in (".md", ".txt"):
        return raw.decode("utf-8", errors="ignore")
    else:
        raise HTTPException(400, f"Unsupported file type: {suffix} (use .pdf, .md, or .txt)")


def summarize(source_text: str, prompt_style: str = "default") -> str:
    if not source_text.strip():
        raise HTTPException(400, "No text extracted -- nothing to summarize.")
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=PROMPT_STYLES[prompt_style],
        messages=[{"role": "user", "content": source_text}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def render_latex(body: str, title: str, author: str) -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("document.tex")
    return template.render(
        title=title, author=author, date=date.today().strftime("%B %d, %Y"), body=body
    )


def compile_pdf(tex_content: str, out_name: str) -> Path:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        tex_file = tmp_path / f"{out_name}.tex"
        tex_file.write_text(tex_content, encoding="utf-8")
        for _ in range(2):
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex_file.name],
                cwd=tmp_path, capture_output=True, text=True,
            )
        if result.returncode != 0:
            log_tail = "\n".join(result.stdout.splitlines()[-30:])
            raise HTTPException(500, f"LaTeX compilation failed:\n{log_tail}")
        produced = tmp_path / f"{out_name}.pdf"
        final_path = OUTPUT_DIR / f"{out_name}.pdf"
        final_path.write_bytes(produced.read_bytes())
        return final_path


def check_access(access_code: str | None):
    if ACCESS_CODE and access_code != ACCESS_CODE:
        raise HTTPException(403, "Invalid or missing access code.")


@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <html>
    <head><title>LaTeX Summary Agent</title></head>
    <body style="font-family: sans-serif; max-width: 600px; margin: 40px auto;">
      <h2>LaTeX Summary Agent</h2>
      <form action="/summarize" method="post" enctype="multipart/form-data">
        <p>Upload a PDF / .md / .txt file:<br>
           <input type="file" name="file"></p>
        <p>...or paste raw text instead:<br>
           <textarea name="text" rows="6" style="width:100%"></textarea></p>
        <p>Title: <input type="text" name="title" value="Summary"></p>
        <p>Access code: <input type="password" name="access_code"></p>
        <button type="submit">Summarize -&gt; PDF</button>
      </form>
    </body>
    </html>
    """


@app.post("/summarize")
def summarize_endpoint(
    file: UploadFile | None = File(None),
    text: str | None = Form(None),
    title: str = Form("Summary"),
    access_code: str | None = Form(None),
):
    check_access(access_code)

    if file is not None and file.filename:
        source_text = extract_text_from_upload(file)
    elif text and text.strip():
        source_text = text
    else:
        raise HTTPException(400, "Provide either a file or text.")

    body = summarize(source_text)
    tex_content = render_latex(body, title, author="Nadim")
    out_name = f"summary-{uuid.uuid4().hex[:8]}"
    pdf_path = compile_pdf(tex_content, out_name)

    return FileResponse(pdf_path, media_type="application/pdf", filename=f"{title}.pdf")


@app.get("/health")
def health():
    return {"status": "ok"}
