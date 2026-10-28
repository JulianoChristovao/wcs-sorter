import { useEffect, useState, type FormEvent } from 'react'
import { pedidosApi } from '../api/client'
import type { Pedido } from '../types'
import { useAuth } from '../context/AuthContext'

const statusColors: Record<string, string> = {
  recebido: 'bg-slate-100 text-slate-700',
  pendente: 'bg-amber-100 text-amber-800',
  em_processamento: 'bg-blue-100 text-blue-800',
  separado: 'bg-emerald-100 text-emerald-800',
  enviado_wms: 'bg-green-100 text-green-800',
  erro: 'bg-red-100 text-red-800',
  cancelado: 'bg-gray-100 text-gray-600',
}

export default function Pedidos() {
  const { isAdmin } = useAuth()
  const [items, setItems] = useState<Pedido[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState('')
  const [codigoFilter, setCodigoFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    etiqueta: '',
    codigo_externo: '',
    sigla: '',
    uf: '',
    filial: '',
  })
  const [msg, setMsg] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const { data } = await pedidosApi.list({
        status: statusFilter || undefined,
        codigo: codigoFilter || undefined,
        page,
        size: 20,
      })
      setItems(data.items)
      setTotal(data.total)
    } catch {
      setMsg('Erro ao carregar pedidos.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [page, statusFilter])

  const handleSearch = (e: FormEvent) => {
    e.preventDefault()
    setPage(1)
    load()
  }

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault()
    try {
      await pedidosApi.create({
        etiqueta: form.etiqueta.trim(),
        codigo_externo: form.codigo_externo || undefined,
        sigla: form.sigla.trim() || undefined,
        UF: form.uf.trim() || undefined,
        Filial: form.filial.trim() || undefined,
      })
      setMsg('Pedido criado com sucesso.')
      setShowForm(false)
      setForm({
        etiqueta: '',
        codigo_externo: '',
        sigla: '',
        uf: '',
        filial: '',
      })
      load()
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Erro ao criar pedido.'
      setMsg(String(detail))
    }
  }

  const handleExcluir = async (p: Pedido) => {
    if (!window.confirm(`Excluir pedido ${p.etiqueta}?`)) return
    try {
      const force = ['separado', 'enviado_wms'].includes(p.status)
      if (force && !window.confirm('Pedido já processado. Confirma exclusão forçada?')) return
      await pedidosApi.remove(p.id, force)
      setMsg(`Pedido ${p.etiqueta} excluído.`)
      load()
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Erro ao excluir.'
      setMsg(String(detail))
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-xl font-bold text-slate-800">Pedidos</h1>
        {isAdmin ? (
          <button
            onClick={() => setShowForm(!showForm)}
            className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg"
          >
            {showForm ? 'Cancelar' : '+ Novo pedido (simular WMS)'}
          </button>
        ) : (
          <span className="text-sm text-slate-500">Modo consulta</span>
        )}
      </div>

      {msg && (
        <div className="bg-blue-50 border border-blue-200 text-blue-800 text-sm rounded-lg px-4 py-2">
          {msg}
        </div>
      )}

      {showForm && isAdmin && (
        <form
          onSubmit={handleCreate}
          className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm grid grid-cols-1 sm:grid-cols-2 gap-4"
        >
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Etiqueta de rastreio *
            </label>
            <input
              required
              value={form.etiqueta}
              onChange={(e) => setForm({ ...form, etiqueta: e.target.value })}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
              placeholder="FFFF45678"
            />
            <p className="text-xs text-slate-400 mt-1">
              Única etiqueta de rastreio do volume (enviada pelo WMS)
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Sigla</label>
            <input
              value={form.sigla}
              onChange={(e) => setForm({ ...form, sigla: e.target.value })}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm uppercase"
              placeholder="SAO"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">UF</label>
            <input
              value={form.uf}
              onChange={(e) => setForm({ ...form, uf: e.target.value })}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm uppercase"
              placeholder="SP"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Filial</label>
            <input
              value={form.filial}
              onChange={(e) => setForm({ ...form, filial: e.target.value })}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
              placeholder="Braz"
            />
          </div>
          <p className="sm:col-span-2 text-xs text-slate-400">
            Informe ao menos um destino (sigla, UF ou filial). O mapa habilitado usa apenas o critério configurado.
          </p>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Código externo (WMS)
            </label>
            <input
              value={form.codigo_externo}
              onChange={(e) => setForm({ ...form, codigo_externo: e.target.value })}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
              placeholder="NF-111111111111111"
            />
            <p className="text-xs text-slate-400 mt-1">
              ID do documento/pedido no WMS (NF, pedido, etc.)
            </p>
          </div>
          <div className="sm:col-span-2">
            <button
              type="submit"
              className="bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium px-4 py-2 rounded-lg"
            >
              Criar pedido
            </button>
          </div>
        </form>
      )}

      <form onSubmit={handleSearch} className="flex flex-wrap gap-3 items-end">
        <div>
          <label className="block text-xs text-slate-500 mb-1">Status</label>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value)
              setPage(1)
            }}
            className="border border-slate-300 rounded-lg px-3 py-2 text-sm"
          >
            <option value="">Todos</option>
            <option value="pendente">Pendente</option>
            <option value="recebido">Recebido</option>
            <option value="em_processamento">Em processamento</option>
            <option value="separado">Separado</option>
            <option value="enviado_wms">Enviado WMS</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-slate-500 mb-1">Etiqueta</label>
          <input
            value={codigoFilter}
            onChange={(e) => setCodigoFilter(e.target.value)}
            className="border border-slate-300 rounded-lg px-3 py-2 text-sm"
            placeholder="Buscar etiqueta..."
          />
        </div>
        <button
          type="submit"
          className="bg-slate-700 hover:bg-slate-800 text-white text-sm px-4 py-2 rounded-lg"
        >
          Filtrar
        </button>
      </form>

      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-slate-600">
            <tr>
              <th className="px-4 py-3 font-medium">Etiqueta</th>
              <th className="px-4 py-3 font-medium">Cód. externo</th>
              <th className="px-4 py-3 font-medium">Destino</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Altura</th>
              <th className="px-4 py-3 font-medium">Largura</th>
              <th className="px-4 py-3 font-medium">Compr.</th>
              <th className="px-4 py-3 font-medium">Peso</th>
              <th className="px-4 py-3 font-medium">Saída</th>
              <th className="px-4 py-3 font-medium">Criado em</th>
              {isAdmin && <th className="px-4 py-3 font-medium"></th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              <tr>
                <td colSpan={12} className="px-4 py-8 text-center text-slate-400">
                  Carregando...
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={12} className="px-4 py-8 text-center text-slate-400">
                  Nenhum pedido encontrado.
                </td>
              </tr>
            ) : (
              items.map((p) => (
                <tr key={p.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-mono font-medium">{p.etiqueta}</td>
                  <td className="px-4 py-3 text-slate-500">{p.codigo_externo || '—'}</td>
                  <td className="px-4 py-3 text-xs">
                    {p.sigla && (
                      <span className="bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded font-medium mr-1">
                        {p.sigla}
                      </span>
                    )}
                    {p.uf && (
                      <span className="bg-sky-50 text-sky-700 px-2 py-0.5 rounded font-medium mr-1">
                        {p.uf}
                      </span>
                    )}
                    {p.filial && (
                      <span className="bg-amber-50 text-amber-800 px-2 py-0.5 rounded font-medium mr-1">
                        {p.filial}
                      </span>
                    )}
                    {!p.sigla && !p.uf && !p.filial && (
                      <span className="bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                        {p.rota_codigo}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium ${
                        statusColors[p.status] ?? 'bg-slate-100'
                      }`}
                    >
                      {p.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{p.altura_cm ?? '—'}</td>
                  <td className="px-4 py-3 text-slate-600">{p.largura_cm ?? '—'}</td>
                  <td className="px-4 py-3 text-slate-600">{p.comprimento_cm ?? '—'}</td>
                  <td className="px-4 py-3 text-slate-600">{p.peso_kg ?? '—'}</td>
                  <td className="px-4 py-3 text-slate-600">{p.saida_confirmada ?? '—'}</td>
                  <td className="px-4 py-3 text-slate-500">
                    {new Date(p.created_at).toLocaleString('pt-BR')}
                  </td>
                  {isAdmin && (
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        onClick={() => handleExcluir(p)}
                        className="text-xs text-red-600 hover:text-red-800 font-medium"
                      >
                        Excluir
                      </button>
                    </td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {total > 20 && (
        <div className="flex items-center gap-3 text-sm">
          <button
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
            className="px-3 py-1 border rounded disabled:opacity-40"
          >
            Anterior
          </button>
          <span className="text-slate-500">
            Página {page} — {total} total
          </span>
          <button
            disabled={page * 20 >= total}
            onClick={() => setPage((p) => p + 1)}
            className="px-3 py-1 border rounded disabled:opacity-40"
          >
            Próxima
          </button>
        </div>
      )}
    </div>
  )
}
