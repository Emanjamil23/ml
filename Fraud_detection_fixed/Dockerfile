FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY shared/ ./shared/

EXPOSE 8000

CMD ["uvicorn", "backend.api.index:app", "--host", "0.0.0.0", "--port", "8000"]