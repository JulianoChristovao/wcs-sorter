import { useEffect, useState } from 'react'
import { dashboardApi } from '../api/client'
import type { DashboardKpis } from '../types'

function KpiCard({
  title,
  value,
  subtitle,
  color,
}: {
  title: string
  value: string | number
  subtitle?: string
  color: string
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
      <p className="text-sm font-medium text-slate-500">{title}</p>
      <p className={`text-3xl font-bold mt-1 ${color}`}>{value}</p>
      {subtitle && <p className="text-xs text-slate-400 mt-1">{subtitle}</p>}
    </div>
  )
}

export default function Dashboard() {
  const [kpis, setKpis] = useState<DashboardKpis | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = async () => {
    try {
      setLoading(true)
      const { data } = await dashboardApi.kpis()
      setKpis(data)
      setError('')
    } catch {
      setError('Não foi possível carregar os KPIs.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const interval = setInterval(load, 30000)
    return () => clearInterval(interval)
  }, [])

  if (loading && !kpis) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500">
        Carregando dashboard...
      </div>
    )
  }

  if (error && !kpis) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4">
        {error}
      </div>
    )
  }

  if (!kpis) return null

  const statusLabels: Record<string, string> = {
    recebido: 'Recebido',
    pendente: 'Pendente',
    em_processamento: 'Em processamento',
    separado: 'Separado',
    enviado_wms: 'Enviado ao WMS',
    erro: 'Erro',
    cancelado: 'Cancelado',
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-slate-800">Dashboard</h1>
        <button
          onClick={load}
          className="text-sm text-blue-600 hover:text-blue-800 font-medium"
        >
          Atualizar
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          title="Pedidos pendentes"
          value={kpis.pendentes}
          color="text-amber-600"
          subtitle="Aguardando sorter"
        />
        <KpiCard
          title="Separados hoje"
          value={kpis.separados_hoje}
          color="text-emerald-600"
          subtitle="Confirmados"
        />
        <KpiCard
          title="Consultas (24h)"
          value={kpis.consultas_24h}
          color="text-blue-600"
          subtitle={`Taxa de sucesso: ${kpis.taxa_sucesso_percent}%`}
        />
        <KpiCard
          title="Tempo médio"
          value={`${kpis.tempo_medio_resposta_ms} ms`}
          color="text-violet-600"
          subtitle="Resposta do sorter"
        />
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-700 mb-4">
          Pedidos por status
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {Object.entries(kpis.por_status).map(([status, count]) => (
            <div
              key={status}
              className="flex items-center justify-between bg-slate-50 rounded-lg px-3 py-2"
            >
              <span className="text-sm text-slate-600">
                {statusLabels[status] ?? status}
              </span>
              <span className="text-sm font-bold text-slate-800">{count}</span>
            </div>
          ))}
          {Object.keys(kpis.por_status).length === 0 && (
            <p className="text-sm text-slate-400 col-span-full">
              Nenhum pedido registrado ainda.
            </p>
          )}
        </div>
      </div>

      <p className="text-xs text-slate-400">
        Atualizado em: {new Date(kpis.atualizado_em).toLocaleString('pt-BR')}
      </p>
    </div>
  )
}
