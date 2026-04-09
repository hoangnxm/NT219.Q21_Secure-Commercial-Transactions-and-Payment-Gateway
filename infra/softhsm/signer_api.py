import os
import hmac
import hashlib
import base64
import time
import pkcs11
from fastapi import FastAPI, HTTPException, Request, Header, Depends
from pydantic import BaseModel
from cachetools import TTLCache # Thư viện thay thế Redis

app = FastAPI()
lib = pkcs11.lib('/usr/lib/x86_64-linux-gnu/softhsm/libsofthsm2.so')
SHARED_SECRET = os.getenv("HMAC_SECRET", "chuoi_bi_mat_cua_nhom_NT219").encode('utf-8')
MAX_TIME_WINDOW = 300 # 5 phút

# Tạo một "Kho" lưu Nonce trong RAM: Tối đa 10.000 cái, mỗi cái sống đúng 300 giây (5 phút)
nonce_cache = TTLCache(maxsize=10000, ttl=MAX_TIME_WINDOW)

class SignRequest(BaseModel):
    payload: str 

# Thêm x_token vào tham số của hàm verify_security_headers
async def verify_security_headers(
    request: Request, 
    x_signature: str = Header(None),
    x_timestamp: int = Header(None),
    x_nonce: str = Header(None),
    authorization: str = Header(None) # Lấy token từ header
):
    # 1. Kiểm tra 3 món vũ khí bảo mật
    if not all([x_signature, x_timestamp, x_nonce]):
        raise HTTPException(status_code=401, detail="Thiếu Headers bảo mật (Signature, Timestamp hoặc Nonce)!")

    # 2. Check Timestamp (Dấu thời gian)
    current_time = int(time.time())
    if abs(current_time - x_timestamp) > MAX_TIME_WINDOW:
        raise HTTPException(status_code=403, detail="Request quá hạn (Expired)!")

    # 3. Check Nonce trong RAM (Thay cho Redis)
    if x_nonce in nonce_cache:
        raise HTTPException(status_code=403, detail="Phát hiện Replay Attack! Nonce này đã được sử dụng.")
    
    # Tách lấy chữ ký JWT (bỏ chữ Bearer đi)
    token = authorization.split(" ")[1] if (authorization and " " in authorization) else "no-token"
  ## 4. Xác thực HMAC (Băm cả Timestamp + Nonce + Body)
    body = await request.body()
    
    # DÙNG .strip() ĐỂ ÉP BỎ KÝ TỰ XUỐNG DÒNG THỪA
    body_text = body.decode('utf-8').strip()
    data_to_hash = f"{x_timestamp}.{x_nonce}.{body_text}".encode('utf-8')
    expected_mac = hmac.new(SHARED_SECRET, data_to_hash, hashlib.sha256).hexdigest()
    
    # In ra log của Docker để bắt quả tang lỗi
    print("--- DEBUG HMAC ---")
    print(f"Server tự băm: {expected_mac}")
    print(f"Client gửi tới: {x_signature}")
    print(f"Dữ liệu gốc: {data_to_hash}")
    
    if not hmac.compare_digest(expected_mac, x_signature):
        raise HTTPException(status_code=403, detail="Sai chữ ký HMAC! Dữ liệu bị sửa.")

    # 5. Lưu Nonce vào bộ nhớ đệm để đánh dấu đã dùng
    nonce_cache[x_nonce] = True

@app.post("/api/sign", dependencies=[Depends(verify_security_headers)])
def sign_data(req: SignRequest):
    try:
        token = lib.get_token(token_label='NT219_Token')
        with token.open(user_pin='1234') as session:
            priv_key = session.get_key(object_class=pkcs11.ObjectClass.PRIVATE_KEY, label='my_sign_key')
            data_bytes = req.payload.encode('utf-8')
            signature = priv_key.sign(data_bytes, mechanism=pkcs11.Mechanism.RSA_PKCS)
            return {"signature": base64.b64encode(signature).decode('utf-8')}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))