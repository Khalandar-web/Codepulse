FROM python:3.14-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential gcc curl \
    && rm -rf /var/lib/apt/lists/*

# 🔥 ADD THIS LINE (IMPORTANT)
ENV PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1

COPY . .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]