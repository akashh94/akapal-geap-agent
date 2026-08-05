FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY app/ app/
COPY agents-cli-manifest.yaml .

RUN pip install --no-cache-dir .

EXPOSE 8080
CMD ["uvicorn", "app.fast_api_app:app", "--host", "0.0.0.0", "--port", "8080"]
