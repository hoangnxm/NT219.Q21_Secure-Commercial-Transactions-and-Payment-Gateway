import { useState, useEffect } from "react";
import { loadStripe } from "@stripe/stripe-js";
import { Elements } from "@stripe/react-stripe-js";
import PaymentForm from "./PaymentForm";

// Key Stripe của ông
const stripePromise = loadStripe('pk_test_51TE1cpLEdwXIMzQb1PF9p7ixh7vm612NQYjL8Xu0TnxLEwvky3S7oO62fWocy132Do7sX4DFxFK96UPtu07sGBVP009X6bHnpe');

export default function Checkout() {
  const [orderData, setOrderData] = useState(null);

  // Hiệu ứng loading để chờ lấy dữ liệu
  const[isLoading,setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  // Được gọi khi bấm nút "Thanh toán"
  const handlePaymentSubmit = async (paymentToken) => {
    try {
      setIsLoading(true);
      setErrorMessage('');

      // GỌI API FASTAPI ĐỂ TRỪ TIỀN VÀ KÝ SOFTHSM
      const response = await fetch('http://localhost:5000/api/orders/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          product_id: "SP01", 
          quantity: 1,        
          email: "khachhang@example.com",
          payment_token: paymentToken || "pm_card_visa" // Lấy token thật từ Stripe, tạm thời hardcode để test
        }),
      });

      const data = await response.json();

      if (response.ok && data.status === "success") {
        setOrderData(data);
      } else {
        setErrorMessage(`❌ Lỗi từ Server: ${data.detail || 'Thanh toán thất bại'}`);
      }
    } catch (err) {
      setErrorMessage("❌ Không kết nối được Backend FastAPI.");
    } finally {
      setIsLoading(false);
    }
  };

  // ĐANG LOADING
  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <div style={{
          width: '50px', height: '50px', border: '5px solid rgba(255,255,255,0.2)',
          borderTop: '5px solid #6772e5', borderRadius: '50%', 
          animation: 'spin 1s linear infinite', margin: '0 auto 20px auto'
        }}></div>
        <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
        
        <h2>Đang thiết lập kênh thanh toán mTLS...</h2>
        <p style={{ color: '#aaa' }}>Hệ thống đang gọi sang SoftHSM và Stripe, vui lòng chờ ⏳</p>
      </div>
    );
  }

  // NẾU THANH TOÁN THÀNH CÔNG -> SHOW BIÊN LAI (JWS)
  if (orderData) {
    return (
      <div style={{ padding: '20px', backgroundColor: '#e8f5e9', color: '#2e7d32', borderRadius: '8px', textAlign: 'center' }}>
        <h3>✅ Thanh toán thành công!</h3>
        <p>Mã đơn hàng: <strong>{orderData.order_id}</strong></p>
        <div style={{ marginTop: '15px', padding: '10px', backgroundColor: '#fff', border: '1px solid #c8e6c9', wordBreak: 'break-all', fontSize: '12px' }}>
          <strong>Biên lai điện tử (JWS SoftHSM):</strong><br/>
          {orderData.jws_receipt}
        </div>
      </div>
    );
  }

  // 3. NẾU CHƯA THANH TOÁN -> SHOW FORM NHẬP THẺ
  return (
    <div style={{ width: '100%', maxWidth: '450px', margin: '0 auto', fontFamily: 'sans-serif' }}>
      <h2 style={{textAlign: 'center'}}>Thanh toán Đơn hàng</h2>
      
      {/* Hiển thị lỗi nếu có */}
      {errorMessage && (
        <div style={{ padding: '10px', backgroundColor: '#ffebee', color: '#c62828', borderRadius: '8px', marginBottom: '15px', textAlign: 'center' }}>
          {errorMessage}
        </div>
      )}

      {/* Truyền hàm Submit xuống cho Form */}
      <Elements stripe={stripePromise}>
        <PaymentForm onSubmit={handlePaymentSubmit} />
      </Elements>
    </div>
  );
}