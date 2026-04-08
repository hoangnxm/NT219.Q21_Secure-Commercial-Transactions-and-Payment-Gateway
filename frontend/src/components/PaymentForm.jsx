import { useState } from "react";
import { PaymentElement, useStripe, useElements } from "@stripe/react-stripe-js";

export default function PaymentForm({ orderData }) {
  const stripe = useStripe();
  const elements = useElements();
  
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false); // Trạng thái kiểm tra thanh toán thành công

  const handleSubmit = async (event) => {
    event.preventDefault();
    
    if (!stripe || !elements) return;

    setLoading(true);
    setMessage('⏳ Đang xử lý thanh toán và xác thực bảo mật...');

    const { error, paymentIntent } = await stripe.confirmPayment({
      elements,
      confirmParams: {
        return_url: window.location.origin, 
      },
      // ĐÂY LÀ DÒNG CHÚA TỂ FIX LỖI RELOAD TRANG:
      redirect: "if_required" 
    });

    if (error) {
      if (error.type === "card_error" || error.type === "validation_error") {
        setMessage(`❌ Lỗi: ${error.message}`);
      } else {
        setMessage("❌ Đã xảy ra lỗi không xác định. Kiểm tra lại mạng hoặc thẻ.");
      }
      setIsSuccess(false);
    } else if (paymentIntent && paymentIntent.status === "succeeded") {
      setMessage(`✅ Thanh toán thành công!`);
      setIsSuccess(true);
    }
    
    setLoading(false);
  };

  const formattedAmount = new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(orderData?.amount || 0);

  return (
    <form onSubmit={handleSubmit} style={{ 
      padding: '40px', backgroundColor: '#ffffff',
      borderRadius: '12px', boxShadow: '0 10px 25px rgba(0,0,0,0.5)', color: '#333'
    }}>
      <h2 style={{ textAlign: 'center', marginBottom: '30px', color: '#000' }}>
        🛒 CỔNG THANH TOÁN
      </h2>
      <p style={{ textAlign: 'center', fontWeight: 'bold', marginBottom: '20px' }}>
        Mã đơn: {orderData?.order_id} | Tổng: {formattedAmount}
      </p>

      <div style={{ marginBottom: '25px' }}>
        <PaymentElement />
      </div>

      <button 
        type="submit" 
        disabled={!stripe || loading || isSuccess}
        style={{ 
          width: '100%', padding: '12px', 
          backgroundColor: isSuccess ? '#2e7d32' : '#6772e5', 
          color: 'white', border: 'none', borderRadius: '6px', 
          fontSize: '16px', fontWeight: 'bold',
          cursor: (loading || isSuccess) ? 'not-allowed' : 'pointer'
        }}
      >
        {loading ? 'Đang xử lý...' : isSuccess ? 'Đã thanh toán' : 'Thanh toán ngay'}
      </button>

      {message && (
        <div style={{ 
          marginTop: '20px', padding: '10px', borderRadius: '4px', textAlign: 'center',
          backgroundColor: message.includes('❌') ? '#fff0f0' : '#f0fff4',
          color: message.includes('❌') ? '#d32f2f' : '#2e7d32',
          fontWeight: 'bold'
        }}>
          {message}
        </div>
      )}

      {/* Chỉ hiện cục JWS sau khi thẻ đã báo thành công */}
      {isSuccess && orderData?.jws_receipt && (
        <div style={{ 
          marginTop: '20px', padding: '15px', backgroundColor: '#f8f9fa', 
          border: '1px dashed #6772e5', borderRadius: '8px'
        }}>
          <h4 style={{ margin: '0 0 10px 0', color: '#6772e5' }}>📄 Biên lai xác thực (JWS)</h4>
          <p style={{ fontSize: '11px', color: '#666', marginBottom: '8px' }}>
            Mã này chứng minh phiên giao dịch đã được ký bởi hệ thống bảo mật HSM.
          </p>
          <code style={{ 
            display: 'block', wordBreak: 'break-all', backgroundColor: '#eee', 
            padding: '10px', fontSize: '10px', borderRadius: '4px', lineHeight: '1.4'
          }}>
            {orderData.jws_receipt}
          </code>
          <div style={{ marginTop: '10px', fontSize: '12px', color: 'green', fontWeight: 'bold' }}>
            🛡️ Verified by SoftHSM
          </div>
        </div>
      )}
    </form>
  );
}