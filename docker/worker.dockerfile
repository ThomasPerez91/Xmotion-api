FROM python:3.11

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN addgroup --system celery && adduser --system --ingroup celery celery
USER celery

COPY . .

CMD ["celery", "-A", "app.worker.tasks", "worker", "--loglevel=info", "--without-mingle"]