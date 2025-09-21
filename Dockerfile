FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends     build-essential     libfreetype6-dev     libjpeg-dev     zlib1g-dev     && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

RUN mkdir -p /app/data
ENV STREAMLIT_SERVER_PORT=8501     STREAMLIT_SERVER_HEADLESS=true     DATA_DIR=/app/data

EXPOSE 8501

CMD ["streamlit", "run", "haccp_1_app.py", "--server.port=8501", "--server.address=0.0.0.0"]