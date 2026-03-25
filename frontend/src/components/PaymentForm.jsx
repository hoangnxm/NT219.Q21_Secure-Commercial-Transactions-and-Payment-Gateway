import { useState } from "react";
import { PaymentElement, useStripe, useElements } from "@stripe/react-stripe-js";

export default function PaymentForm() {
  const stripe = useStripe();
  const elements = useElements();

  const [message, setMessage] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Nếu thư viện Stripe chưa load xong thì không làm gì cả
    if (!stripe || !elements) {
      return;
    }

    setIsProcessing(true);

    // Bắt đầu luồng xác nhận thanh toán (tự động xử lý 3D-Secure nếu thẻ yêu cầu)
    const { error } = await stripe.confirmPayment({
      elements,
      confirmParams: {
        // Sau khi thanh toán xong (hoặc gõ OTP 3DS xong), nó sẽ văng về link này.
        // Mày có thể tạo thêm 1 trang /success để hứng nó sau.
        return_url: "http://localhost:5173/success", 
      },
    });

    // Nếu có lỗi (sai số thẻ, hết tiền, từ chối...) thì show ra
    if (error) {
      if (error.type === "card_error" || error.type === "validation_error") {
        setMessage(error.message);
      } else {
        setMessage("Có lỗi đéo gì đó xảy ra rồi, check lại mạng hoặc thẻ test đi.");
      }
    }

    setIsProcessing(false);
  };

  return (
    <form id="payment-form" onSubmit={handleSubmit} style={{ marginTop: "20px" }}>
      {/* Đây là cái cục thần thánh chứa ô nhập số thẻ, ngày hết hạn, CVC của Stripe */}
      <PaymentElement id="payment-element" />

      <button 
        disabled={isProcessing || !stripe || !elements} 
        id="submit"
        style={{
          marginTop: "20px",
          padding: "10px 20px",
          backgroundColor: "#5469d4",
          color: "white",
          border: "none",
          borderRadius: "4px",
          cursor: isProcessing ? "not-allowed" : "pointer",
          width: "100%"
        }}
      >
        <span id="button-text">
          {isProcessing ? "Đang xử lý..." : "Thanh toán ngay"}
        </span>
      </button>

      {/* Hiển thị câu chửi/lỗi báo về từ Stripe nếu user nhập bậy */}
      {message && <div id="payment-message" style={{ color: "red", marginTop: "10px" }}>{message}</div>}
    </form>
  );
}