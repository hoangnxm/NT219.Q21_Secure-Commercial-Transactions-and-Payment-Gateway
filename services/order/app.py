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

PAYMENT_ORCHESTRATOR_URL = "http://api-gateway-service.nt219-project.svc.cluster.local/payment/api/payments/charge"
PAYMENT_CHECK_URL = "http://api-gateway-service.nt219-project.svc.cluster.local/payment/api/payments/status/"

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
    status = Column(String, default="PENDING")  

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class CheckoutRequest(BaseModel):
    product_id: str
    quantity: int
    email: str

class ConfirmRequest(BaseModel):
    order_id: str

# ==========================================
# MODULE 1: KHỞI TẠO ĐƠN HÀNG (CHƯA KÝ SOFTHSM)
# ==========================================
@app.post("/api/orders/create")
async def create_order(request: CheckoutRequest):
    db = SessionLocal()

    try:
        product = db.query(Product).filter(Product.id == request.product_id).with_for_update().first()
        if not product:
            db.close()
            raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm")
        if product.stock < request.quantity:
            db.close()
            raise HTTPException(status_code=400, detail="Hết hàng!")

        product.stock -= request.quantity
        db.commit()

        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"    
        total_amount = product.price * request.quantity

        async with httpx.AsyncClient(timeout=30.0) as client:
            pay_payload = {
                "order_id": order_id,
                "amount": total_amount,
                "email": request.email,
            }
            headers = {"Accept": "application/json"}

            response = await client.post(PAYMENT_ORCHESTRATOR_URL, json=pay_payload, headers=headers)
            if response.status_code != 200:
                raise Exception(f"Thanh toán bị từ chối: {response.text}")
            pay_data = response.json()
            client_secret = pay_data.get("client_secret")

        # LƯU ĐƠN HÀNG VỚI TRẠNG THÁI PENDING (CHỜ KHÁCH QUẸT THẺ)
        new_order = Order(
            id=order_id, product_id=request.product_id,
            email=request.email, quantity=request.quantity,
            amount=total_amount,
            status="PENDING"
        )

        db.add(new_order)
        db.commit()

        print(f"✅ Đã tạo đơn {order_id} (PENDING). Kho còn: {product.stock}")

        # KHÔNG GỌI SOFTHSM Ở ĐÂY NỮA
        return {
            "status": "success",
            "order_id": order_id,   
            "amount": total_amount,
            "client_secret": client_secret
        }
       
    except Exception as e:
        db.rollback()
        refund_product = db.query(Product).filter(Product.id == request.product_id).with_for_update().first()
        if refund_product:
            refund_product.stock += request.quantity
            db.commit()
        raise HTTPException(status_code=500, detail=f"Lỗi khởi tạo đơn: {str(e)}")
    finally:
        db.close()

# ==========================================
# MODULE 2: XÁC THỰC THÀNH CÔNG VÀ KÝ BIÊN LAI
# ==========================================
@app.post("/api/orders/confirm")
async def confirm_order(request: ConfirmRequest):
    db = SessionLocal()
    try:
        # TÌM LẠI ĐƠN HÀNG ĐANG CHỜ
        order = db.query(Order).filter(Order.id == request.order_id).with_for_update().first()
        if not order:
            raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng")
        
        if order.status == "SUCCESS":
            return {"status": "success", "message": "Đơn hàng đã được xác nhận từ trước"}
        
        # CẬP NHẬT TRẠNG THÁI THÀNH CÔNG
        order.status = "SUCCESS"
        db.commit()

        print(f"✅ Đã đồng bộ trạng thái thanh toán cho đơn {order.id}")

        return {
            "status": "success",
            "order_id": order.id,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi xác nhận: {str(e)}")
    finally:
        db.close()

# ==========================================
# PHẦN API QUẢN LÝ SẢN PHẨM & ĐỐI SOÁT
# ==========================================
class ProductCreateRequest(BaseModel):
    id: str
    name: str
    stock: int
    price: int

@app.post("/api/products")
async def add_product(request: ProductCreateRequest):
    db = SessionLocal()
    try:
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
        raise HTTPException(status_code=500, detail=f"Lỗi thêm sản phẩm: {str(e)}")
    finally:
        db.close()

@app.get("/api/products")
async def get_products():
    db = SessionLocal()
    products =  db.query(Product).filter(Product.stock > 0).all() 
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

@app.get("/api/orders/reconcile")
def reconcile_orders():
    db = SessionLocal()
    
    report = {
        "total_checked" : 0,
        "matched" : [], 
        "mismatched": [], 
        "missing_in_gw": [] 
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)