from sqlalchemy import Column, Integer, String, Numeric, Text, DateTime, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, unique=True, index=True)
    email = Column(String)
    amount = Column(Numeric(15, 2))
    fraud_score = Column(Integer, nullable=True)
    fraud_action = Column(String, nullable=True)
    stripe_payment_id = Column(String, nullable=True)
    status = Column(String, default="PENDING")
    jws_signature = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    event = Column(String)
    payload = Column(Text)
    signature = Column(Text)
    created_at = Column(DateTime, default=func.now())