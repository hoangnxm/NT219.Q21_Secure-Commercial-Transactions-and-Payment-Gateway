from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import Product

DATABASE_URL = "sqlite:///./orders.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

db = SessionLocal()
iphone = db.query(Product).filter(Product.id == "iphone-15").first()

if iphone:
    iphone.stock = 20
    db.commit()
    print(f"✅ Đã bơm hàng thành công! Kho hiện tại đang có: {iphone.stock} cái.")
else:
    print("❌ Không tìm thấy sản phẩm trong kho.")
    
db.close()