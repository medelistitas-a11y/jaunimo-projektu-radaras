FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System deps:
# - libpq-dev/gcc for psycopg build fallback
# - poppler-utils for pdftoppm (used by ocrmypdf)
# - tesseract-ocr + lit/eng language data for OCR of scanned PDFs
# - ghostscript required by ocrmypdf
# - libreoffice for legacy .doc -> .docx conversion (headless)
# - fonts-dejavu for consistent text rendering during OCR pre-processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    poppler-utils \
    ghostscript \
    tesseract-ocr \
    tesseract-ocr-lit \
    tesseract-ocr-eng \
    libreoffice --no-install-recommends \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv

COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements-dev.txt

# Playwright browser (chromium only) for the JS adapter.
RUN python -m playwright install --with-deps chromium || true

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
