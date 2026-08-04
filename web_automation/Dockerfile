FROM mcr.microsoft.com/playwright/python:v1.61.0-noble

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PLAYWRIGHT_BROWSER_CHANNEL=chromium

WORKDIR /app
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8010
CMD ["python", "-m", "uvicorn", "gateway.app:app", "--host", "0.0.0.0", "--port", "8010"]
