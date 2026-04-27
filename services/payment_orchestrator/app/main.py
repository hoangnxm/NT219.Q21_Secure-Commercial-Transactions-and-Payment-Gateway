# services/payment_orchestrator/app/main.py
import os
import json
import time
import hmac
import hashlib
import secrets
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import httpx
import stripe
from pydantic import BaseModel

from app.models import Base, Order, AuditLog
from app.schemas import ChargeRequest, CancelRequest

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@postgres-db/payment_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

stripe.api_key = os.getenv("STRIPE_SECRET")
HMAC_SECRET = os.getenv("HMAC_SECRET", "chuoi_bi_mat_cua_nhom_NT219")

# ---------------------------------------------------------
# CẤU HÌNH THẺ NGÀNH (mTLS) CHO CHIỀU GỌI ĐI
# ---------------------------------------------------------
CERT_PATH = ('/certs/client.crt', '/certs/client.key')
VERIFY_CA = '/certs/ca.crt' 

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 1. API Charge
@app.post("/api/payments/charge")
async def charge(req_data: ChargeRequest, request: Request, db: Session = Depends(get_db)):
    email = req_data.email.strip()
    
    user_agent = request.headers.get('User-Agent', '').lower()
    device = "Mobile" if "mobile" in user_agent else "Desktop"
    
    time_threshold = datetime.utcnow() - timedelta(minutes=30)
    failed_attempts = db.query(Order).filter(
        Order.email == email, 
        Order.status == 'FAILED',
        Order.created_at >= time_threshold
    ).count()

    fraud_payload = {
        "amount": req_data.amount,
        "email": email,
        "ip_address": request.client.host or "127.0.0.1",
        "device": device,
        "failed_attempts": failed_attempts,
        "hour_of_day": datetime.utcnow().hour
    }

    try: 
        # THAY ĐỔI 1: Rút thẻ ngành gọi sang Fraud Engine qua HTTPS
        async with httpx.AsyncClient(cert=CERT_PATH, verify=VERIFY_CA) as client:
            fraud_res = await client.post('https://fraud-engine-service:8001/api/fraud/score', json=fraud_payload, timeout=5.0)
            fraud_data = fraud_res.json()
            
        if fraud_data['action'] == "block":
            return {"error": "Giao dịch bị từ chối", "fraud_score": fraud_data['score']}
        
        new_order = Order(
            order_id = req_data.order_id,
            email = email,
            amount = req_data.amount,
            fraud_score = fraud_data['score'],
            fraud_action = fraud_data['action'],
            status = 'PENDING',
            jws_signature = 'PENDING_PAYMENT'
        )
        db.add(new_order)
        db.commit()
        
        payment_intent = stripe.PaymentIntent.create(
            amount = int(req_data.amount),
            currency = 'vnd',
            receipt_email = email,
            metadata = {'order_id':req_data.order_id}
        )
        new_order.stripe_payment_id = payment_intent.id
        db.commit()
        
        return {
            "status": "success", "order_id": new_order.order_id, "amount": new_order.amount,
            "client_secret": payment_intent.client_secret, "fraud_score": fraud_data['score']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Lỗi kết nối", "msg": str(e)})

# 2. Webhook Stripe
@app.post("/api/webhook/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret) 
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid webhook")

    payment_intent = event['data']['object']
    order = db.query(Order).filter(Order.stripe_payment_id == payment_intent['id']).first()

    if event['type'] == 'payment_intent.succeeded' and order and order.status != 'SUCCESS':
        order.status = 'SUCCESS'

        try:
            order_info = f"Order:{order.order_id}|Amount:{order.amount}|StripeID:{payment_intent['id']}"
            data_to_send = {'payload': order_info}
            final_json = json.dumps(data_to_send, separators=(',', ':'))
            
            timestamp = str(int(time.time()))
            nonce = secrets.token_hex(16)
            data_to_hash = f"{timestamp}.{nonce}.{final_json}"
            signature = hmac.new(HMAC_SECRET.encode(), data_to_hash.encode(), hashlib.sha256).hexdigest()

            # THAY ĐỔI 2: Đổi đường dẫn chứng chỉ cho đồng bộ với Master Secret
            async with httpx.AsyncClient(cert=CERT_PATH, verify=VERIFY_CA) as hsm_client:
                sign_res = await hsm_client.post(
                    'https://softhsm:8443/api/sign',
                    headers={'X-Signature': signature, 'X-Timestamp': timestamp, 'X-Nonce': nonce,'Content-Type': 'application/json'},
                    content=final_json
                )
                if sign_res.status_code == 200:
                    order.jws_signature = sign_res.json().get('signature', 'SIGNING FAILED')
                else:
                    order.jws_signature = 'SIGNING FAILED'
        except Exception as e:
            print(f"Lỗi gọi HSM từ Webhook: {e}")
            order.jws_signature = 'HSM_OFFLINE_ERROR'
        db.commit()

    elif event['type'] == 'payment_intent.payment_failed' and order:
        order.status = 'FAILED'
        db.commit()
    return {"status": "success"}

# 3. Get Status
@app.get("/api/payments/status/{order_id}")
def get_status(order_id: str, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng")
    return {
        "order_id": order.order_id, 
        "amount": order.amount, 
        "status": order.status,
        "jws_signature": order.jws_signature
    }

# 4. Cancel Order
@app.post("/api/payments/cancel")
def cancel_order(req: CancelRequest, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.order_id == req.order_id).first()
    if order and order.status == 'PENDING':
        order.status = 'FAILED'
        db.commit()
        return {"message": "Đã hủy đơn hàng thành công"}
    raise HTTPException(status_code=400, detail="Không tìm thấy đơn hợp lệ để hủy")

# THAY ĐỔI 3: Giương khiên mTLS cho chiều nhận
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        ssl_keyfile="/certs/server.key",
        ssl_certfile="/certs/server.crt",
        ssl_ca_certs="/certs/ca.crt",
        ssl_cert_reqs=2
    )