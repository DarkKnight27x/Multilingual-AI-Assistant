FROM python:3.11-slim

WORKDIR /app

# System deps needed by sentence-transformers / chromadb
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Build the vector index at image build time so the container starts ready.
# (Re-run manually if you change data/knowledge_base/ without rebuilding the image.)
RUN python scripts/build_index.py || true

EXPOSE 8000

CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
