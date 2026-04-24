import { use, useState } from 'react';
import Checkout from './components/Checkout';
import ProductList from './components/ProductList';

function App() {
  const [selectedProduct, setSelectedProduct] = useState(null);
  // State quản lý Popup Modal và AI Check
  const [showModal, setShowModal] = useState(false);
  const [email,setEmail] = useState('');
  const [isChecking,setIsChecking] = useState(false);
  const [errorMsg,setErrorMsg] = useState('')
  // Lưu phiên thanh toán khi AI cho qua
  const [checkoutSession, setCheckoutSession] = useState(null);

  const handleBuyClick = (product) => {
    setSelectedProduct(product);
    setShowModal(true);
    setErrorMsg('');
  }

  const closeModal = () =>{
    setShowModal(false);
    setSelectedProduct(null);
    setEmail('')
  }

  const handleVerifyEmail = async () =>{
    if (!email) {
      setErrorMsg("Vui lòng nhập email!");
      return;
    }
    setIsChecking(true);
    setErrorMsg('');

    try {
      const response = await fetch('http://localhost:8080/order/api/orders/create',{
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          product_id: selectedProduct.id,
          quantity: 1,
          email: email
        }),
      });

      const data = await response.json();
      if(response.ok && data.status === 'success'){
        // Nếu AI cho qua, lưu client_secret và cho qua checkout
        setCheckoutSession({
          clientSecret: data.client_secret,
          orderData: data,
          email: email
        });
        setShowModal(false);
      }else{
        // AI CHẶN -> Báo lỗi đỏ ngay trên popup
        setErrorMsg(data.error || data.detail || 'Lỗi giao dịch!');
      }

    } catch (err) {
      setErrorMsg('Lỗi kết nối đến Server AI!');
    } finally{
      setIsChecking(false);
    }
  };

  const handleBackToStore = () => {
    setCheckoutSession(null);
    setSelectedProduct(null);
    setEmail('');
  };

  return (
    <div style={{
      display: 'flex', justifyContent: 'center', alignItems: 'center', flexDirection: 'column',
      minHeight: '100vh', backgroundColor: '#1a1a1a', fontFamily: 'Arial, sans-serif',
      color: 'white'
    }}>
      {/* Nút quay lại nếu đang ở trang thanh toán */}
      {checkoutSession && (
        <button onClick={handleBackToStore} style={styles.backBtn}>
          ← Quay lại cửa hàng
        </button>
      )}

      {/* Điều hướng: Có Session thì qua Checkout, chưa có thì ở ProductList */}
      {!checkoutSession ? (
        <ProductList onSelectProduct={handleBuyClick} />
      ) : (
        <Checkout product={selectedProduct} session={checkoutSession} />
      )}

      {/* Popup nhập email */}
      {showModal && (
        <div style={styles.modalOverlay}>
          <div style={styles.modalContent}>
            <button onClick={closeModal} style={styles.closeBtn}>×</button>
            <h3 style={{ color: '#00f2fe', marginTop: 0 }}>XÁC THỰC BẢO MẬT</h3>
            <p style={{ fontSize: '13px', color: '#aaa', marginBottom: '20px' }}>
              Vui lòng nhập email trước khi thanh toán.
            </p>
            
            <input 
              type="email" 
              placeholder="Nhập email của bạn..." 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={styles.modalInput}
            />
            
            <button onClick={handleVerifyEmail} disabled={isChecking} style={styles.modalBtn}>
              {isChecking ? 'ĐANG KIỂM TRA...' : 'TIẾP TỤC'}
            </button>

            {errorMsg && <div style={styles.errorMsg}>❌ {errorMsg}</div>}
          </div>
        </div>
      )}
    </div>
  );
}

const styles = {
  backBtn: { position: 'absolute', top: '20px', left: '20px', padding: '8px 16px', backgroundColor: 'transparent', border: '1px solid #fff', color: '#fff', borderRadius: '4px', cursor: 'pointer' },
  modalOverlay: { position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', backgroundColor: 'rgba(0,0,0,0.8)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 },
  modalContent: { background: '#24243e', padding: '30px', borderRadius: '16px', width: '350px', border: '1px solid #00f2fe', textAlign: 'center', position: 'relative', boxShadow: '0 0 30px rgba(0, 242, 254, 0.2)' },
  closeBtn: { position: 'absolute', top: '10px', right: '15px', background: 'none', border: 'none', color: '#fff', fontSize: '24px', cursor: 'pointer' },
  modalInput: { width: '100%', padding: '12px', borderRadius: '8px', border: '1px solid #555', background: '#111', color: '#fff', marginBottom: '15px', boxSizing: 'border-box' },
  modalBtn: { width: '100%', padding: '12px', background: 'linear-gradient(to right, #00f2fe, #4facfe)', color: '#fff', border: 'none', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer' },
  errorMsg: { marginTop: '15px', padding: '10px', background: 'rgba(255,0,0,0.1)', color: '#ff4757', borderRadius: '8px', fontSize: '13px' }
};

export default App;