# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Install Chromium & dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        chromium-driver chromium \
        ca-certificates fonts-liberation libnss3 libgconf-2-4 libxi6 libgbm1 \
    && rm -rf /var/lib/apt/lists/*


# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # For Selenium to find chrome binary
    CHROME_BIN=/usr/bin/chromium

# Working directory
WORKDIR /app

# Copy requirements first, install, then copy source – leverages Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

# By default run Flask app with gunicorn (production ready)
CMD ["python", "app.py"]
