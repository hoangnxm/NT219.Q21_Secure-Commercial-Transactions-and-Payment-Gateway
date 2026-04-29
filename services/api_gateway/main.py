from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import uvicorn
from fastapi.responses import Response
import traceback
import ssl

app = FastAPI(title="Payment API Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# httpx dùng SSL Context chuẩn TLS 1.3
ssl_ctx = ssl.create_default_context(cafile='/certs/ca.crt')
ssl_ctx.load_cert_chain(certfile='/certs/client.crt', keyfile='/certs/client.key')
# Cho phép httpx đưa chứng chỉ ra khi Uvicorn đòi (PHA)
ssl_ctx.post_handshake_auth = True 

# Đưa SSL Context bảo mật cao nhất vào httpx
client = httpx.AsyncClient(verify=ssl_ctx)

# SỬA LẠI THÀNH CỔNG 80 ĐỂ KHỚP VỚI K8S SERVICE CỦA ORCHESTRATOR
SERVICES = {
    "payment": "https://payment-orchestrator-service:80",
}

@app.api_route("/{service_name}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def dynamic_router(service_name: str, path: str, request: Request):
    if service_name not in SERVICES:
        raise HTTPException(status_code=404, detail="Service không tồn tại")
    
    # clean_path = f"/{path}" if not path.startswith("/") else path
    target_url = f"{SERVICES[service_name]}/{path}"
    
    print(f"DEBUG: Gateway forwarding to -> {target_url}")
    
    body = await request.body() # Lấy byte thô để giữ nguyên chữ ký Stripe
    
    headers = {}
    for k, v in request.headers.items():
        if k.lower() not in ["host", "content-length", "transfer-encoding", "connection", "keep-alive"]:
            headers[k] = v

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
        print("🔥 LỖI GATEWAY BẮT ĐƯỢC:")
        traceback.print_exc()
        raise HTTPException(status_code=503, detail=f"Lỗi khớp nối: {repr(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8443, # Đổi sang cổng HTTPS
        ssl_keyfile="/certs/server.key",
        ssl_certfile="/certs/server.crt",
        ssl_ca_certs="/certs/ca.crt"
        # Cố tình không dùng ssl_ca_certs và ssl_cert_reqs để client không bị đòi thẻ
    )