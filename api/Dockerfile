FROM python:3.12-slim
WORKDIR /app
COPY api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY api /app
COPY ingestion /app/ingestion
COPY ai-service /app/ai-service
COPY evidence-service /app/evidence-service
COPY workers /app/workers
COPY bootstrap.py /app/bootstrap.py
# El prototipo hermano (the-newsbreakers/api + config) se reutiliza en local via PYTHONPATH.
# En Docker, monta esas carpetas en /legacy y define TNB_DEMO_ROOT=/legacy.
ENV PYTHONPATH=/app:/app/ingestion:/app/ai-service:/app/ai-service/nlp:/app/workers:/legacy/api
ENV TNB_DEMO_ROOT=/legacy
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8010"]
