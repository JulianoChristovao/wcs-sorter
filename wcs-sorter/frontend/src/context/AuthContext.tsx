import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import type { User } from '../types'
import { authApi } from '../api/client'

interface AuthContextType {
  user: User | null
  token: string | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  isAdmin: boolean
  isGestor: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(localStorage.getItem('wcs_token'))
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const stored = localStorage.getItem('wcs_user')
    if (token && stored) {
      try {
        setUser(JSON.parse(stored))
      } catch {
        localStorage.removeItem('wcs_user')
        localStorage.removeItem('wcs_token')
        setToken(null)
      }
    }
    setLoading(false)
  }, [token])

  const login = async (username: string, password: string) => {
    const { data } = await authApi.login(username, password)
    localStorage.setItem('wcs_token', data.access_token)
    localStorage.setItem('wcs_user', JSON.stringify(data.user))
    setToken(data.access_token)
    setUser(data.user)
  }

  const logout = () => {
    localStorage.removeItem('wcs_token')
    localStorage.removeItem('wcs_user')
    setToken(null)
    setUser(null)
  }

  const isAdmin = user?.role === 'admin'
  const isGestor = user?.role === 'admin' || user?.role === 'gestor'

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout, isAdmin, isGestor }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
