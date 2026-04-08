import { useState } from "react";
import { loadStripe } from "@stripe/stripe-js";
import { Elements } from "@stripe/react-stripe-js";
import PaymentForm from "./PaymentForm";

const stripePromise = loadStripe('pk_test_51TE1cpLEdwXIMzQb1PF9p7ixh7vm612NQYjL8Xu0TnxLEwvky3S7oO62fWocy132Do7sX4DFxFK96UPtu07sGBVP009X6bHnpe');

export default function Checkout({ product }) {
  const [orderData, setOrderData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const options = {
    mode: 'payment',
    amount: product?.price > 0 ? product.price : 1000,
    currency: 'vnd',
  };

  const handlePaymentSubmit = async (paymentToken) => {
    try {
      setIsLoading(true);
      setErrorMessage('');

      // Gửi Payment Method ID (pm_...) sang FastAPI
      const response = await fetch('http://localhost:5000/api/orders/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          product_id: product.id,
          quantity: 1,        
          email: "khachhang@example.com",
          payment_token: paymentToken 
        }),
      });

      const data = await response.json();
      if (response.ok && data.status === "success") {
        setOrderData(data);
      } else {
        setErrorMessage(data.detail || 'Thanh toán thất bại');
      }
    } catch (err) {
      setErrorMessage("Không kết nối được Backend FastAPI.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ width: '100%', display: 'flex', justifyContent: 'center', padding: '20px' }}>
      <Elements stripe={stripePromise} options={options}>
        <PaymentForm 
          product={product} 
          orderData={orderData} 
          onSubmit={handlePaymentSubmit}
          isLoading={isLoading}
          externalError={errorMessage}
        />
      </Elements>
    </div>
  );
}