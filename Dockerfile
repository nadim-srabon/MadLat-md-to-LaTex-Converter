FROM python:3.11-slim

# --- LaTeX toolchain (needed to compile the generated .tex into a PDF) ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-latex-extra \
    && rm -rf /var/lib/apt/lists/*

# Run as a non-root user (good practice; not required by Render specifically)
RUN useradd -m -u 1000 user

WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY --chown=user . .

USER user
ENV HOME=/home/user
ENV PATH=/home/user/.local/bin:$PATH

# Render assigns the port dynamically via $PORT -- don't hardcode it
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
