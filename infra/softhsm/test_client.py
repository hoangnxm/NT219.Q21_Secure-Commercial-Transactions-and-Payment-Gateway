import time
import hmac
import hashlib
import requests
import uuid

# Cấu hình y chang đồ án
url = "http://localhost:8888/api/sign"
secret = b"chuoi_bi_mat_cua_nhom_NT219"
payload = '{"payload": "HoaDon_001_500000VND"}'

# 1. Sinh Dấu thời gian và Tem chống giả (Nonce) động
timestamp = int(time.time())
nonce = uuid.uuid4().hex # Sinh chuỗi ngẫu nhiên 32 ký tự

# 2. Băm HMAC (Kẹp cả 3 thứ: thời gian, tem, dữ liệu)
data_to_hash = f"{timestamp}.{nonce}.{payload}".encode('utf-8')
signature = hmac.new(secret, data_to_hash, hashlib.sha256).hexdigest()

# 3. Gom vào Header
headers = {
    "Content-Type": "application/json",
    "X-Signature": signature,
    "X-Timestamp": str(timestamp),
    "X-Nonce": nonce
}

print("--- LẦN 1: KHÁCH HÀNG THANH TOÁN HỢP LỆ ---")
res1 = requests.post(url, data=payload, headers=headers)
print(f"Mã lỗi: {res1.status_code}")
print(f"Phản hồi: {res1.text}\n")

print("--- LẦN 2: HACKER CHẶN ĐƯỜNG VÀ COPY Y CHANG REQUEST 1 ĐỂ GỬI LẠI (REPLAY ATTACK) ---")
# Hacker không biết Secret Key nên không tự băm HMAC mới được, đành xài lại đồ cũ
res2 = requests.post(url, data=payload, headers=headers)
print(f"Mã lỗi: {res2.status_code}")
print(f"Phản hồi: {res2.text}\n")