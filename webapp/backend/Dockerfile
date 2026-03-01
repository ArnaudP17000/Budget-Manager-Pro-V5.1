FROM python:3.13-slim
WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Backend (dans /app)
COPY backend/ .

# Frontend (dans /frontend, accessible via ../frontend depuis /app)
COPY frontend/ /frontend

EXPOSE 5000

CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:5000", "--timeout", "120", "server:app"]
