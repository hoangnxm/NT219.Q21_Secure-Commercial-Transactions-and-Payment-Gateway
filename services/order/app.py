from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import httpx # THÊM THƯ VIỆN NÀY ĐỂ GỌI API
import time
import hmac
import hashlib
from sqlalchemy import Column, String, Integer, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./orders.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

PAYMENT_ORCHESTRATOR_URL = "http://localhost:8000/api/payments/charge"
SOFTHSM_SIGNER_URL = "http://localhost:8888/api/sign" 
HMAC_SECRET = b"chuoi_bi_mat_cua_nhom_NT219"

class Product(Base):
    __tablename__ = "products"
    id = Column(String, primary_key=True)
    name = Column(String)
    stock = Column(Integer)
    price = Column(Integer)

class Order(Base):
    __tablename__ = "orders"
    id = Column(String, primary_key=True)
    product_id = Column(String)
    quantity = Column(Integer)
    amount = Column(Integer)
    payment_token = Column(String)

Base.metadata.create_all(bind=engine)

db = SessionLocal()
if not db.query(Product).filter(Product.id == "iphone-15").first():
    iphone = Product(id="iphone-15", name="iPhone 15", stock=10, price=500000)
    db.add(iphone)
    db.commit()
db.close()

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class CheckoutRequest(BaseModel):
    product_id: str
    quantity: int
    payment_token: str

@app.post("/api/orders/create")
async def create_order(request: CheckoutRequest):
    db = SessionLocal()
    
    # 1. TÍNH TOÁN & KIỂM TRA KHO (RESERVE STOCK)
    product = db.query(Product).filter(Product.id == request.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm")
    if product.stock < request.quantity:
        raise HTTPException(status_code=400, detail="Hết hàng!")

    # 2. GIỮ CHỖ KHO
    product.stock -= request.quantity
    order_id = str(uuid.uuid4())
    total_amount = product.price * request.quantity

    async with httpx.AsyncClient() as client:
        try:
            pay_payload = {
                "order_id": order_id, 
                "amount": total_amount, 
                "payment_token": request.payment_token
            }
            pay_resp = await client.post(PAYMENT_ORCHESTRATOR_URL, json=pay_payload, timeout=10.0)
            
            if pay_resp.status_code != 200:
                product.stock += request.quantity
                db.commit()
                raise HTTPException(status_code=400, detail=f"Thanh toán Stripe thất bại: {pay_resp.text}")
                
        except Exception as e:
            product.stock += request.quantity
            db.commit()
            raise HTTPException(status_code=500, detail=f"Không kết nối được Payment Orchestrator: {str(e)}")

    new_order = Order(
        id=order_id, product_id=request.product_id,
        quantity=request.quantity, amount=total_amount,
        payment_token=request.payment_token
    )
    db.add(new_order)
    db.commit()
    print(f"✅ Đã trừ tiền và tạo đơn {order_id}. Kho còn: {product.stock}")

    real_jws_receipt = ""
    payload_str = f'{{"payload": "HoaDon_{order_id}_{total_amount}VND"}}'
    
    timestamp = int(time.time())
    nonce = uuid.uuid4().hex
    data_to_hash = f"{timestamp}.{nonce}.{payload_str}".encode('utf-8')
    signature = hmac.new(HMAC_SECRET, data_to_hash, hashlib.sha256).hexdigest()

    headers =headers = {
        "Content-Type": "application/json",
        "X-Signature": signature,
        "X-Timestamp": str(timestamp),
        "X-Nonce": nonce
    }