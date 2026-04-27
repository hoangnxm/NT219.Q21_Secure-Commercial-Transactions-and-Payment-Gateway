# Sử dụng base image Python 3.12 bản slim để tối ưu dung lượng
FROM python:3.12-slim

# Ngăn Python tạo ra các file .pyc và ép output log ra console ngay lập tức
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Thiết lập thư mục làm việc trong container
WORKDIR /payment_orchestrator

# Cài đặt thư viện hệ thống cần thiết (nếu có dùng psycopg2 để kết nối DB)
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt vào trước để tận dụng Docker cache
COPY requirements.txt .

# Cài đặt các thư viện Python
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn vào container
COPY . .

# Expose port mặc định của uvicorn
EXPOSE 8000

# Lệnh khởi chạy server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--ssl-keyfile=/certs/server.key", "--ssl-certfile=/certs/server.crt", "--ssl-ca-certs=/certs/ca.crt", "--ssl-cert-reqs=2"]