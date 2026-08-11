FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY worker/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# کدهای مشترک (مدل‌ها، تنظیمات، استوریج) از سرویس api استفاده می‌شه
COPY api/app /app/app
COPY worker/app /app/workerapp

CMD ["celery", "-A", "workerapp.celery_app:celery", "worker", "--loglevel=INFO"]
