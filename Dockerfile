# Use official Python slim image for smaller attack surface
FROM python:3.11-slim

# Security: Create non-root user
RUN groupadd -r iseeyou && useradd -r -g iseeyou iseeyou

# Install system dependencies with security considerations
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Core networking tools
    build-essential \
    libpcap-dev \
    gcc \
    net-tools \
    iproute2 \
    iputils-ping \
    # Wireless tools (only essential ones)
    wireless-tools \
    iw \
    # Security hardening
    libcap2-bin \
    procps \
    # Logging
    rsyslog \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Security: Set proper permissions
RUN mkdir -p /app /var/log/iseeyou /tmp/iseeyou_captures \
    && chown -R iseeyou:iseeyou /app /var/log/iseeyou /tmp/iseeyou_captures \
    && chmod 755 /app \
    && chmod 755 /var/log/iseeyou \
    && chmod 755 /tmp/iseeyou_captures

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn

# Copy application code
COPY . /app

# Security: Set proper permissions on application files
RUN chown -R iseeyou:iseeyou /app \
    && chmod -R 755 /app/scripts \
    && chmod 644 /app/*.py \
    && chmod 644 /app/*.ini* \
    && chmod 644 /app/requirements.txt \
    && find /app -name "*.sh" -exec chmod +x {} \;

# Security: Drop root privileges
USER iseeyou

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Expose port
EXPOSE 8000

# Security: Use gunicorn with proper configuration
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--worker-class", "sync", \
     "--worker-connections", "1000", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "50", \
     "--timeout", "30", \
     "--keep-alive", "10", \
     "--log-level", "info", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--capture-output", \
     "iseeyou.dashboard:create_app()"]
