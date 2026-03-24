FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy engine code
COPY . .

# Copy agent config + knowledge from project root
COPY ../../agent.yaml /app/agent.yaml
COPY ../../agent/ /app/agent/

EXPOSE ${PORT:-5000}

CMD flask db upgrade && gunicorn run:app --bind 0.0.0.0:${PORT:-5000}
