import { useState } from 'react';
import Checkout from './components/Checkout';
import ProductList from './components/ProductList';

function App() {
  const [selectedProduct, setSelectedProduct] = useState(null);

  return (
    <div style={{
      display: 'flex', justifyContent: 'center', alignItems: 'center', flexDirection: 'column',
      minHeight: '100vh', backgroundColor: '#1a1a1a', fontFamily: 'Arial, sans-serif',
      color: 'white'
    }}>
      {/* Nút quay lại nếu đang ở trang thanh toán */}
      {selectedProduct && (
        <button 
          onClick={() => setSelectedProduct(null)}
          style={{
            position: 'absolute', top: '20px', left: '20px', padding: '8px 16px',
            backgroundColor: 'transparent', border: '1px solid #fff', color: '#fff',
            borderRadius: '4px', cursor: 'pointer'
          }}
        >
          ← Quay lại cửa hàng
        </button>
      )}

      {!selectedProduct ? (
        <ProductList onSelectProduct={setSelectedProduct} />
      ) : (
        <Checkout product={selectedProduct} />
      )}
    </div>
  );
}

export default App;