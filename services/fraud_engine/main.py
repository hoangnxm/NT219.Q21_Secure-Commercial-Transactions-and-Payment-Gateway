from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import os

app = FastAPI()

# Huấn luyện AI từ Kaggle
def train_fraud_model():
    file_path = "Fraudulent_E-Commerce_Transaction_Data.csv"
    
    print("Đang đọc dataset Kaggle....")
    # Data rất lớn hơn 1 triệu dòng nên cho đọc 100k dòng cho đỡ lag
    df = pd.read_csv(file_path, nrows=100000)
    
    # Chuyển cột chữ thành số
    le_device = LabelEncoder()
    df['Device Used'] = le_device.fit_transform(df['Device Used'].astype(str))
    
    features = ['Transaction Amount', 'Device Used']
    X = df[features]
    y = df['Is Fraudulent']
    
    model = RandomForestClassifier(n_estimators=50, max_depth=10, random_state=42)
    model.fit(X, y)
    
    print("✅ AI đã học xong từ dữ liệu Kaggle!")
    return model, le_device

# Khởi tạo AI
ML_MODEL, LE_DEVICE = train_fraud_model()

# API cho laravel gọi
class TransactionRequest(BaseModel):
    amount: float
    email: str
    ip_address: str
    device: str           
    failed_attempts: int
    hour_of_day: int
    
@app.post("/api/fraud/score")
def fraud_score(tx: TransactionRequest):
    # ---------------------------------------------------------
    # TẦNG 1: LUẬT CỨNG (RULE-BASED) - Block nếu vi phạm
    # ---------------------------------------------------------
    
    # Luật 1: Dùng mail rác
    trash_emails = ['mailinator.com', '10minutemail.com', 'temp-mail.org', 'dispostable.com']
    if any(domain in tx.email for domain in trash_emails):
        return {"action": "block", "score": 95, "reason": "Rule: Khách dùng Email ảo/rác"}
    
    # Luật 2: Thử sai quá nhiều
    if tx.failed_attempts >= 5:
        return {"action": "block", "score": 100, "reason": "Rule: Thử sai quá 5 lần (Card-testing attack)"}

    # Luật 3: Giao dịch nửa đêm
    if 0 <= tx.hour_of_day <= 4 and tx.amount > 10000000:
        return {"action": "force_3ds", "score": 65, "reason": "Rule: Giao dịch lớn vào khung giờ nhạy cảm (0h-4h sáng)"}

    # ---------------------------------------------------------
    # TẦNG 2: ML ENGINE (AI CHẤM ĐIỂM)
    # ---------------------------------------------------------
    
    try:
        device_map = {"Desktop": 0, "Mobile": 1, "Tablet": 2}
        d_code = device_map.get(tx.device, 0)

        amount_for_ai = tx.amount / 25000
                
        input_data = [[amount_for_ai, d_code]]
        prob =  ML_MODEL.predict_proba(input_data)[0][1]
        score = int(prob * 100)
    except Exception as e:
        print(f"⚠️ Lỗi AI: {e}")
        score = 20
    
    # ---------------------------------------------------------
    # TẦNG 3: MA TRẬN QUYẾT ĐỊNH
    # ---------------------------------------------------------
    
    if score >= 85:
        action = "block"
    elif score >= 40:
        action = "force_3ds"
    else:
        action = "allow"

    return {
        "action": action, 
        "score": score, 
        "reason": f"AI Risk Scoring: {score}/100"
    }

if __name__ == "__main__":
    
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8001,
        ssl_keyfile="/certs/server.key",
        ssl_certfile="/certs/server.crt",
        ssl_ca_certs="/certs/ca.crt",
        ssl_cert_reqs=2
    )