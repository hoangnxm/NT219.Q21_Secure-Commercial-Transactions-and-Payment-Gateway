import { useState, useEffect } from "react";
import { loadStripe } from "@stripe/stripe-js";
import { Elements } from "@stripe/react-stripe-js";
import PaymentForm from "./PaymentForm";

// Key Stripe của ông
const stripePromise = loadStripe('pk_test_51TE1cpLEdwXIMzQb1PF9p7ixh7vm612NQYjL8Xu0TnxLEwvky3S7oO62fWocy132Do7sX4DFxFK96UPtu07sGBVP009X6bHnpe');

export default function Checkout() {
  const [clientSecret, setClientSecret] = useState('');
  const [orderData, setOrderData] = useState(null);
  const [message, setMessage] = useState('Đang khởi tạo phiên thanh toán an toàn...');

  useEffect(() => {
    const initPayment = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/payments/charge', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            order_id: "idd112",
            amount: 60000,
            email: "khachhang@example.com" 
          }),
        });

        const data = await response.json();

        if (response.ok && data.client_secret) {
          setClientSecret(data.client_secret);
          setOrderData(data);
          setMessage('');
        } else {
          setMessage(`❌ Lỗi từ Server: ${data.error || data.detail || 'Không thể tạo phiên thanh toán'}`);
        }
      } catch (err) {
        setMessage("❌ Không kết nối được Backend. Kêu thằng Ngô Hoàng check lại cổng 8000 đi!");
      }
    };

    initPayment();
  }, []);

  return (
    <div style={{ width: '100%', maxWidth: '450px' }}>
      {clientSecret ? (
        <Elements stripe={stripePromise} options={{ clientSecret, appearance: { theme: 'stripe' } }}>
          <PaymentForm orderData={orderData} />
        </Elements>
      ) : (
        <div style={{ fontSize: '18px', textAlign: 'center' }}>{message}</div>
      )}
    </div>
  );
}