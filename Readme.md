# 🛡️ NT219 - Secure Commercial Transactions and Payment Gateway

Chào mừng anh em đến với Đồ án môn học NT219! 
Hệ thống này được thiết kế theo kiến trúc **Microservices** chạy trên nền tảng **Kubernetes (Local)**, kết hợp bảo mật **Mutual TLS (mTLS)** cấp độ cao với Két sắt mã hoá **SoftHSM**.

Dưới đây là hướng dẫn "Lắp ráp mô hình" từ A-Z để anh em có thể tự chạy hệ thống trên máy cá nhân.

---

## ⚙️ Yêu cầu chuẩn bị (Prerequisites)

Trước khi bắt đầu, anh em cần cài đặt các công cụ sau (Dùng cho Windows/WSL2 hoặc Ubuntu/Mac):

1. **Docker Desktop** (Hoặc Docker Engine) - Bắt buộc phải chạy được lệnh `docker`.
2. **kubectl**: Công cụ giao tiếp với Kubernetes.
   - [Hướng dẫn cài đặt kubectl](https://kubernetes.io/docs/tasks/tools/)
3. **k3d**: Công cụ giả lập cụm Kubernetes siêu nhẹ chạy trong Docker.
   - Lệnh cài nhanh: `curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash`

---

## 🚀 Hướng dẫn Triển khai (Deployment Guide)

Anh em làm tuần tự theo các "Giai đoạn lắp ráp" dưới đây, tuyệt đối không nhảy bước nhé!

### Giai đoạn 1: Xây dựng Cụm máy chủ (K8s Cluster)

Mở Terminal và gõ các lệnh sau để tạo một cụm Kubernetes tên là `payment-gateway`:

```bash
# 1. Tạo cluster với k3d
k3d cluster create payment-gateway --api-port 6550 -p "8081:80@loadbalancer" --agents 2

# 2. Tạo 2 khu vực (namespaces) để cách ly hệ thống
kubectl create namespace nt219-project
kubectl create namespace merchant-site

Giai đoạn 2: Bơm "Thẻ ngành" (Cấu hình mTLS & Secret)
Hệ thống yêu cầu chứng chỉ mTLS để SoftHSM và Payment/Order giao tiếp an toàn.
(Lưu ý: Đảm bảo trong thư mục chứa code đã có sẵn thư mục certs chứa ca.crt, client.crt, client.key, server.crt, server.key).

# 1. Tạo hộp chứa chứng chỉ cho Server (SoftHSM)
kubectl create secret generic softhsm-certs \
  --from-file=tls.crt=./softhsm/certs/server.crt \
  --from-file=tls.key=./softhsm/certs/server.key \
  --from-file=ca.crt=./softhsm/certs/ca.crt \
  -n nt219-project

# 2. Tạo hộp chứa chứng chỉ cho Client (Payment Orchestrator)
kubectl create secret generic client-certs \
  --from-file=client.crt=./softhsm/certs/client.crt \
  --from-file=client.key=./softhsm/certs/client.key \
  --from-file=ca.crt=./softhsm/certs/ca.crt \
  -n nt219-project

# 3. Nhân bản hộp chứng chỉ Client sang cho Order Service (Merchant Site)
kubectl get secret client-certs -n nt219-project -o yaml | sed 's/namespace: nt219-project/namespace: merchant-site/g' | kubectl apply -f -

Giai đoạn 3: Nấu linh kiện (Build Docker Images)
Đứng ở thư mục gốc của project, chúng ta cần đóng gói toàn bộ code thành Docker Images:


# 1. Build SoftHSM
docker build -t softhsm-service:latest -f ./softhsm/Dockerfile.softhsm ./softhsm

# 2. Build Payment Orchestrator (Laravel)
docker build -t payment_orchestrator:v1 ./services/payment_orchestrator

# 3. Build Order Service (Python FastAPI)
docker build -t merchant-backend:local ./services/order

# 4. Build Frontend (ReactJS)
docker build -t merchant-frontend:local ./frontend

Giai đoạn 4: Lắp ráp kiến trúc (Apply K8s YAML)
Giờ chúng ta đưa bản vẽ cho K8s tự động khởi chạy các Container:

kubectl apply -f infra/k8s/postgres-redis.yaml      # Khởi động DB
kubectl apply -f infra/k8s/softhsm-deployment.yaml  # Khởi động Két sắt
kubectl apply -f infra/k8s/payment-orchestrator.yaml # Khởi động Payment (Core)
kubectl apply -f infra/k8s/merchant-app.yaml        # Khởi động Web & Order Service

Giai đoạn 5: Kích hoạt đường hầm mạng (Port Forwarding)
Vì chạy ở Local, anh em cần đục lỗ mạng để trình duyệt ở ngoài có thể gọi vào hệ thống bên trong K8s. Mở 2 Tab Terminal mới và chạy song song 2 lệnh này (treo máy ở đó):

# Terminal 1: Đục lỗ cho API Order Service (Backend Merchant)
kubectl port-forward svc/merchant-backend-svc 5000:5000 -n merchant-site

# Terminal 2: Đục lỗ cho Frontend (Giao diện ReactJS)
kubectl port-forward svc/merchant-frontend-svc 8080:80 -n merchant-site