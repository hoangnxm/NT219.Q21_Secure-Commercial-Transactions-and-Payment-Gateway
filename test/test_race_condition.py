import asyncio
import httpx
import time

API_URL = "http://localhost:8001/api/orders/create" 

async def buy_iphone(client, user_id):
    payload = {
        "product_id": "iphone-15",
        "quantity": 1,
        "payment_token": f"tok_test_{user_id}"
    }
    try:
        response = await client.post(API_URL, json=payload)
        return response.status_code, response.json()
    except Exception as e:
        return 500, str(e)

async def main():
    print("🚀 BẮT ĐẦU TEST RACE CONDITION (DOUBLE-SPEND)...")
    print("Mô phỏng 20 người dùng cùng click nút 'Thanh toán' một lúc trong khi kho chỉ có 10 máy.")
    
    async with httpx.AsyncClient() as client:
        tasks = [buy_iphone(client, i) for i in range(20)]
        start_time = time.time()
        
        results = await asyncio.gather(*tasks)
        
        success_count = sum(1 for status, res in results if status == 200)
        fail_count = sum(1 for status, res in results if status != 200)
        
        print("\n📊 KẾT QUẢ TEST:")
        print(f"✅ Số đơn thành công: {success_count} (Kỳ vọng: 10)")
        print(f"❌ Số đơn bị từ chối (Hết hàng/Lỗi DB): {fail_count} (Kỳ vọng: 10)")
        print(f"⏱️ Thời gian thực thi: {time.time() - start_time:.2f} giây")
        
        if success_count > 10:
            print("⚠️ CẢNH BÁO: HỆ THỐNG BỊ LỖI RACE CONDITION (BÁN ÂM KHO)!")
        elif success_count == 10:
            print("🛡️ TỐT: Hệ thống giữ nguyên vẹn kho dữ liệu, không bán lố.")
        else:
            print("💡 Lưu ý: Nếu có lỗi 500 (Database is locked), đây là nhược điểm của SQLite khi chạy concurrency. Ghi vào báo cáo nên chuyển sang PostgreSQL theo kế hoạch.")

if __name__ == "__main__":
    asyncio.run(main())