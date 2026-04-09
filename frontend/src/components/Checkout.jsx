// frontend/src/components/Checkout.jsx
import { useState, useEffect } from "react";
import { loadStripe } from "@stripe/stripe-js";
import { Elements } from "@stripe/react-stripe-js";
import PaymentForm from "./PaymentForm";

const stripePromise = loadStripe('pk_test_51TE1cpLEdwXIMzQb1PF9p7ixh7vm612NQYjL8Xu0TnxLEwvky3S7oO62fWocy132Do7sX4DFxFK96UPtu07sGBVP009X6bHnpe');

export default function Checkout({ product }) {
  const [clientSecret, setClientSecret] = useState("");
  const [orderData, setOrderData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');

  // GỌI API NGAY KHI VÀO TRANG CHECKOUT ĐỂ LẤY CLIENT SECRET
  useEffect(() => {
    const createPaymentIntent = async () => {
      try {
        // Lưu ý: Không gửi payment_token ở bước này nữa
        const response = await fetch('http://localhost:5000/api/orders/create', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            product_id: product.id,
            quantity: 1,        
            email: "khachhang@example.com"
          }),
        });

        const data = await response.json();
        if (response.ok && data.status === "success") {
          setClientSecret(data.client_secret); // Nhận client_secret từ Laravel truyền qua FastAPI
          setOrderData(data); // Lưu thông tin order (chứa JWS, fraud_score,...)
        } else {
          setErrorMessage(data.detail || 'Lỗi khi khởi tạo giao dịch');
          
        }
      } catch (err) {
        const errorMsg = typeof data.detail === 'string' 
            ? data.detail 
            : JSON.stringify(data.detail || 'Lỗi khi khởi tạo giao dịch');
            
          setErrorMessage(errorMsg);
      } finally {
        setIsLoading(false);
      }
    };

    createPaymentIntent();
  }, [product.id]);

  const appearance = {
    theme: 'night',
    variables: {
      colorPrimary: '#00f2fe',
    },
  };

  const options = {
    clientSecret,
    appearance,
  };

  if (isLoading) return <div style={{color: 'white'}}>Đang khởi tạo cổng thanh toán...</div>;
  if (errorMessage) return <div style={{color: 'red'}}>{errorMessage}</div>;

  return (
    <div style={{ width: '100%', display: 'flex', justifyContent: 'center', padding: '20px' }}>
      {/* Chỉ render Elements khi đã có clientSecret */}
      {clientSecret && (
        <Elements stripe={stripePromise} options={options}>
          <PaymentForm 
            product={product} 
            orderData={orderData} 
          />
        </Elements>
      )}
    </div>
  );
}