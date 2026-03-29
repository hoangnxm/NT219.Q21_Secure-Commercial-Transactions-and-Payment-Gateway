from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import httpx 
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

PAYMENT_ORCHESTRATOR_URL = "http://host.docker.internal/api/payments/charge"
SOFTHSM_SIGNER_URL = "http://localhost:8443/api/sign" 
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
    email = Column(String)
    quantity = Column(Integer)
    amount = Column(Integer)
    payment_token = Column(String)
    status = Column(String, default="PENDING")  

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class CheckoutRequest(BaseModel):
    product_id: str
    quantity: int
    email: str
    payment_token: str

@app.post("/api/orders/create")
async def create_order(request: CheckoutRequest):
    db = SessionLocal()
    
    # 1. TÌM VÀ KHÓA DÒNG DỮ LIỆU SẢN PHẨM (Pessimistic Locking)
    product = db.query(Product).filter(Product.id == request.product_id).with_for_update().first()
    
    if not product:
        db.close()
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm")
    if product.stock < request.quantity:
        db.close()
        raise HTTPException(status_code=400, detail="Hết hàng!")

    # 2. GIỮ CHỖ KHO VÀ CHỐT SỔ NGAY LẬP TỨC ĐỂ NHẢ KHÓA
    product.stock -= request.quantity
    db.commit() 
    
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"    
    total_amount = product.price * request.quantity

    # 3. GỌI PAYMENT ORCHESTRATOR ĐỂ TRỪ TIỀN
    async with httpx.AsyncClient() as client:
        try:
            pay_payload = {
                "order_id": order_id, 
                "amount": total_amount, 
                "email": request.email,
                "payment_token": request.payment_token
            }

            response = await client.post(PAYMENT_ORCHESTRATOR_URL, json=pay_payload,  timeout=10.0)
            if response.status_code != 200:
                raise Exception("Thanh toán bị từ chối bởi Payment Gateway")
            
            # 4. GỌI SOFTHSM KÝ BIÊN LAI
            payload_str = f'{{"payload": "HoaDon_{order_id}_{total_amount}VND"}}'
                
            timestamp = str(int(time.time()))
            nonce = uuid.uuid4().hex
            data_to_hash = f"{timestamp}.{nonce}.{payload_str}".encode('utf-8')
            signature = hmac.new(HMAC_SECRET, data_to_hash, hashlib.sha256).hexdigest()
            
            headers = {
                "X-Signature": signature,
                "X-Timestamp": timestamp,
                "X-Nonce": nonce
            }

            res_sign = await client.post(
                SOFTHSM_SIGNER_URL, 
                content=payload_str,
                headers=headers,
                timeout=5.0
            )
            
            jws_receipt = res_sign.json().get("signature", "SIGNING_FAILED")
                
        except Exception as e:
            refund_product = db.query(Product).filter(Product.id == request.product_id).with_for_update().first()
            if refund_product:
                refund_product.stock += request.quantity
                db.commit()
            db.close()
            raise HTTPException(status_code=500, detail=f"Lỗi thanh toán, đã hoàn lại kho: {str(e)}")

    # 5. LƯU ĐƠN HÀNG VÀO DB
    new_order = Order(
        id=order_id, product_id=request.product_id,
        email=request.email,quantity=request.quantity, 
        amount=total_amount,payment_token=request.payment_token,
        status="SUCCESS"
    )
    db.add(new_order)
    db.commit()
    print(f"✅ Đã trừ tiền và tạo đơn {order_id}. Kho còn: {product.stock}")

    db.close()
    
    return {
        "status": "success", 
        "order_id": order_id, 
        "amount": total_amount,
        "jws_receipt": jws_receipt
    }
