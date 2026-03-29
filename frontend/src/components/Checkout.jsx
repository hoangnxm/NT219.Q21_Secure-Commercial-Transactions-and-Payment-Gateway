import { useState, useEffect } from "react";
import axios from "axios";
import { loadStripe } from "@stripe/stripe-js";
import { Elements } from "@stripe/react-stripe-js";
import PaymentForm from "./PaymentForm"; // Import cái form Bước 5 vào đây

// Load key từ file .env.local
const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY);

export default function Checkout() {
  const [clientSecret, setClientSecret] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    // Gọi sang API của Leader Ngô Hoàng (nhớ bảo nó chốt cái URL và Port)
    // Ví dụ Backend Laravel đang chạy ở http://localhost:8000
    axios.post("https://localhost/api/payments/charge", {
      order_id: "ORD-123456",
      amount: 50000,
    })
    .then((res) => {
      // Bắt cái client_secret từ json response của Backend
      setClientSecret(res.data.client_secret);
    })
    .catch((err) => {
      console.error("Lỗi gọi API Backend:", err);
      setError("Không thể kết nối đến máy chủ thanh toán. Kêu thằng Ngô Hoàng check lại!");
    });
  }, []);

  const appearance = {
    theme: 'stripe', // Giao diện mặc định cho đẹp
  };
  const options = {
    clientSecret,
    appearance,
  };

  return (
    <div className="checkout-page" style={{ maxWidth: "500px", margin: "0 auto", padding: "20px" }}>
      <h2>Thanh Toán Đơn Hàng</h2>
      
      {error && <p style={{ color: "red" }}>{error}</p>}

      {/* Có clientSecret thì mới render cái form của Stripe */}
      {clientSecret ? (
        <Elements options={options} stripe={stripePromise}>
          <PaymentForm /> 
        </Elements>
      ) : (
        !error && <p>Đang tải cổng thanh toán an toàn...</p>
      )}
    </div>
  );
}