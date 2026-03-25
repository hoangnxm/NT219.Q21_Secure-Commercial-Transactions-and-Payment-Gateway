import time
import hmac
import hashlib
import requests
import uuid

# Đã đổi sang HTTPS và cổng 8443 của Nginx
url = "https://localhost:8443/api/sign"
secret = b"chuoi_bi_mat_cua_nhom_NT219"
payload = '{"payload": "HoaDon_001_500000VND"}'

# 1. Sinh tham số chống Replay Attack
timestamp = int(time.time())
nonce = uuid.uuid4().hex

# 2. Băm HMAC
# Sửa dòng ráp chuỗi data_to_hash thành:
data_to_hash = f"{timestamp}.{nonce}.{payload.strip()}".encode('utf-8')
signature = hmac.new(secret, data_to_hash, hashlib.sha256).hexdigest()

headers = {
    "Content-Type": "application/json",
    "X-Signature": signature,
    "X-Timestamp": str(timestamp),
    "X-Nonce": nonce
}

# 3. Chuẩn bị "Thẻ ngành" (Trỏ tới 2 file đúc hồi nãy)
client_cert = ('certs/client.crt', 'certs/client.key')

print("--- GỌI API QUA NGINX CÓ KÈM THẺ NGÀNH VÀ CHỮ KÝ HMAC ---")
try:
    # verify=False để bỏ qua việc check CA vì CA này do mình tự ký (Self-signed)
    res = requests.post(url, data=payload, headers=headers, cert=client_cert, verify=False)
    print(f"Mã lỗi: {res.status_code}")
    print(f"Phản hồi: {res.text}\n")
except Exception as e:
    print(f"Lỗi: {e}")