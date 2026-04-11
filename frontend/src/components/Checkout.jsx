// frontend/src/components/Checkout.jsx
import { useState, useEffect } from "react";
import { loadStripe } from "@stripe/stripe-js";
import { Elements } from "@stripe/react-stripe-js";
import PaymentForm from "./PaymentForm";

const stripePromise = loadStripe('pk_test_51TE1cpLEdwXIMzQb1PF9p7ixh7vm612NQYjL8Xu0TnxLEwvky3S7oO62fWocy132Do7sX4DFxFK96UPtu07sGBVP009X6bHnpe');

export default function Checkout({ product,session }) {
  const options ={
    clientSecret: session.clientSecret,
    appearance: { theme: 'night', variables: { colorPrimary: '#00f2fe' } },
  }

  return (
    <div style={{ width: '100%', display: 'flex', justifyContent: 'center', padding: '20px' }}>
      <Elements stripe={stripePromise} options={options}>
        <PaymentForm 
          product={product} 
          orderData={session.orderData} 
          userEmail={session.email} 
        />
      </Elements>
    </div>
  );
}