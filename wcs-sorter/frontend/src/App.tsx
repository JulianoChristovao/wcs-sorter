import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Pedidos from './pages/Pedidos'
import MapeamentoPage from './pages/Mapeamento'
import Usuarios from './pages/Usuarios'
import Logs from './pages/Logs'
import type { ReactNode } from 'react'

function PrivateRoute({ children }: { children: ReactNode }) {
  const { token, user, loading } = useAuth()
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-slate-500">
        Carregando...
      </div>
    )
  }
  if (!token || !user) return <Navigate to="/login" replace />
  return <>{children}</>
}

function GestorRoute({ children }: { children: ReactNode }) {
  const { isGestor } = useAuth()
  if (!isGestor) return <Navigate to="/" replace />
  return <>{children}</>
}

function AdminRoute({ children }: { children: ReactNode }) {
  const { isAdmin } = useAuth()
  if (!isAdmin) return <Navigate to="/" replace />
  return <>{children}</>
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <PrivateRoute>
            <Layout />
          </PrivateRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="pedidos" element={<Pedidos />} />
        <Route path="mapeamento" element={<MapeamentoPage />} />
        <Route
          path="logs"
          element={
            <AdminRoute>
              <Logs />
            </AdminRoute>
          }
        />
        <Route
          path="usuarios"
          element={
            <GestorRoute>
              <Usuarios />
            </GestorRoute>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}
