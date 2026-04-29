import React, { useState, useEffect } from 'react';

export default function ProductList({ onSelectProduct }) {
  const [products, setProducts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  // Gọi API lấy dữ liệu thật từ Backend khi vừa load trang
  useEffect(() => {
    fetch('http://localhost:5000/api/products', { cache: 'no-store' })
      .then(response => response.json())
      .then(data => {
        if (data.status === "success") {
          setProducts(data.data);
        }
      })
      .catch(error => console.error("❌ Lỗi lấy data:", error))
      .finally(() => setIsLoading(false));
  }, []);

  // Hàm phụ để random icon cho sinh động (vì DB không có cột lưu hình)
  const getIcon = (id) => {
    if (id.includes("RAM") || id.includes("SP01")) return "💾";
    if (id.includes("AO") || id.includes("SP02")) return "👕";
    return "📦";
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={styles.headerTop}>
          <h1 style={styles.logo}>SECURE <span style={{ color: '#00f2fe' }}>STORE</span></h1>
          <button style={styles.cartBtn}>
            🛒 Giỏ hàng <span style={styles.cartBadge}>{products.length}</span>
          </button>
        </div>
      </div>

      <div style={styles.mainContent}>
        <h2 style={styles.sectionTitle}>Danh mục sản phẩm</h2>

        {isLoading ? (
          <p style={{ textAlign: 'center', color: '#00f2fe', fontSize: '18px' }}>⏳ Đang tải kho hàng...</p>
        ) : products.length === 0 ? (
          <p style={{ textAlign: 'center', color: '#ff4757', fontSize: '18px' }}>❌ Kho đang trống, hãy dùng API POST /api/products để nhập hàng!</p>
        ) : (
          <div style={styles.productGrid}>
            {products.map((product) => (
              <div key={product.id} style={styles.productCard}>
                
                {/* Thay discount thành hiển thị số lượng tồn kho */}
                <div style={styles.stockBadge}>Kho: {product.stock}</div>
                
                <div style={styles.imageContainer}>
                  <span style={{ fontSize: '70px', filter: 'drop-shadow(0 0 10px rgba(255,255,255,0.3))' }}>
                    {getIcon(product.id)}
                  </span>
                </div>

                <div style={styles.productInfo}>
                  <h3 style={styles.productName}>{product.name}</h3>
                  <p style={styles.productPrice}>
                    {new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(product.price)}
                  </p>
                  
                  <button 
                    style={styles.buyBtn}
                    onClick={() => onSelectProduct(product)}
                  >
                    MUA NGAY
                  </button>
                </div>

              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// --- CSS TRONG JS (Giữ nguyên phong cách Kính mờ của tin nhắn trước) ---
const styles = {
  container: {
    width: '100%', maxWidth: '1000px', margin: '20px auto',
    background: 'linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%)',
    fontFamily: "'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
    borderRadius: '24px', boxShadow: '0 25px 50px rgba(0,0,0,0.5)',
    border: '1px solid rgba(255,255,255,0.1)', minHeight: '85vh',
    color: '#fff', padding: '30px', boxSizing: 'border-box'
  },
  header: {
    background: 'rgba(255,255,255,0.03)', borderRadius: '16px',
    padding: '20px 30px', marginBottom: '40px',
    border: '1px solid rgba(255,255,255,0.05)', backdropFilter: 'blur(10px)'
  },
  headerTop: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  logo: { fontSize: '26px', fontWeight: '800', letterSpacing: '2px', margin: 0, textShadow: '0 0 15px rgba(0, 242, 254, 0.5)' },
  cartBtn: {
    backgroundColor: 'rgba(0, 242, 254, 0.1)', color: '#00f2fe', border: '1px solid rgba(0, 242, 254, 0.3)',
    padding: '10px 20px', borderRadius: '12px', fontWeight: 'bold', fontSize: '15px',
    display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer'
  },
  cartBadge: { backgroundColor: '#00f2fe', color: '#000', padding: '2px 8px', borderRadius: '8px', fontSize: '13px', fontWeight: '900' },
  mainContent: { padding: '0 10px' },
  sectionTitle: { fontSize: '20px', fontWeight: '600', marginBottom: '25px', color: '#cbd5e1', textTransform: 'uppercase', letterSpacing: '1px' },
  productGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '30px' },
  productCard: {
    background: 'rgba(255,255,255,0.04)', borderRadius: '20px', padding: '25px 20px',
    position: 'relative', border: '1px solid rgba(255,255,255,0.08)', backdropFilter: 'blur(8px)',
    display: 'flex', flexDirection: 'column', alignItems: 'center', boxShadow: '0 15px 35px rgba(0,0,0,0.2)'
  },
  stockBadge: {
    position: 'absolute', top: '15px', left: '15px',
    background: 'rgba(46, 213, 115, 0.2)', color: '#2ed573', border: '1px solid #2ed573',
    padding: '6px 12px', borderRadius: '8px', fontSize: '12px', fontWeight: 'bold'
  },
  imageContainer: {
    width: '100%', height: '160px', background: 'rgba(0,0,0,0.2)', borderRadius: '16px',
    display: 'flex', justifyContent: 'center', alignItems: 'center', marginBottom: '25px', border: '1px dashed rgba(255,255,255,0.1)'
  },
  productInfo: { width: '100%', textAlign: 'center' },
  productName: { fontSize: '18px', fontWeight: '600', color: '#fff', margin: '0 0 10px 0' },
  productPrice: { fontSize: '24px', fontWeight: 'bold', color: '#00f2fe', margin: '0 0 25px 0', textShadow: '0 0 15px rgba(0, 242, 254, 0.4)' },
  buyBtn: {
    width: '100%', padding: '14px', background: 'linear-gradient(to right, #667eea 0%, #764ba2 100%)',
    color: 'white', border: 'none', borderRadius: '12px', fontSize: '15px', fontWeight: 'bold',
    cursor: 'pointer', boxShadow: '0 10px 20px rgba(118, 75, 162, 0.3)'
  }
};