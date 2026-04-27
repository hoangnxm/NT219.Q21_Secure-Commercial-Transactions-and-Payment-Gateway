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

# THAY ĐỔI 1: Bơm thẻ ngành mTLS vào HTTPX Client
cert_path = ('/certs/client.crt', '/certs/client.key')
client = httpx.AsyncClient(cert=cert_path, verify=False)

# THAY ĐỔI 2: Đổi giao thức Khớp nối thành HTTPS
SERVICES = {
    "payment": "https://payment-orchestrator-service:80",
    "fraud": "https://fraud-engine-service:8001"
}

# Route mở rộng để tự do thêm các khớp nối khác
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