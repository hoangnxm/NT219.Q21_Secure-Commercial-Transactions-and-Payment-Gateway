# Sử dụng base image Python 3.11 bản slim để tối ưu dung lượng
FROM python:3.11-slim

# Thiết lập thư mục làm việc bên trong container
WORKDIR /app

# Cài đặt đầy đủ 100% các thư viện theo đúng mã nguồn
RUN pip install --no-cache-dir fastapi uvicorn pandas scikit-learn pydantic numpy

# Chép toàn bộ mã nguồn và dữ liệu vào container
COPY . .

# Mở cổng 8001 cho API
EXPOSE 8001

# Lệnh khởi động service
CMD ["python", "main.py"]