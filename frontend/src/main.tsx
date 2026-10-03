import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

class ErrorBoundary extends React.Component<{ children: React.ReactNode }, { error: Error | null }> {
  state = { error: null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  render() {
    if (this.state.error) {
      return (
        <div style={{ minHeight: '100vh', background: '#0B1120', color: '#e2e8f0', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 16, padding: 32 }}>
          <h1 style={{ fontSize: 24, fontWeight: 700 }}>upay Pulse — Startup Error</h1>
          <pre style={{ background: '#1e293b', padding: 16, borderRadius: 12, fontSize: 12, maxWidth: 600, overflow: 'auto', color: '#f87171' }}>
            {(this.state.error as Error).message}
          </pre>
          <p style={{ fontSize: 13, color: '#94a3b8' }}>Check that VITE_API_BASE_URL is set correctly and the backend is reachable.</p>
          <button onClick={() => window.location.reload()} style={{ padding: '10px 24px', background: '#0ea5e9', borderRadius: 8, border: 'none', color: '#fff', fontWeight: 700, cursor: 'pointer' }}>Reload</button>
        </div>
      );
    }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <ErrorBoundary>
    <App />
  </ErrorBoundary>,
);
