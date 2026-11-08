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

function toLocalInputValue(d: Date) {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function localInputToIso(value: string) {
  if (!value) return undefined
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? undefined : d.toISOString()
}

export default function Dashboard() {
  const now = new Date()
  const defaultInicio = new Date(now.getTime() - 24 * 60 * 60 * 1000)

  const [inicio, setInicio] = useState(toLocalInputValue(defaultInicio))
  const [fim, setFim] = useState(toLocalInputValue(now))
  const [kpis, setKpis] = useState<DashboardKpis | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = async (ini = inicio, fi = fim) => {
    try {
      setLoading(true)
      const { data } = await dashboardApi.kpis({
        inicio: localInputToIso(ini),
        fim: localInputToIso(fi),
      })
      setKpis(data)
      setError('')
    } catch {
      setError('Não foi possível carregar os KPIs.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const aplicarPreset = (horas: number) => {
    const fimNow = new Date()
    const ini = new Date(fimNow.getTime() - horas * 60 * 60 * 1000)
    const iniStr = toLocalInputValue(ini)
    const fimStr = toLocalInputValue(fimNow)
    setInicio(iniStr)
    setFim(fimStr)
    void load(iniStr, fimStr)
  }

  const statusLabels: Record<string, string> = {
    recebido: 'Recebido',
    pendente: 'Pendente',
    em_processamento: 'Em processamento',
    separado: 'Separado',
    enviado_wms: 'Enviado ao WMS',
    erro: 'Erro',
    cancelado: 'Cancelado',
  }

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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-xl font-bold text-slate-800">Dashboard</h1>
        <button
          type="button"
          onClick={() => void load()}
          className="text-sm text-blue-600 hover:text-blue-800 font-medium"
        >
          Atualizar
        </button>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
        <p className="text-sm font-medium text-slate-700">Período</p>
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="block text-xs text-slate-500 mb-1">Início</label>
            <input
              type="datetime-local"
              value={inicio}
              onChange={(e) => setInicio(e.target.value)}
              className="border border-slate-300 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">Fim</label>
            <input
              type="datetime-local"
              value={fim}
              onChange={(e) => setFim(e.target.value)}
              className="border border-slate-300 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <button
            type="button"
            onClick={() => void load()}
            className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg"
          >
            Filtrar
          </button>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={() => aplicarPreset(1)} className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 hover:bg-slate-50">
              1h
            </button>
            <button type="button" onClick={() => aplicarPreset(8)} className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 hover:bg-slate-50">
              8h
            </button>
            <button type="button" onClick={() => aplicarPreset(24)} className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 hover:bg-slate-50">
              24h
            </button>
            <button type="button" onClick={() => aplicarPreset(24 * 7)} className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 hover:bg-slate-50">
              7 dias
            </button>
          </div>
        </div>
        {kpis.periodo_inicio && kpis.periodo_fim && (
          <p className="text-xs text-slate-400">
            Filtrado de {new Date(kpis.periodo_inicio).toLocaleString('pt-BR')} até{' '}
            {new Date(kpis.periodo_fim).toLocaleString('pt-BR')}
          </p>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          title="Pedidos pendentes"
          value={kpis.pendentes}
          color="text-amber-600"
          subtitle="Fila atual (snapshot)"
        />
        <KpiCard
          title="Separados no período"
          value={kpis.separados_periodo ?? kpis.separados_hoje}
          color="text-emerald-600"
          subtitle="Confirmados no filtro"
        />
        <KpiCard
          title="Consultas no período"
          value={kpis.consultas_24h}
          color="text-blue-600"
          subtitle={`OK: ${kpis.consultas_ok_24h ?? 0} · Erro: ${kpis.consultas_erro_24h ?? 0} · Sucesso: ${kpis.taxa_sucesso_percent}%`}
        />
        <KpiCard
          title="Tempo médio"
          value={`${kpis.tempo_medio_resposta_ms} ms`}
          color="text-violet-600"
          subtitle="Resposta do sorter no período"
        />
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-700 mb-4">
          Pedidos por status (situação atual)
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
