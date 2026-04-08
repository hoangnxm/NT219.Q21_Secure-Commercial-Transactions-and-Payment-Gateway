import Checkout from './Checkout';

function App() {
  return (
    <div style={{
      display: 'flex', justifyContent: 'center', alignItems: 'center',
      minHeight: '100vh', backgroundColor: '#1a1a1a', fontFamily: 'Arial, sans-serif',
      color: 'white'
    }}>
      <Checkout />
    </div>
  );
}

export default App;