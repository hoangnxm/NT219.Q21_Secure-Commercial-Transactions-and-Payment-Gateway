import requests
import time
import statistics

API_URL = "http://localhost:8000/api/orders/create"
latencies = []

def measure_performance(n=10):
    print(f"--- Đang đo đạc hiệu năng với {n} request ---")
    for i in range(n):
        start_time = time.time()
        
        response = requests.post(API_URL, json={
            "product_id": f"test_{i}",
            "quantity": 1,
            "payment_token": "pm_1TEm832eZvKYlo2C4vhzBydI"
        })
        
        end_time = time.time()
        duration = (end_time - start_time) * 1000
        latencies.append(duration)
        print(f"Request {i+1}: {duration:.2f} ms")

    print("\n--- KẾT QUẢ ĐO ĐẠC ---")
    print(f"Thời gian trung bình (Median): {statistics.median(latencies):.2f} ms")
    print(f"Độ trễ P95 (95th percentile): {statistics.quantiles(latencies, n=20)[18]:.2f} ms") # 
    print(f"Độ trễ P99 (99th percentile): {statistics.quantiles(latencies, n=100)[98]:.2f} ms") # 

measure_performance(30)