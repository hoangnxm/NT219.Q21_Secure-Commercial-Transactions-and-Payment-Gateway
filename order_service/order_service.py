from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import uuid

app = FastAPI()

# 1. Bật CORS để cho phép Frontend React (chạy port khác) gọi API vào đây
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Đang code ở local nên cứ mở cho thoáng
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khai báo cấu trúc dữ liệu gửi lên từ React (khớp y xì với file App.jsx)
class OrderRequest(BaseModel):
    product_id: str
    quantity: int
    payment_token: str

# Bảng giá giả lập (sau này ông có thể móc từ Database)
PRODUCT_PRICES = {
    "iphone-15": 20000000, # 20 củ
    "macbook-pro": 45000000
}

# Địa chỉ cái Payment Orchestrator (Laravel) của lão Ngô Hoàng
ORCHESTRATOR_URL = "http://localhost:8000/api/payments/charge"

@app.post("/api/orders/create")
async def create_order(request: OrderRequest):
    print(f"\n🚀 [ORDER SERVICE] Nhận yêu cầu mua {request.quantity} x {request.product_id}")
    
    # 2. Tính toán tiền bạc & Trừ kho
    if request.product_id not in PRODUCT_PRICES:
        raise HTTPException(status_code=400, detail="Sản phẩm không tồn tại trong kho!")
    
    amount = PRODUCT_PRICES[request.product_id] * request.quantity
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    
    # 💡 CHỖ NÀY DÀNH CHO ÔNG:
    # Viết lệnh Insert thông tin (order_id, amount) vào bảng PostgreSQL ở đây nhé!
    print(f"📦 [DB] Đã lưu đơn hàng {order_id} với tổng tiền: {amount} VND")

    # 3. Đá thông tin sang Laravel Orchestrator để lo phần Thanh Toán
    print(f"💸 [PAYMENT] Đang gửi Token sang Orchestrator (Port 8000)...")
    
    async with httpx.AsyncClient() as client:
        try:
            # Gửi request sang cổng 8000
            response = await client.post(ORCHESTRATOR_URL, json={
                "order_id": order_id,
                "amount": amount,
                "payment_token": request.payment_token
            }, timeout=15.0)
            
            # Lấy kết quả từ Laravel trả về
            orchestrator_data = response.json()
            
            # 4. Trả kết quả cuối cùng về cho màn hình React
            if response.status_code == 200 and orchestrator_data.get("status") == "success":
                return {
                    "status": "success",
                    "order_id": order_id,
                    "amount": amount,
                    "jws_receipt": orchestrator_data.get("jws_receipt", "Đợi lão Đăng ráp HSM sẽ có chữ ký JWS ở đây")
                }
            else:
                return {
                    "status": "failed",
                    "detail": orchestrator_data.get("reason", "Giao dịch bị từ chối từ Orchestrator")
                }
                
        except httpx.RequestError as exc:
            print(f"❌ Chết dở, không gọi được Laravel: {exc}")
            raise HTTPException(status_code=500, detail="Mất kết nối với Payment Orchestrator. Sếp Ngô Hoàng đã bật cổng 8000 chưa?")

if __name__ == "__main__":
    import uvicorn
    # Chạy đúng cổng 8001 để Frontend React gọi tới
    print("🔥 Khởi động Order Service tại http://localhost:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)