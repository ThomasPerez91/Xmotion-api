FROM python:3.11

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --system celery && adduser --system --ingroup celery celery

RUN mkdir -p /app/deepface_cache && chown -R celery:celery /app/deepface_cache

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

USER celery

COPY . .

ENV DEEPFACE_HOME=/app/deepface_cache
ENV HOME=/app

CMD ["celery", "-A", "app.worker.tasks", "worker", "--loglevel=info", "--without-mingle"]
