from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
from sqlalchemy import Column, String, Integer, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./orders.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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

    # 2. GIỮ CHỖ (RESERVE)
    product.stock -= request.quantity
    
    # 3. TẠO ĐƠN HÀNG
    order_id = str(uuid.uuid4())
    total_amount = product.price * request.quantity
    
    new_order = Order(
        id=order_id, product_id=request.product_id,
        quantity=request.quantity, amount=total_amount,
        payment_token=request.payment_token
    )
    
    db.add(new_order)
    db.commit()
    print(f"✅ Đã giữ chỗ & tạo đơn {order_id}. Kho còn: {product.stock}")
    db.close()
    return {
        "status": "success", 
        "order_id": order_id, 
        "amount": total_amount,
        "jws_receipt": f"eyJhbGciOiJSUzI1NiJ9.eyJvcmRlciI6I... (Giả lập)"
    }