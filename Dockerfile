FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed by pdfplumber/pdfminer
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies step by step for better error visibility
RUN pip install --no-cache-dir flask
RUN pip install --no-cache-dir pypdf
RUN pip install --no-cache-dir pdfplumber
RUN pip install --no-cache-dir reportlab
RUN pip install --no-cache-dir gunicorn

# Copy application files
COPY geister_custom_catalog.py .
COPY webapp.py .

# Copy all catalog PDFs
COPY *.pdf ./

# Copy pre-built article index (skip expensive rebuild during build)
COPY article_index_cache.json .

# Create output directory for generated PDFs
RUN mkdir -p /app/generated

EXPOSE 5000

# Run with gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "webapp:app"]
