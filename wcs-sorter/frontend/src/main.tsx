import { StrictMode, Component, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

class ErrorBoundary extends Component<{ children: ReactNode }, { error: string | null }> {
  state = { error: null as string | null }

  static getDerivedStateFromError(err: Error) {
    return { error: err.message || 'Erro ao carregar a interface.' }
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 32, fontFamily: 'system-ui, sans-serif', color: '#0f172a' }}>
          <h1 style={{ fontSize: 20, marginBottom: 8 }}>Não foi possível abrir o WCS</h1>
          <p style={{ color: '#b91c1c' }}>{this.state.error}</p>
          <p style={{ marginTop: 16, color: '#475569' }}>
            Atualize a página (Ctrl+Shift+R). Se continuar, veja o console do navegador (F12).
          </p>
        </div>
      )
    }
    return this.props.children
  }
}

const root = document.getElementById('root')
if (!root) {
  throw new Error('Elemento #root não encontrado')
}

createRoot(root).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>
)
