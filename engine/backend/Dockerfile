FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Python deps
COPY engine/backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy engine backend
COPY engine/backend/ ./

# Copy agent config + knowledge + tools from project root
COPY agent.yaml ./agent.yaml
COPY agent/ ./agent/

EXPOSE ${PORT:-5000}

CMD ["sh", "-c", "gunicorn run:app --bind 0.0.0.0:${PORT:-5000} --workers 2 --timeout 120"]
