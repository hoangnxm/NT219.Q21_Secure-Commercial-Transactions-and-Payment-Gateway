import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, classification_report

print("🚀 ĐANG KHỞI TẠO VÀ HUẤN LUYỆN FRAUD DETECTION ENGINE...")

# 1. Giả lập tập dữ liệu giao dịch (1000 mẫu)
np.random.seed(42)
n_samples = 1000

# Các đặc trưng: Số tiền (Amount), Khoảng cách địa lý IP (Distance), 
# Giờ giao dịch (Hour), Thiết bị mới (IsNewDevice - 0/1)
data = {
    'Amount': np.random.uniform(10, 5000000, n_samples),
    'Distance': np.random.uniform(0, 10000, n_samples),
    'Hour': np.random.randint(0, 24, n_samples),
    'IsNewDevice': np.random.randint(0, 2, n_samples),
}
df = pd.DataFrame(data)

# Logic tạo nhãn Fraud (Gian lận): Tiền lớn + khoảng cách xa + thiết bị mới + nửa đêm
df['IsFraud'] = np.where(
    (df['Amount'] > 2000000) & (df['Distance'] > 5000) & (df['IsNewDevice'] == 1) & ((df['Hour'] < 5) | (df['Hour'] > 22)),
    1, # 1 = Gian lận
    0  # 0 = Hợp lệ
)
# Thêm chút nhiễu (noise) để thực tế hơn
df.loc[np.random.choice(df.index, size=20, replace=False), 'IsFraud'] = 1 

# 2. Train - Test Split
X = df.drop('IsFraud', axis=1)
y = df['IsFraud']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 3. Build & Train Model
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# 4. Dự đoán & Đo đạc Tỷ lệ (Metrics)
y_pred = model.predict(X_test)

print("\n📊 BÁO CÁO ĐO ĐẠC MÔ HÌNH CHỐNG GIAN LẬN (ML METRICS):")
print("-" * 50)
print(f"✅ Accuracy (Độ chính xác tổng thể): {accuracy_score(y_test, y_pred) * 100:.2f}%")
print(f"🎯 Precision (Tỷ lệ bắt trúng gian lận): {precision_score(y_test, y_pred, zero_division=0) * 100:.2f}%")
print(f"🔍 Recall (Tỷ lệ không bỏ sót gian lận): {recall_score(y_test, y_pred, zero_division=0) * 100:.2f}%")
print("-" * 50)
print("Chi tiết báo cáo:")
print(classification_report(y_test, y_pred))

# 5. Test thử một giao dịch thực tế
test_tx = pd.DataFrame({'Amount': [4500000], 'Distance': [8000], 'Hour': [2], 'IsNewDevice': [1]})
risk_score = model.predict_proba(test_tx)[0][1] * 100
print(f"\n🔮 TEST GIAO DỊCH MỚI:")
print(f"Tham số: 4.5tr VND, cách 8000km, 2h sáng, thiết bị mới")
print(f"⚠️ Điểm rủi ro (Risk Score): {risk_score:.2f}% -> {'🛑 BLOCK / Yêu cầu 3DS' if risk_score > 70 else '✅ Cho phép thanh toán'}")