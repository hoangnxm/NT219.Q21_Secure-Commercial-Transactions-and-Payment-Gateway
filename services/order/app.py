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
import os
from requests.adapters import HTTPAdapter
import requests
import ssl
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DATABASE_URL = "sqlite:///./orders.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()



PAYMENT_ORCHESTRATOR_URL = "http://localhost/api/payments/charge"
SOFTHSM_SIGNER_URL = "https://localhost:8443/api/sign"
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

# ==========================================
# PHẦN API MUA ĐƠN HÀNG
# ==========================================

@app.post("/api/orders/create")

async def create_order(request: CheckoutRequest):
    db = SessionLocal()

    try:
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
        async with httpx.AsyncClient(timeout=30.0) as client:
            pay_payload = {
                "order_id": order_id,
                "amount": total_amount,
                "email": request.email,
                "payment_token": request.payment_token
            }

            response = await client.post(PAYMENT_ORCHESTRATOR_URL, json=pay_payload)
            if response.status_code != 200:
                raise Exception(f"Thanh toán bị từ chối: {response.text}")
            pay_data = response.json()
            client_secret = pay_data.get("client_secret")

       
        # 4. GỌI SOFTHSM KÝ BIÊN LAI
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        ca_path = os.path.join(BASE_DIR, "ca.crt")
        cert_path = os.path.join(BASE_DIR, "client.crt")
        key_path = os.path.join(BASE_DIR, "client.key")

        payload_str = f'{{"payload": "HoaDon_{order_id}_{total_amount}VND"}}'          
        timestamp = str(int(time.time()))
        nonce = uuid.uuid4().hex
        data_to_hash = f"{timestamp}.{nonce}.{payload_str}".encode('utf-8')
        signature = hmac.new(HMAC_SECRET, data_to_hash, hashlib.sha256).hexdigest()

        headers = {
            "X-Signature": signature,
            "X-Timestamp": timestamp,
            "X-Nonce": nonce,
            "Content-Type": "application/json"
        }

        # TẠO BỘ LỌC ĐỂ BỎ QUA CHECK "LOCALHOST" NHƯNG VẪN CHECK CA
        class HostNameIgnoreAdapter(HTTPAdapter):
            def init_poolmanager(self, *args, **kwargs):
                context = ssl.create_default_context(cafile=ca_path)
                context.load_cert_chain(certfile=cert_path, keyfile=key_path)
                context.check_hostname = False # TẮT SOI TÊN MIỀN Ở ĐÂY
                kwargs['ssl_context'] = context
                return super(HostNameIgnoreAdapter, self).init_poolmanager(*args, **kwargs)

            def cert_verify(self, conn, url, verify, cert):
                conn.assert_hostname = False
                return super(HostNameIgnoreAdapter, self).cert_verify(conn, url, verify, cert)
            
        with requests.Session() as session:
            session.mount('https://', HostNameIgnoreAdapter())
            # Gọi SoftHSM bằng session đã được độ lại
            res_sign = session.post(SOFTHSM_SIGNER_URL, data=payload_str, headers=headers, timeout=30)

        if res_sign.status_code != 200:
            raise Exception(f"SoftHSM lỗi {res_sign.status_code}: {res_sign.text}")

        jws_receipt = res_sign.json().get("signature", "SIGNING_FAILED")
        
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

        return {
        "status": "success",
        "order_id": order_id,   
        "amount": total_amount,
        "jws_receipt": jws_receipt,
        "client_secret": client_secret
        }
       
    except Exception as e:
        db.rollback()
        
        try:
            # Gửi tín hiệu hủy sang Laravel
            requests.post("http://localhost/api/payments/cancel", json={"order_id": order_id}, timeout=5)
        except Exception as cancel_err:
            print(f"Không thể báo Laravel hủy đơn: {cancel_err}")
        
        refund_product = db.query(Product).filter(Product.id == request.product_id).with_for_update().first()
        
        if refund_product:
            refund_product.stock += request.quantity
            db.commit()
        raise HTTPException(status_code=500, detail=f"Lỗi thanh toán, đã hoàn lại kho: {str(e)}")

    finally:
        db.close()


# ==========================================
# PHẦN API QUẢN LÝ SẢN PHẨM
# ==========================================
class ProductCreateRequest(BaseModel):
    id: str
    name: str
    stock: int
    price: int



# API để shop thêm sản phẩm vào kho

@app.post("/api/products")

async def add_product(request: ProductCreateRequest):
    db = SessionLocal()
    try:
        # Check có hàng chưa
        existing = db.query(Product).filter(Product.id == request.id).first()
        if existing:
            existing.stock += request.stock
            existing.price = request.price
            existing.name = request.name
        else:
            new_prod = Product(
                id = request.id,
                name = request.name,
                stock = request.stock,
                price = request.price
            )
            db.add(new_prod)
        db.commit()

        return {"status":"success","message":f"Đã nhập kho {request.name}"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi thanh toán, đã hoàn lại kho: {str(e)}")
    finally:
        db.close()

       

# API cho Frontend gọi để lấy danh sách hàng show lên Web

@app.get("/api/products")
async def get_products():
    db = SessionLocal()
    products =  db.query(Product).filter(Product.stock > 0).all() # Lấy hàng còn
    db.close()


    result =  []
    for p in products:
        result.append({
            "id": p.id,
            "name": p.name,
            "stock": p.stock,
            "price": p.price
        })
        
    return {"status":"success","data": result}

# ==========================================
# PHẦN ĐỐI SOÁT GIAO DỊCH
# ==========================================

PAYMENT_CHECK_URL = "http://localhost/api/payments/status/"

@app.get("/api/orders/reconcile")
def reconcile_orders():
    db = SessionLocal()
    
    report = {
        "total_checked" : 0,
        "matched" : [], # Khớp
        "mismatched": [], # Ko đúng trạng thái
        "missing_in_gw": [] # Có trên FastAPI nhưng backend chưa biết
    }
    
    try:
        orders = db.query(Order).all()
        
        for order in orders:
            report["total_checked"] += 1
            
            try:
                res = requests.get(f"{PAYMENT_CHECK_URL}{order.id}", timeout=5)
                
                if res.status_code == 404:
                    report["missing_in_gw"].append(order.id)
                    continue
                
                gw_data = res.json()
                gw_status = gw_data.get("status")
                gw_amount = gw_data.get("amount")
                
                # Bắt đầu đối soát
                if order.status == gw_status and float(order.amount) == float(gw_amount):
                    report["matched"].append(order.id)
                else:
                    report["mismatched"].append({
                        "order_id": order.id,
                        "local_status": order.status,
                        "local_amount": order.amount,
                        "gw_status": gw_status,
                        "gw_amount": gw_amount
                    })
            except Exception as e:
                report["mismatched"].append({
                    "order_id": order.id,
                    "error": f"Lỗi kết nối Laravel: {str(e)}"
                })
        return {"status": "success", "reconciliation_report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# Treo máy để lắng nghe cổng 5000, chờ Frontend gọi API tạo đơn hàng
if __name__ == "__main__":
    import uvicorn
    # Chạy server tại cổng 5000
    uvicorn.run(app, host="0.0.0.0", port=5000)