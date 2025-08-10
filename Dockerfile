FROM python:3.11-slim

# Install system deps for scapy, networking, and bcrypt; adjust for your OS
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential python3-dev libssl-dev libffi-dev cargo \
    libpcap-dev gcc net-tools iproute2 iputils-ping \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

EXPOSE 8000

# By default run the server; in production recommend running via gunicorn
CMD ["python3", "iseeyou_server.py"]
