import { useEffect, useState, Fragment } from 'react'
import { logsApi } from '../api/client'
import type { LogSorter, LogWms } from '../types'
import { useAuth } from '../context/AuthContext'

type Tab = 'sorter' | 'wms'

export default function LogsPage() {
  const { isGestor } = useAuth()
  const [tab, setTab] = useState<Tab>('sorter')
  const [sorterLogs, setSorterLogs] = useState<LogSorter[]>([])
  const [wmsLogs, setWmsLogs] = useState<LogWms[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [onlyErrors, setOnlyErrors] = useState(false)
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [msg, setMsg] = useState('')

  const load = async () => {
    setLoading(true)
    setMsg('')
    try {
      if (tab === 'sorter') {
        const { data } = await logsApi.sorter({
          page,
          size: 30,
          sucesso: onlyErrors ? false : undefined,
        })
        setSorterLogs(data.items)
        setTotal(data.total)
      } else {
        const { data } = await logsApi.wms({
          page,
          size: 30,
          sucesso: onlyErrors ? false : undefined,
        })
        setWmsLogs(data.items)
        setTotal(data.total)
      }
    } catch {
      setMsg('Erro ao carregar logs.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (tab === 'wms' && !isGestor) {
      setTab('sorter')
      return
    }
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, page, onlyErrors, isGestor])

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-xl font-bold text-slate-800">Logs</h1>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={onlyErrors}
              onChange={(e) => {
                setPage(1)
                setOnlyErrors(e.target.checked)
              }}
            />
            Somente erros
          </label>
          <button
            type="button"
            onClick={() => load()}
            className="text-sm bg-slate-700 hover:bg-slate-800 text-white px-3 py-1.5 rounded-lg"
          >
            Atualizar
          </button>
        </div>
      </div>

      <div className="flex gap-2 border-b border-slate-200">
        <button
          type="button"
          onClick={() => {
            setPage(1)
            setTab('sorter')
          }}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
            tab === 'sorter'
              ? 'border-blue-600 text-blue-700'
              : 'border-transparent text-slate-500'
          }`}
        >
          Sorter
        </button>
        {isGestor && (
          <button
            type="button"
            onClick={() => {
              setPage(1)
              setTab('wms')
            }}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
              tab === 'wms'
                ? 'border-blue-600 text-blue-700'
                : 'border-transparent text-slate-500'
            }`}
          >
            Integração WMS
          </button>
        )}
      </div>

      {msg && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-2">
          {msg}
        </div>
      )}

      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        {loading ? (
          <p className="px-4 py-8 text-center text-slate-400 text-sm">Carregando...</p>
        ) : tab === 'sorter' ? (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-slate-600">
              <tr>
                <th className="px-4 py-3 font-medium">Data</th>
                <th className="px-4 py-3 font-medium">Tipo</th>
                <th className="px-4 py-3 font-medium">Código</th>
                <th className="px-4 py-3 font-medium">Saída</th>
                <th className="px-4 py-3 font-medium">ms</th>
                <th className="px-4 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {sorterLogs.map((l) => (
                <Fragment key={l.id}>
                  <tr
                    className="hover:bg-slate-50 cursor-pointer"
                    onClick={() => setExpanded(expanded === l.id ? null : l.id)}
                  >
                    <td className="px-4 py-3 text-slate-500 whitespace-nowrap">
                      {new Date(l.created_at).toLocaleString('pt-BR')}
                    </td>
                    <td className="px-4 py-3">{l.tipo}</td>
                    <td className="px-4 py-3 font-mono">{l.codigo_encontrado || '—'}</td>
                    <td className="px-4 py-3">{l.saida_retornada ?? '—'}</td>
                    <td className="px-4 py-3">{l.tempo_ms ?? '—'}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`text-xs font-semibold px-2 py-0.5 rounded ${
                          l.sucesso
                            ? 'bg-emerald-100 text-emerald-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {l.sucesso ? 'OK' : 'ERRO'}
                      </span>
                    </td>
                  </tr>
                  {expanded === l.id && (
                    <tr key={`${l.id}-d`}>
                      <td colSpan={6} className="px-4 py-3 bg-slate-50 text-xs">
                        {l.mensagem && (
                          <p className="mb-2 text-red-700">{l.mensagem}</p>
                        )}
                        <pre className="overflow-auto max-h-48 text-slate-600">
                          {JSON.stringify(
                            { entrada: l.payload_entrada, saida: l.payload_saida },
                            null,
                            2
                          )}
                        </pre>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
              {sorterLogs.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-400">
                    Nenhum log do sorter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-slate-600">
              <tr>
                <th className="px-4 py-3 font-medium">Data</th>
                <th className="px-4 py-3 font-medium">Tipo</th>
                <th className="px-4 py-3 font-medium">Pedido</th>
                <th className="px-4 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {wmsLogs.map((l) => (
                <Fragment key={l.id}>
                  <tr
                    className="hover:bg-slate-50 cursor-pointer"
                    onClick={() => setExpanded(expanded === l.id ? null : l.id)}
                  >
                    <td className="px-4 py-3 text-slate-500 whitespace-nowrap">
                      {new Date(l.created_at).toLocaleString('pt-BR')}
                    </td>
                    <td className="px-4 py-3">{l.tipo}</td>
                    <td className="px-4 py-3 font-mono text-xs">
                      {l.pedido_id ? l.pedido_id.slice(0, 8) + '…' : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`text-xs font-semibold px-2 py-0.5 rounded ${
                          l.sucesso
                            ? 'bg-emerald-100 text-emerald-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {l.sucesso ? 'OK' : 'ERRO'}
                      </span>
                    </td>
                  </tr>
                  {expanded === l.id && (
                    <tr key={`${l.id}-d`}>
                      <td colSpan={4} className="px-4 py-3 bg-slate-50 text-xs">
                        {l.mensagem_erro && (
                          <p className="mb-2 text-red-700">{l.mensagem_erro}</p>
                        )}
                        <pre className="overflow-auto max-h-48 text-slate-600">
                          {JSON.stringify(
                            { payload: l.payload, resposta: l.resposta },
                            null,
                            2
                          )}
                        </pre>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
              {wmsLogs.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-slate-400">
                    Nenhum log de integração WMS.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {total > 30 && (
        <div className="flex items-center gap-3 text-sm">
          <button
            type="button"
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
            type="button"
            disabled={page * 30 >= total}
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
