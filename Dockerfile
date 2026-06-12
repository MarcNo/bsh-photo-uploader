FROM python:3.12-slim

# System deps (Pillow, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

# Create data mount points (overridden by volume mounts at runtime)
RUN mkdir -p /DATA/bsh/picnic-images

EXPOSE 5000

CMD ["python", "entrypoint.py"]
