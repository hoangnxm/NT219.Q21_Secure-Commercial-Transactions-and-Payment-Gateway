# api_gateway/Dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN pip install fastapi uvicorn httpx
COPY main.py .
CMD ["python", "main.py"]