import time
import hmac
import hashlib
import httpx
import asyncio
import uuid

SOFTHSM_URL = "http://localhost:8888/api/sign"
HMAC_SECRET = b"chuoi_bi_mat_cua_nhom_NT219"

async def simulate_replay_attack():
    print("🚀 BẮT ĐẦU KỊCH BẢN TẤN CÔNG REPLAY ATTACK...")

    payload_str = '{"payload": "HoaDon_HACKERTEST_500000VND"}'
    timestamp = int(time.time())
    nonce = uuid.uuid4().hex
    data_to_hash = f"{timestamp}.{nonce}.{payload_str}".encode('utf-8')
    signature = hmac.new(HMAC_SECRET, data_to_hash, hashlib.sha256).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-Signature": signature,
        "X-Timestamp": str(timestamp),
        "X-Nonce": nonce
    }

    async with httpx.AsyncClient() as client:
        print("\n[LẦN 1] Gửi request lần đầu tiên (Hợp lệ)...")
        res1 = await client.post(SOFTHSM_URL, data=payload_str, headers=headers)
        if res1.status_code == 200:
            print(f"✅ Thành công! Lấy được chữ ký: {res1.text[:30]}...")
        
        print("\n[LẦN 2] Hacker chộp được request và gửi lại y chang...")
        res2 = await client.post(SOFTHSM_URL, data=payload_str, headers=headers)
        
        if res2.status_code == 403:
            print(f"🛡️ TƯỜNG LỬA HOẠT ĐỘNG TỐT: Bị chặn với lỗi -> {res2.json()}")
        else:
            print("❌ TOANG! Tường lửa thủng, Hacker lọt qua được!")

if __name__ == "__main__":
    asyncio.run(simulate_replay_attack())