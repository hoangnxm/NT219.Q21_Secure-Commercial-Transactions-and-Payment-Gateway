import asyncio
import httpx
import time
import statistics

API_URL = "http://localhost:8001/api/orders/create" # Chỉnh lại port Backend nếu cần
TOTAL_REQUESTS = 100
CONCURRENCY = 10 # Số request gửi cùng lúc

async def make_request(client, semaphore, times_list):
    async with semaphore:
        start_t = time.time()
        payload = {"product_id": "iphone-15", "quantity": 1, "payment_token": "tok_test_perf"}
        try:
            await client.post(API_URL, json=payload, timeout=5.0)
        except:
            pass
        finally:
            times_list.append(time.time() - start_t)

async def main():
    print(f"🚀 BẮT ĐẦU LOAD TEST...")
    print(f"Đang gửi {TOTAL_REQUESTS} requests với concurrency là {CONCURRENCY}...\n")
    
    semaphore = asyncio.Semaphore(CONCURRENCY)
    times_list = []
    
    start_test_time = time.time()
    
    async with httpx.AsyncClient() as client:
        tasks = [make_request(client, semaphore, times_list) for _ in range(TOTAL_REQUESTS)]
        await asyncio.gather(*tasks)
        
    total_time = time.time() - start_test_time
    
    # Tính toán TPS và Latency
    tps = TOTAL_REQUESTS / total_time
    avg_latency = statistics.mean(times_list) * 1000 # Đổi ra mili-giây (ms)
    p95_latency = statistics.quantiles(times_list, n=100)[94] * 1000 if len(times_list) > 1 else 0

    print("📊 KẾT QUẢ HIỆU NĂNG (PERFORMANCE REPORT):")
    print(f"⚡ Thông lượng (TPS): {tps:.2f} requests/giây")
    print(f"⏱️ Độ trễ trung bình (Avg Latency): {avg_latency:.2f} ms")
    print(f"🐢 Độ trễ P95 (95% request nhanh hơn): {p95_latency:.2f} ms")
    print(f"Tổng thời gian test: {total_time:.2f} giây")
    print("\n📝 Note cho báo cáo: Nếu TPS quá thấp, giải pháp đề xuất là chuyển từ SQLite sang PostgreSQL (k8s) và tăng RAM/CPU cho pod Kubernetes.")

if __name__ == "__main__":
    asyncio.run(main())