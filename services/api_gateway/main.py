from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import uvicorn
from fastapi.responses import Response

app = FastAPI(title="Payment API Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

cert_path = ('/certs/client.crt', '/certs/client.key')
# ca_cert_path = '../certs/ca.crt' 

# Ống dẫn xài chung
client = httpx.AsyncClient(cert=cert_path, verify=False)

# SỬA LẠI THÀNH CỔNG 80 ĐỂ KHỚP VỚI K8S SERVICE CỦA ORCHESTRATOR
SERVICES = {
    "payment": "https://payment-orchestrator-service:80",
    "fraud": "https://fraud-engine-service:8001"
}

@app.api_route("/{service_name}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def dynamic_router(service_name: str, path: str, request: Request):
    if service_name not in SERVICES:
        raise HTTPException(status_code=404, detail="Service không tồn tại")
    
    clean_path = f"/{path}" if not path.startswith("/") else path
    target_url = f"{SERVICES[service_name]}{clean_path}"
    
    body = await request.body() # Lấy byte thô để giữ nguyên chữ ký Stripe
    headers = dict(request.headers)
    headers.pop("host", None) 

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
        print(f"🔥 LỖI mTLS: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Lỗi khớp nối: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=443, # Đổi sang cổng HTTPS
        ssl_keyfile="/certs/server.key",
        ssl_certfile="/certs/server.crt"
        # Cố tình không dùng ssl_ca_certs và ssl_cert_reqs để client không bị đòi thẻ
    )