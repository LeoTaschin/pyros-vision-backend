FROM python:3.11-slim

WORKDIR /app

# Dependências de sistema para OpenCV (usado internamente pelo ultralytics)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Pré-carrega o modelo na build para evitar delay no primeiro request
RUN python -c "from ultralytics import YOLO; YOLO('keremberke/yolov8n-fire-detection')"

EXPOSE 8000

CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
