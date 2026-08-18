FROM nvidia/cuda:13.0.2-cudnn-runtime-ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    ffmpeg \
    libsndfile1 \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN python3 -m pip install --break-system-packages --no-cache-dir \
    torch==2.11.0 \
    torchaudio==2.11.0 \
    --index-url https://download.pytorch.org/whl/cu130

COPY voice_service/requirements.txt /app/requirements.txt

RUN python3 -m pip install --break-system-packages --no-cache-dir \
    -r /app/requirements.txt

COPY voice_service /app/voice_service

EXPOSE 8000

ENTRYPOINT []

CMD ["python3", "-m", "uvicorn", "voice_service.api:app", "--host", "0.0.0.0", "--port", "8000"]
