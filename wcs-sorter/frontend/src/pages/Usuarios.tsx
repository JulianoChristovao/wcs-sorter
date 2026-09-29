import { useEffect, useState, type FormEvent } from 'react'
import { usuariosApi } from '../api/client'
import type { User } from '../types'
import { useAuth } from '../context/AuthContext'

export default function Usuarios() {
  const { isAdmin, user: currentUser } = useAuth()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [msg, setMsg] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    username: '',
    email: '',
    nome_completo: '',
    password: '',
    role: 'operador',
  })

  const load = async () => {
    setLoading(true)
    try {
      const { data } = await usuariosApi.list()
      setUsers(data)
    } catch {
      setMsg('Erro ao carregar usuários.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault()
    try {
      await usuariosApi.create(form)
      setMsg(`Usuário ${form.username} criado.`)
      setShowForm(false)
      setForm({
        username: '',
        email: '',
        nome_completo: '',
        password: '',
        role: 'operador',
      })
      load()
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Erro ao criar usuário.'
      setMsg(String(detail))
    }
  }

  const toggleAtivo = async (u: User) => {
    if (u.id === currentUser?.id) {
      setMsg('Você não pode desativar a si mesmo.')
      return
    }
    try {
      await usuariosApi.update(u.id, { ativo: !u.ativo })
      setMsg(`Usuário ${u.username} ${u.ativo ? 'desativado' : 'ativado'}.`)
      load()
    } catch {
      setMsg('Erro ao atualizar usuário.')
    }
  }

  const roleBadge: Record<string, string> = {
    admin: 'bg-purple-100 text-purple-800',
    gestor: 'bg-blue-100 text-blue-800',
    operador: 'bg-slate-100 text-slate-700',
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-slate-800">Usuários</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg"
        >
          {showForm ? 'Cancelar' : '+ Novo usuário'}
        </button>
      </div>

      {msg && (
        <div className="bg-blue-50 border border-blue-200 text-blue-800 text-sm rounded-lg px-4 py-2">
          {msg}
        </div>
      )}

      {showForm && (
        <form
          onSubmit={handleCreate}
          className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm grid grid-cols-1 sm:grid-cols-2 gap-4"
        >
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Username *</label>
            <input
              required
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">E-mail *</label>
            <input
              required
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Nome completo *
            </label>
            <input
              required
              value={form.nome_completo}
              onChange={(e) => setForm({ ...form, nome_completo: e.target.value })}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Senha *</label>
            <input
              required
              type="password"
              minLength={8}
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Papel *</label>
            <select
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value })}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
            >
              <option value="operador">Operador</option>
              <option value="gestor">Gestor</option>
              {isAdmin && <option value="admin">Admin</option>}
            </select>
          </div>
          <div className="flex items-end">
            <button
              type="submit"
              className="bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium px-4 py-2 rounded-lg"
            >
              Criar usuário
            </button>
          </div>
        </form>
      )}

      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-slate-600">
            <tr>
              <th className="px-4 py-3 font-medium">Usuário</th>
              <th className="px-4 py-3 font-medium">Nome</th>
              <th className="px-4 py-3 font-medium">E-mail</th>
              <th className="px-4 py-3 font-medium">Papel</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-slate-400">
                  Carregando...
                </td>
              </tr>
            ) : (
              users.map((u) => (
                <tr key={u.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium">{u.username}</td>
                  <td className="px-4 py-3">{u.nome_completo}</td>
                  <td className="px-4 py-3 text-slate-500">{u.email}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium capitalize ${
                        roleBadge[u.role] ?? ''
                      }`}
                    >
                      {u.role}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`text-xs font-medium ${
                        u.ativo ? 'text-emerald-600' : 'text-red-500'
                      }`}
                    >
                      {u.ativo ? 'Ativo' : 'Inativo'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => toggleAtivo(u)}
                      className="text-xs text-blue-600 hover:underline"
                    >
                      {u.ativo ? 'Desativar' : 'Ativar'}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
