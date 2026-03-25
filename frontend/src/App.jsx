import { useState } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import { Elements, CardElement, useStripe, useElements } from '@stripe/react-stripe-js';

const stripePromise = loadStripe('pk_test_TYooMQauvdEDq54NiTphI7jx'); 

const CheckoutForm = () => {
  const stripe = useStripe();
  const elements = useElements();
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [jwsReceipt, setJwsReceipt] = useState('');

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!stripe || !elements) return;

    setLoading(true);
    setMessage('⏳ Đang xác thực thẻ...');
    setJwsReceipt('');

    const cardElement = elements.getElement(CardElement);

    const { error, paymentMethod } = await stripe.createPaymentMethod({
      type: 'card',
      card: cardElement,
    });

    if (error) {
      setMessage(`❌ Lỗi Stripe: ${error.message}`);
      setLoading(false);
    } else {
      setMessage(`✅ Đã lấy Token! Đang gửi đơn hàng...`);
      
      try {
        const response = await fetch('http://localhost:8000/api/orders/create', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            product_id: "iphone-15",
            quantity: 1,
            payment_token: paymentMethod.id 
          }),
        });

        const data = await response.json();

        if (response.ok && data.status === "success") {
          const formattedAmount = new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(data.amount);
          setMessage(`🚀 Thành công! Order ID: ${data.order_id} | Tổng tiền: ${formattedAmount}`);
          setJwsReceipt(data.jws_receipt); 
        } else {
          setMessage(`❌ Lỗi từ Server: ${data.detail || 'Lỗi không xác định'}`); 
        }
      } catch (err) {
        setMessage(`❌ Không kết nối được Backend (Ông đã bật uvicorn chưa?)`);
      }
      setLoading(false);
    }
  };

  return (
    <div style={{
      display: 'flex', justifyContent: 'center', alignItems: 'center',
      minHeight: '100vh', backgroundColor: '#1a1a1a', fontFamily: 'Arial, sans-serif'
    }}>
      <form onSubmit={handleSubmit} style={{ 
        width: '100%', maxWidth: '450px', padding: '40px', backgroundColor: '#ffffff',
        borderRadius: '12px', boxShadow: '0 10px 25px rgba(0,0,0,0.5)', color: '#333'
      }}>
        <h2 style={{ textAlign: 'center', marginBottom: '30px', color: '#000' }}>
          🛒 CỔNG THANH TOÁN
        </h2>
        
        <label style={{ display: 'block', marginBottom: '10px', fontWeight: 'bold' }}>
          Thông tin thẻ
        </label>

        <div style={{ 
          border: '1px solid #ddd', padding: '15px', borderRadius: '6px', 
          marginBottom: '25px', backgroundColor: '#f9f9f9' 
        }}>
          {/* Ô nhập thẻ bảo mật của Stripe */}
          <CardElement options={{ 
            style: { base: { fontSize: '16px', color: '#424770', '::placeholder': { color: '#aab7c4' } } },
            hidePostalCode: true 
          }} />
        </div>

        <button 
          type="submit" 
          disabled={!stripe || loading}
          style={{ 
            width: '100%', padding: '12px', backgroundColor: '#6772e5', color: 'white', 
            border: 'none', borderRadius: '6px', fontSize: '16px', fontWeight: 'bold',
            cursor: loading ? 'not-allowed' : 'pointer'
          }}
        >
          {loading ? 'Đang xử lý...' : 'Thanh toán ngay'}
        </button>

        {/* Thông báo trạng thái */}
        {message && (
          <div style={{ 
            marginTop: '20px', padding: '10px', borderRadius: '4px', textAlign: 'center',
            backgroundColor: message.includes('❌') ? '#fff0f0' : '#f0fff4',
            color: message.includes('❌') ? '#d32f2f' : '#2e7d32'
          }}>
            {message}
          </div>
        )}

        {/* Hiển thị biên lai JWS (Tính chống chối bỏ - Non-repudiation) */}
        {jwsReceipt && (
          <div style={{ 
            marginTop: '20px', padding: '15px', backgroundColor: '#f8f9fa', 
            border: '1px dashed #6772e5', borderRadius: '8px'
          }}>
            <h4 style={{ margin: '0 0 10px 0', color: '#6772e5' }}>📄 Biên lai xác thực (JWS)</h4>
            <p style={{ fontSize: '11px', color: '#666', marginBottom: '8px' }}>
              Mã này chứng minh giao dịch đã được ký bởi hệ thống bảo mật.
            </p>
            <code style={{ 
              display: 'block', wordBreak: 'break-all', backgroundColor: '#eee', 
              padding: '10px', fontSize: '10px', borderRadius: '4px', lineHeight: '1.4'
            }}>
              {jwsReceipt}
            </code>
            <div style={{ marginTop: '10px', fontSize: '12px', color: 'green', fontWeight: 'bold' }}>
              🛡️ Verified by SoftHSM
            </div>
          </div>
        )}
      </form>
    </div>
  );
};
function App() {
  return (
    <Elements stripe={stripePromise}>
      <CheckoutForm />
    </Elements>
  );
}

export default App;