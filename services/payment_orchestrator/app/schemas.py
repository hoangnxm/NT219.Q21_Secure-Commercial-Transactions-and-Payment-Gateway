from pydantic import BaseModel

class ChargeRequest(BaseModel):
    amount: float
    order_id: str
    email: str

class CancelRequest(BaseModel):
    order_id: str