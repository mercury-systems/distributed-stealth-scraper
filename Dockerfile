FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y \
    wget gnupg ca-certificates libglib2.0-0 libnss3 libnspr4 \
    libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libdbus-1-3 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements-heavy.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-heavy.txt
RUN playwright install chromium
RUN playwright install-deps chromium

COPY . .
RUN pip install -e .

CMD ["stealth-scraper", "demo"]
