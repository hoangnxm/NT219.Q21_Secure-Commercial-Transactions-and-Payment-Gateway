import os
import json
import time
import hmac
import hashlib
import secrets
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request, Header, Depends
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import httpx
import stripe
from pydantic import BaseModel

from app.models import Base, Order, AuditLog
from app.schemas import ChargeRequest, CancelRequest

app = FastAPI()

# Cấu hình DB & Stripe
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@postgres-db/payment_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

stripe.api_key = os.getenv("STRIPE_SECRET")
HMAC_SECRET = os.getenv("HMAC_SECRET", "chuoi_bi_mat_cua_nhom_NT219")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper: Ghi log bảo mật ký bằng SoftHSM
async def log_security_event(event: str, data: dict, db: Session):
    payload_str = json.dumps(data)
    timestamp = str(int(time.time()))
    nonce = secrets.token_hex(16)
    
    # Tính HMAC
    data_to_hash = timestamp + payload_str
    signature = hmac.new(HMAC_SECRET.encode(), data_to_hash.encode(), hashlib.sha256).hexdigest()

    try:
        # Cấu hình mTLS tương tự Laravel
        #
        cert_path = ('/path/to/certs/client.crt', '/path/to/certs/client.key') 
        async with httpx.AsyncClient(cert=cert_path, verify=False) as client:
            res = await client.post(
                'https://softhsm.nt219-project.svc.cluster.local:8888/api/sign',
                headers={
                    'X-Signature': signature,
                    'X-Timestamp': timestamp,
                    'X-Nonce': nonce
                },
                json={'payload': payload_str}
            )
            if res.status_code == 200:
                audit_log = AuditLog(event=event, payload=payload_str, signature=res.json().get('signature'))
                db.add(audit_log)
                db.commit()
    except Exception as e:
        print(f"Lỗi ghi Audit Log: {e}")

# 1. API Charge
@app.post("/api/payments/charge")
async def charge(req_data: ChargeRequest, request: Request, db: Session = Depends(get_db)):
    email = req_data.email.strip()
    
    # Phân tích thiết bị
    user_agent = request.headers.get('User-Agent', '').lower()
    device = "Mobile" if "mobile" in user_agent else "Desktop"
    
    # Đếm số lần thất bại 30p qua
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
        # Gọi Fraud Engine
        async with httpx.AsyncClient() as client:
            fraud_res = await client.post(
                'http://fraud-engine-service.nt219-project.svc.cluster.local:8001/api/fraud/score',
                json=fraud_payload,
                timeout=5.0
            )
            if fraud_res.status_code != 200:
                raise HTTPException(status_code=500, detail={"error": "AI bị lỗi", "detail": fraud_res.text})
            
            fraud_data = fraud_res.json()
            
            order_status = 'FRAUD_BLOCKED' if fraud_data['action'] == 'block' else 'PENDING'
            
            new_order = Order(
                order_id=req_data.order_id,
                email=email,
                amount=req_data.amount,
                fraud_score=fraud_data['score'],
                fraud_action=fraud_data['action'],
                status=order_status
            )
            db.add(new_order)
            db.commit()
            
            if fraud_data['action'] == 'block':
                await log_security_event('FRAUD_BLOCK_ACTION', {
                    'order_id': req_data.order_id,
                    'email': email,
                    'fraud_score': fraud_data['score'],
                    'reason': fraud_data.get('reason'),
                    'ip': request.client.host
                }, db)
                return {"error": "Giao dịch bị từ chối do rủi ro gian lận cao", "fraud_score": fraud_data['score']}

            force_3ds = (fraud_data['action'] == 'force_3ds')

            # Chuyển tiếp Stripe
            payment_intent = stripe.PaymentIntent.create(
                amount=int(req_data.amount), # Lưu ý: Stripe dùng số nguyên (VND không có cent)
                currency='vnd',
                receipt_email=email,
                metadata={'order_id': req_data.order_id, 'fraud_score': fraud_data['score']},
                payment_method_options={
                    'card': {'request_three_d_secure': 'any' if force_3ds else 'automatic'}
                }
            )

            # Ký số mTLS qua SoftHSM
            jws_signature = 'HSM_OFFLINE_TEMP'
            try:
                order_info = f"Order:{req_data.order_id}|Amount:{req_data.amount}|StripeID:{payment_intent.id}"
                data_to_send = {'payload': order_info}
                final_json = json.dumps(data_to_send, separators=(',', ':'))
                
                timestamp = str(int(time.time()))
                nonce = secrets.token_hex(16)
                data_to_hash = f"{timestamp}.{nonce}.{final_json}"
                signature = hmac.new(HMAC_SECRET.encode(), data_to_hash.encode(), hashlib.sha256).hexdigest()

                cert_path = ('/path/to/certs/client.crt', '/path/to/certs/client.key')
                async with httpx.AsyncClient(cert=cert_path, verify=False) as hsm_client:
                    sign_res = await hsm_client.post(
                        'https://softhsm.nt219-project.svc.cluster.local:8888/api/sign',
                        headers={'X-Signature': signature, 'X-Timestamp': timestamp, 'X-Nonce': nonce},
                        content=final_json
                    )
                    if sign_res.status_code == 200:
                        jws_signature = sign_res.json().get('signature', 'SIGNING FAILED')
                    else:
                        jws_signature = 'SIGNING FAILED'
            except Exception as e:
                print(f"HSM Error: {e}")
            
            new_order.stripe_payment_id = payment_intent.id
            new_order.jws_signature = jws_signature
            db.commit()

            return {
                "status": "success",
                "order_id": new_order.order_id,
                "amount": new_order.amount,
                "client_secret": payment_intent.client_secret,
                "fraud_score": fraud_data['score'],
                "action": fraud_data['action'],
                "jws_receipt": jws_signature
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Lỗi kết nối Fraud Engine", "msg": str(e)})

# 2. Webhook Stripe
@app.post("/api/webhook/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret) # Xác minh chữ ký
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    payment_intent = event['data']['object']
    order = db.query(Order).filter(Order.stripe_payment_id == payment_intent['id']).first()

    if event['type'] == 'payment_intent.succeeded' and order:
        order.status = 'SUCCESS'
        await log_security_event('PAYMENT_SUCCESS_FINAL', {
            'order_id': order.order_id,
            'stripe_id': payment_intent['id']
        }, db)
    elif event['type'] == 'payment_intent.payment_failed' and order:
        order.status = 'FAILED'
        await log_security_event('PAYMENT_FAILED_ALERT', {
            'order_id': order.order_id,
            'stripe_id': payment_intent['id']
        }, db)
    
    db.commit()
    return {"status": "success"}

# 3. Get Status
@app.get("/api/payments/status/{order_id}")
def get_status(order_id: str, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng")
    return {"order_id": order.order_id, "amount": order.amount, "status": order.status}

# 4. Cancel Order
@app.post("/api/payments/cancel")
def cancel_order(req: CancelRequest, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.order_id == req.order_id).first()
    if order and order.status == 'PENDING':
        order.status = 'FAILED'
        db.commit()
        return {"message": "Đã hủy đơn hàng thành công"}
    raise HTTPException(status_code=400, detail="Không tìm thấy đơn hợp lệ để hủy")