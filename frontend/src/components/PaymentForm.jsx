import { useState } from "react";
import { CardElement, useStripe, useElements } from "@stripe/react-stripe-js";

export default function PaymentForm({ product, orderData, onSubmit, isLoading, externalError }) {
  const stripe = useStripe();
  const elements = useElements();
  const [message, setMessage] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!stripe || !elements) return;

    setIsProcessing(true);
    setMessage('⏳ Đang kiểm tra thẻ...');

    // Lấy thông tin từ khung nhập thẻ
    const cardElement = elements.getElement(CardElement);

    // Tạo PaymentMethod (pm_...) thay vì confirm giao dịch ngay
    const { error, paymentMethod } = await stripe.createPaymentMethod({
      type: 'card',
      card: cardElement,
    });

    if (error) {
      setMessage(`${error.message}`);
      setIsProcessing(false);
    } else {
      setMessage(`Thẻ hợp lệ!...`);
      // Gửi ID này về cho handlePaymentSubmit
      await onSubmit(paymentMethod.id); 
      setIsProcessing(false);
    }
  };

  const formattedAmount = new Intl.NumberFormat('vi-VN', { 
    style: 'currency', currency: 'VND' 
  }).format(product?.price || 0);

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

        {!orderData && (
          <>
            <div style={styles.stripeBox}>
              {/* CardElement: Nhập thẻ trên 1 dòng, mượt và khớp logic server */}
              <CardElement options={{ 
                style: { base: { color: '#fff', fontSize: '16px', '::placeholder': { color: '#aaa' } } } 
              }} />
            </div>
            <button type="submit" disabled={!stripe || isProcessing || isLoading} style={styles.btn}>
              {isProcessing || isLoading ? 'PROCESSING...' : 'PAY NOW'}
            </button>
          </>
        )}

        {(message || externalError) && (
          <div style={message.includes('❌') ? styles.errorMsg : styles.successMsg}>
            {externalError || message}
          </div>
        )}

        {orderData?.jws_receipt && (
          <div style={styles.jwsBox}>
            <h4 style={{ color: '#00f2fe', margin: '0 0 10px 0' }}>📄 BIÊN LAI XÁC THỰC (JWS)</h4>
            <code style={styles.code}>{orderData.jws_receipt}</code>
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