FROM python:3.13-slim

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Tokyo

RUN apt-get update && apt-get install -y --no-install-recommends \
    libfreetype6 \
    libjpeg62-turbo \
    zlib1g \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY haccp_1_app.py .

RUN mkdir -p /app/data
ENV STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_HEADLESS=true \
    DATA_DIR=/app/data

EXPOSE 8501

CMD ["streamlit", "run", "haccp_1_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
