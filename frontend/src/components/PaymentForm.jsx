// frontend/src/components/PaymentForm.jsx
import { useState } from "react";
import { PaymentElement, useStripe, useElements } from "@stripe/react-stripe-js";

export default function PaymentForm({ product, orderData, userEmail }) {
  const stripe = useStripe();
  const elements = useElements();
  const [message, setMessage] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  
  // NHỊP 3: Thêm State để lưu Biên lai mTLS sau khi thanh toán xong
  const [receipt, setReceipt] = useState(null);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!stripe || !elements) return;

    setIsProcessing(true);
    setMessage('⏳ Đang xử lý thanh toán và kiểm tra 3DS...');

    // Xác nhận thanh toán trực tiếp với Stripe
    const { paymentIntent, error } = await stripe.confirmPayment({
      elements,
      confirmParams: {
        return_url: `${window.location.origin}/`, 
      },
      redirect: "if_required",
    });

    // Xử lí kết quả
    if (error) {
      setIsProcessing(false);
      if (error.type === "card_error" || error.type === "validation_error") {
        setMessage(`❌ ${error.message}`);
      } else {
        setMessage("❌ Lỗi: " + error.message);
      }
    } 
    // NHỊP 2: Check Stripe báo thành công
    else if (paymentIntent && paymentIntent.status === 'succeeded') {
      setMessage("✅ Thanh toán thành công! Đang lấy biên lai an toàn...");
      
      // NHỊP 3: Gọi Backend xác nhận và lấy Biên lai SoftHSM
      try {
        const confirmRes = await fetch('http://localhost:5000/api/orders/confirm', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ order_id: orderData.order_id })
        });
        
        const confirmData = await confirmRes.json();

        if (confirmRes.ok && confirmData.status === 'success') {
          setMessage("✅ Giao dịch hoàn tất! Đã ký biên lai an toàn.");
          // Lưu biên lai vào State để xổ cái bảng xanh lè ra
          setReceipt(confirmData.jws_receipt);
        } else {
          setMessage("⚠️ Thanh toán OK nhưng lỗi lấy biên lai: " + (confirmData.detail || "Lỗi không xác định"));
        }
      } catch (err) {
        setMessage("⚠️ Thanh toán OK nhưng không thể kết nối tới Server để lấy biên lai.");
      } finally {
        setIsProcessing(false);
      }

    } else {
      setMessage("⏳ Trạng thái: " + (paymentIntent?.status || "Đang xử lý..."));
      setIsProcessing(false);
    }
  };

  const formattedAmount = new Intl.NumberFormat('vi-VN', { 
    style: 'currency', currency: 'VND' 
  }).format(product?.price || 0);

  const paymentElementOptions = {
    defaultValues: {
      billingDetails: {
        email: userEmail,
      }
    }
  };

  return (
    <div style={styles.container}>
      <form onSubmit={handleSubmit} style={styles.form}>
        <div style={styles.header}>
          <h2 style={{ margin: 0, fontSize: '22px' }}>SECURE CHECKOUT</h2>
          <p style={{ opacity: 0.6, fontSize: '12px' }}>NT219 GATEWAY</p>
        </div>

        <div style={styles.productBox}>
          <div style={{ textAlign: 'left' }}>
            <span style={styles.label}>Sản phẩm</span>
            <span style={styles.value}>{product?.name || "Sản phẩm"}</span>
          </div>
          <div style={{ textAlign: 'right' }}>
            <span style={styles.label}>Tổng cộng</span>
            <span style={styles.price}>{formattedAmount}</span>
          </div>
        </div>

        <div style={styles.stripeBox}>
          <PaymentElement id="payment-element" options={paymentElementOptions}/>
        </div>
        
        <button type="submit" disabled={!stripe || isProcessing} style={styles.btn}>
          {isProcessing ? 'PROCESSING...' : 'PAY NOW'}
        </button>

        {message && (
          <div style={message.includes('❌') || message.includes('⚠️') ? styles.errorMsg : styles.successMsg}>
            {message}
          </div>
        )}
        
        {/* Render JWS từ State 'receipt' thay vì 'orderData.jws_receipt' */}
        {receipt && (
          <div style={styles.jwsBox}>
            <h4 style={{ color: '#00f2fe', margin: '0 0 10px 0' }}>📄 BIÊN LAI XÁC THỰC (JWS)</h4>
            <code style={styles.code}>{receipt}</code>
          </div>
        )}
      </form>
    </div>
  );
}

const styles = {
  container: { background: 'linear-gradient(135deg, #0f0c29 0%, #24243e 100%)', padding: '35px', borderRadius: '24px', border: '1px solid rgba(255,255,255,0.1)' },
  form: { width: '400px', color: '#fff', fontFamily: 'sans-serif' },
  header: { textAlign: 'center', marginBottom: '25px' },
  productBox: { display: 'flex', justifyContent: 'space-between', background: 'rgba(255,255,255,0.05)', padding: '15px', borderRadius: '15px', marginBottom: '20px' },
  label: { display: 'block', fontSize: '11px', color: '#aaa' },
  value: { fontWeight: 'bold', fontSize: '15px' },
  price: { fontWeight: 'bold', fontSize: '18px', color: '#00f2fe' },
  stripeBox: { background: 'rgba(0,0,0,0.2)', padding: '15px', borderRadius: '12px', marginBottom: '20px' },
  btn: { width: '100%', padding: '16px', background: 'linear-gradient(to right, #667eea, #764ba2)', color: '#fff', border: 'none', borderRadius: '12px', fontWeight: 'bold', cursor: 'pointer' },
  jwsBox: { marginTop: '20px', padding: '15px', background: 'rgba(0,0,0,0.4)', borderRadius: '12px', border: '1px solid #00f2fe' },
  code: { fontSize: '10px', wordBreak: 'break-all', color: '#00f2fe', opacity: 0.8 },
  errorMsg: { marginTop: '15px', padding: '10px', background: 'rgba(255,0,0,0.1)', color: '#ff4757', borderRadius: '8px', textAlign: 'center' },
  successMsg: { marginTop: '15px', padding: '10px', background: 'rgba(0,255,0,0.1)', color: '#2ed573', borderRadius: '8px', textAlign: 'center' }
};