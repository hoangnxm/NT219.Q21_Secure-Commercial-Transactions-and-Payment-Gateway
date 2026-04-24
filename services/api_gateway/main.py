# api_gateway/main.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import uvicorn
from fastapi.responses import Response

app = FastAPI(title="Payment API Gateway")

# Quan trọng: Thêm CORS để Frontend (Vite) gọi không bị chặn
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = httpx.AsyncClient()

# Khớp nối nội bộ trong Kubernetes
SERVICES = {
    "order": "http://order-service:8080",
    "payment": "http://payment-orchestrator-service:8080",
    "fraud": "http://fraud-engine-service:8001"
}

# 1. Route riêng cho Frontend lấy products (Giữ nguyên path để Frontend ít phải sửa nhất)
@app.api_route("/api/products", methods=["GET"])
async def route_products(request: Request):
    return await forward_request("order", "/api/products", request)

# 2. Route mở rộng để mày tự do thêm các khớp nối khác
# Frontend có thể gọi /order/api/xyz, Stripe gọi webhook qua /payment/webhook
@app.api_route("/{service_name}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def dynamic_router(service_name: str, path: str, request: Request):
    if service_name not in SERVICES:
        raise HTTPException(status_code=404, detail="Service không tồn tại")
    return await forward_request(service_name, f"/{path}", request)

async def forward_request(service_name: str, path: str, request: Request):
    target_url = f"{SERVICES[service_name]}{path}"
    body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None) # Gỡ host cũ để tránh kẹt tín hiệu

    try:
        response = await client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body,
            params=request.query_params
        )
        return Response(
            content=response.content, 
            status_code=response.status_code, 
            headers=dict(response.headers)
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Lỗi khớp nối tới {service_name}: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80)