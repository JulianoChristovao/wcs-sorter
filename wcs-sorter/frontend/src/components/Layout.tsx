import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const navItems = [
  { to: '/', label: 'Dashboard', roles: ['admin', 'gestor', 'operador'] },
  { to: '/pedidos', label: 'Pedidos', roles: ['admin', 'gestor', 'operador'] },
  { to: '/mapeamento', label: 'Mapeamento', roles: ['admin', 'gestor', 'operador'] },
  { to: '/logs', label: 'Logs', roles: ['admin'] },
  { to: '/usuarios', label: 'Usuários', roles: ['admin', 'gestor'] },
]

export default function Layout() {
  const { user, logout, isGestor } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const visibleNav = navItems.filter((item) =>
    item.roles.includes(user?.role ?? '')
  )

  return (
    <div className="min-h-screen flex bg-slate-100">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900 text-white flex flex-col shrink-0">
        <div className="p-5 border-b border-slate-700">
          <h1 className="text-xl font-bold tracking-tight">WCS Sorter</h1>
          <p className="text-xs text-slate-400 mt-1">Warehouse Control System</p>
        </div>

        <nav className="flex-1 p-3 space-y-1">
          {visibleNav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `block px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-slate-700">
          <div className="text-sm">
            <p className="font-medium truncate">{user?.nome_completo}</p>
            <p className="text-xs text-slate-400 capitalize">{user?.role}</p>
          </div>
          <button
            onClick={handleLogout}
            className="mt-3 w-full text-left text-sm text-slate-400 hover:text-white transition-colors"
          >
            Sair
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto">
        <header className="bg-white border-b border-slate-200 px-6 py-4 sticky top-0 z-10">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-800">
              Sistema de Controle de Armazém
            </h2>
            {user?.role === 'admin' && (
              <span className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded-full font-medium">
                Acesso Admin
              </span>
            )}
            {user?.role === 'gestor' && (
              <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-full font-medium">
                Acesso Gestor
              </span>
            )}
            {user?.role === 'operador' && (
              <span className="text-xs bg-slate-100 text-slate-600 px-2 py-1 rounded-full font-medium">
                Acesso Operador
              </span>
            )}
          </div>
        </header>
        <div className="p-6">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
