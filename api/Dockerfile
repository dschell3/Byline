# SCRUM-62: container image for the FastAPI service.
# Built by docker-compose; you never run this file by hand.

FROM python:3.13-slim

# Where the code lives inside the container.
WORKDIR /app

# Install dependencies first, on their own layer, so Docker caches them
# and only re-runs this step when requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the api/ folder in.
COPY . .

# Same command as api/README.md, plus --host 0.0.0.0 so the port is
# reachable from outside the container. --reload picks up edits because
# docker-compose mounts api/ over /app.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]