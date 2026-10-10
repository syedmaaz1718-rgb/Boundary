FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py engine.py ./
COPY frontend ./frontend
COPY models ./models
COPY data ./data
ENV PYTHONUNBUFFERED=1 PORT=8000 OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2
EXPOSE 8000
CMD ["sh","-c","gunicorn --workers 1 --threads 2 --timeout 120 --bind 0.0.0.0:${PORT} app:app"]
