import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { mapeamentoApi } from '../api/client'
import type { Mapeamento, Rota, Saida, Mapa } from '../types'
import { useAuth } from '../context/AuthContext'

export default function MapeamentoPage() {
  const { isGestor, isAdmin } = useAuth()

  const [mapas, setMapas] = useState<Mapa[]>([])
  const [mapaId, setMapaId] = useState<number | null>(null)
  const [mapeamentos, setMapeamentos] = useState<Mapeamento[]>([])
  const [rotas, setRotas] = useState<Rota[]>([])
  const [saidas, setSaidas] = useState<Saida[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingMapa, setLoadingMapa] = useState(false)
  const [msg, setMsg] = useState('')
  const [form, setForm] = useState({ valor: '', saida_numero: 1 })
  const [novaRota, setNovaRota] = useState({ codigo: '', descricao: '' })
  const [novoMapa, setNovoMapa] = useState({
    nome: '',
    descricao: '',
    quantidade_saidas: 8,
    criterio_roteamento: 'sigla' as 'sigla' | 'uf' | 'filial',
    habilitado: false,
  })
  const [showNovoMapa, setShowNovoMapa] = useState(false)

  const mapaAtual = mapas.find((m) => m.id === mapaId) ?? null

  const carregarMapas = useCallback(async () => {
    const { data } = await mapeamentoApi.listMapas()
    setMapas(data)
    return data
  }, [])

  const carregarConteudoDoMapa = useCallback(async (id: number) => {
    setLoadingMapa(true)
    setMapeamentos([])
    try {
      const [mResp, rResp, sResp] = await Promise.all([
        mapeamentoApi.list(id),
        mapeamentoApi.rotas(),
        mapeamentoApi.saidas(),
      ])
      setMapeamentos(mResp.data)
      setRotas(rResp.data)
      setSaidas(sResp.data)
      if (rResp.data.length > 0) {
        setForm((prev) => ({
          rota_codigo: rResp.data.some((r) => r.codigo === prev.rota_codigo)
            ? prev.rota_codigo
            : rResp.data[0].codigo,
          saida_numero: 1,
        }))
      }
    } finally {
      setLoadingMapa(false)
    }
  }, [])

  // Carga inicial
  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      try {
        const lista = await carregarMapas()
        if (cancelled) return
        const inicial =
          lista.find((m) => m.habilitado)?.id ?? lista[0]?.id ?? null
        setMapaId(inicial)
      } catch {
        if (!cancelled) setMsg('Erro ao carregar mapas.')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [carregarMapas])

  // Sempre que o mapa selecionado muda, recarrega saídas/mapeamentos
  useEffect(() => {
    if (mapaId == null) return
    let cancelled = false
    ;(async () => {
      try {
        setLoadingMapa(true)
        setMapeamentos([])
        const [mResp, rResp, sResp] = await Promise.all([
          mapeamentoApi.list(mapaId),
          mapeamentoApi.rotas(),
          mapeamentoApi.saidas(),
        ])
        if (cancelled) return
        setMapeamentos(mResp.data)
        setRotas(rResp.data)
        setSaidas(sResp.data)
        setForm((prev) => ({ ...prev, saida_numero: 1 }))
      } catch {
        if (!cancelled) setMsg('Erro ao carregar conteúdo do mapa.')
      } finally {
        if (!cancelled) setLoadingMapa(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [mapaId])

  const selecionarMapa = (id: number) => {
    if (id === mapaId) return
    setMsg('')
    setMapaId(id)
  }

  const handleCriarMapa = async (e: FormEvent) => {
    e.preventDefault()
    try {
      const { data } = await mapeamentoApi.createMapa(novoMapa)
      setMsg(`Mapa "${data.nome}" criado.`)
      setShowNovoMapa(false)
      setNovoMapa({ nome: '', descricao: '', quantidade_saidas: 8, criterio_roteamento: 'sigla', habilitado: false })
      await carregarMapas()
      setMapaId(data.id)
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Erro ao criar mapa.'
      setMsg(String(detail))
    }
  }

  const handleHabilitar = async (id: number) => {
    try {
      await mapeamentoApi.habilitarMapa(id)
      setMsg('Mapa habilitado. O sorter passa a usar este mapa.')
      await carregarMapas()
      // Foca no mapa habilitado e recarrega o visual (useEffect em mapaId)
      if (mapaId !== id) {
        setMapaId(id)
      } else {
        await carregarConteudoDoMapa(id)
      }
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Erro ao habilitar mapa.'
      setMsg(String(detail))
    }
  }

  const handleDesabilitar = async (id: number) => {
    try {
      await mapeamentoApi.desabilitarMapa(id)
      setMsg('Mapa desabilitado (offline).')
      await carregarMapas()
      if (mapaId === id) {
        await carregarConteudoDoMapa(id)
      }
    } catch {
      setMsg('Erro ao desabilitar mapa.')
    }
  }

  const handleExcluirMapa = async (id: number, nome: string) => {
    if (!window.confirm(`Excluir o mapa "${nome}"? Esta ação não pode ser desfeita.`)) {
      return
    }
    try {
      await mapeamentoApi.deleteMapa(id)
      setMsg(`Mapa "${nome}" excluído.`)
      const lista = await carregarMapas()
      if (mapaId === id) {
        const proximo =
          lista.find((m) => m.habilitado)?.id ?? lista[0]?.id ?? null
        setMapaId(proximo)
        if (proximo == null) {
          setMapeamentos([])
        }
      }
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Erro ao excluir mapa.'
      setMsg(String(detail))
    }
  }

  const handleMapear = async (e: FormEvent) => {
    e.preventDefault()
    if (mapaId == null) return
    try {
      await mapeamentoApi.create({
        mapa_id: mapaId,
        valor: form.valor.trim(),
        saida_numero: form.saida_numero,
      })
      setMsg(`${form.valor.trim()} → saída ${form.saida_numero}`)
      setForm((prev) => ({ ...prev, valor: '' }))
      await carregarConteudoDoMapa(mapaId)
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Erro ao mapear.'
      setMsg(String(detail))
    }
  }

  const handleNovaRota = async (e: FormEvent) => {
    e.preventDefault()
    try {
      await mapeamentoApi.createRota({
        codigo: novaRota.codigo.toUpperCase(),
        descricao: novaRota.descricao,
      })
      setMsg(`Rota ${novaRota.codigo.toUpperCase()} criada.`)
      setNovaRota({ codigo: '', descricao: '' })
      if (mapaId != null) await carregarConteudoDoMapa(mapaId)
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Erro ao criar rota.'
      setMsg(String(detail))
    }
  }

  const qtdSaidas = mapaAtual?.quantidade_saidas ?? 0
  const saidasDisponiveis = saidas.filter((s) => s.numero <= qtdSaidas && s.ativo)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-xl font-bold text-slate-800">Mapas e roteamento</h1>
        {isGestor && (
          <button
            type="button"
            onClick={() => setShowNovoMapa(!showNovoMapa)}
            className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg"
          >
            {showNovoMapa ? 'Cancelar' : '+ Novo mapa'}
          </button>
        )}
      </div>

      {msg && (
        <div className="bg-blue-50 border border-blue-200 text-blue-800 text-sm rounded-lg px-4 py-2">
          {msg}
        </div>
      )}

      {showNovoMapa && isGestor && (
        <form
          onSubmit={handleCriarMapa}
          className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm grid grid-cols-1 sm:grid-cols-2 gap-4"
        >
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Nome *</label>
            <input
              required
              value={novoMapa.nome}
              onChange={(e) => setNovoMapa({ ...novoMapa, nome: e.target.value })}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
              placeholder="Turno manhã / Alto volume"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Quantidade de saídas
            </label>
            <input
              type="number"
              min={1}
              max={100}
              value={novoMapa.quantidade_saidas}
              onChange={(e) =>
                setNovoMapa({ ...novoMapa, quantidade_saidas: Number(e.target.value) })
              }
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Critério de roteamento *
            </label>
            <select
              value={novoMapa.criterio_roteamento}
              onChange={(e) =>
                setNovoMapa({
                  ...novoMapa,
                  criterio_roteamento: e.target.value as 'sigla' | 'uf' | 'filial',
                })
              }
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
            >
              <option value="sigla">Sigla (ex: SAO)</option>
              <option value="uf">UF (ex: SP)</option>
              <option value="filial">Filial (ex: Braz)</option>
            </select>
            <p className="text-xs text-slate-400 mt-1">
              Este mapa usará apenas este campo do pedido para decidir a saída.
            </p>
          </div>
          <div className="sm:col-span-2">
            <label className="block text-sm font-medium text-slate-700 mb-1">Descrição</label>
            <input
              value={novoMapa.descricao}
              onChange={(e) => setNovoMapa({ ...novoMapa, descricao: e.target.value })}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={novoMapa.habilitado}
              onChange={(e) => setNovoMapa({ ...novoMapa, habilitado: e.target.checked })}
            />
            Habilitar este mapa agora (desabilita os demais)
          </label>
          <div>
            <button
              type="submit"
              className="bg-emerald-600 hover:bg-emerald-700 text-white text-sm px-4 py-2 rounded-lg"
            >
              Criar mapa
            </button>
          </div>
        </form>
      )}

      {/* Cards dos mapas */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {mapas.map((m) => (
          <button
            type="button"
            key={m.id}
            onClick={() => selecionarMapa(m.id)}
            className={`text-left bg-white border-2 rounded-xl p-4 transition-colors ${
              mapaId === m.id
                ? 'border-blue-500 shadow-md'
                : 'border-slate-200 hover:border-slate-300'
            }`}
          >
            <div className="flex items-start justify-between gap-2">
              <div>
                <h3 className="font-semibold text-slate-800">{m.nome}</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  {m.quantidade_saidas} saídas · critério:{' '}
                  <span className="uppercase font-medium text-slate-600">
                    {m.criterio_roteamento}
                  </span>
                  {m.descricao ? ` · ${m.descricao}` : ''}
                </p>
              </div>
              <span
                className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                  m.habilitado
                    ? 'bg-emerald-100 text-emerald-800'
                    : 'bg-slate-100 text-slate-500'
                }`}
              >
                {m.habilitado ? 'ONLINE' : 'OFFLINE'}
              </span>
            </div>
            {(isGestor || isAdmin) && (
              <div className="mt-3 flex flex-wrap gap-2">
                {isGestor && (
                  !m.habilitado ? (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation()
                        void handleHabilitar(m.id)
                      }}
                      className="text-xs bg-emerald-600 hover:bg-emerald-700 text-white px-2.5 py-1 rounded"
                    >
                      Habilitar
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation()
                        void handleDesabilitar(m.id)
                      }}
                      className="text-xs bg-slate-500 hover:bg-slate-600 text-white px-2.5 py-1 rounded"
                    >
                      Desabilitar
                    </button>
                  )
                )}
                {isAdmin && !m.habilitado && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      void handleExcluirMapa(m.id, m.nome)
                    }}
                    className="text-xs bg-red-600 hover:bg-red-700 text-white px-2.5 py-1 rounded"
                  >
                    Excluir
                  </button>
                )}
              </div>
            )}
          </button>
        ))}
        {mapas.length === 0 && !loading && (
          <p className="text-sm text-slate-400 col-span-full">
            Nenhum mapa cadastrado. Crie o primeiro mapa.
          </p>
        )}
      </div>

      {mapaAtual && (
        <div className="space-y-6">
          <div className="flex items-center gap-2 text-sm text-slate-600">
            <span>
              Editando: <strong>{mapaAtual.nome}</strong> (id {mapaAtual.id})
            </span>
            {mapaAtual.habilitado ? (
              <span className="text-emerald-600 text-xs font-medium">
                (este mapa direciona o sorter)
              </span>
            ) : (
              <span className="text-amber-600 text-xs font-medium">
                (offline — alterações não afetam o sorter até habilitar)
              </span>
            )}
          </div>

          {/* Mapa visual — recriado a cada troca de mapaId */}
          <div key={`painel-mapa-${mapaId}`}>
            <h2 className="text-sm font-semibold text-slate-700 mb-3">
              Mapa visual das saídas — {mapaAtual.nome}
              <span className="text-slate-400 font-normal ml-2">
                ({loadingMapa ? '...' : `${mapeamentos.length} rota(s)`})
              </span>
            </h2>

            {loadingMapa ? (
              <p className="text-slate-400 text-sm py-6">Carregando saídas do mapa...</p>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
                {Array.from({ length: qtdSaidas }, (_, i) => i + 1).map((num) => {
                  const rotasNaSaida = mapeamentos.filter((mm) => mm.saida_numero === num)
                  const saidaInfo = saidasDisponiveis.find((s) => s.numero === num)
                  return (
                    <div
                      key={`mapa-${mapaId}-saida-${num}`}
                      className="bg-white border-2 border-slate-200 rounded-xl p-4 text-center"
                    >
                      <div className="text-2xl font-bold text-slate-800">{num}</div>
                      <div className="text-xs text-slate-400 mb-2">
                        {saidaInfo?.descricao || `Saída ${num}`}
                      </div>
                      <div className="space-y-1 min-h-[1.5rem]">
                        {rotasNaSaida.length === 0 ? (
                          <span className="text-xs text-slate-300">vazia</span>
                        ) : (
                          rotasNaSaida.map((mm) => (
                            <span
                              key={mm.id}
                              className="inline-block bg-indigo-100 text-indigo-800 text-xs font-semibold px-2 py-0.5 rounded mr-1"
                            >
                              {mm.valor || mm.rota_codigo}
                            </span>
                          ))
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          <form
            onSubmit={handleMapear}
            className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-wrap items-end gap-4"
          >
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Valor ({mapaAtual.criterio_roteamento})
              </label>
              <input
                required
                value={form.valor}
                onChange={(e) => setForm({ ...form, valor: e.target.value })}
                className="border border-slate-300 rounded-lg px-3 py-2 text-sm min-w-[160px]"
                placeholder={
                  mapaAtual.criterio_roteamento === 'sigla'
                    ? 'SAO'
                    : mapaAtual.criterio_roteamento === 'uf'
                      ? 'SP'
                      : 'Braz'
                }
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Saída</label>
              <select
                value={form.saida_numero}
                onChange={(e) => setForm({ ...form, saida_numero: Number(e.target.value) })}
                className="border border-slate-300 rounded-lg px-3 py-2 text-sm"
              >
                {Array.from({ length: qtdSaidas }, (_, i) => i + 1).map((num) => (
                  <option key={num} value={num}>
                    Saída {num}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="submit"
              className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg"
            >
              Mapear valor → saída
            </button>
          </form>

          {isGestor && (
            <form
              onSubmit={handleNovaRota}
              className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-wrap items-end gap-4"
            >
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Código da rota
                </label>
                <input
                  required
                  value={novaRota.codigo}
                  onChange={(e) => setNovaRota({ ...novaRota, codigo: e.target.value })}
                  className="border border-slate-300 rounded-lg px-3 py-2 text-sm uppercase w-28"
                  placeholder="FLN"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Descrição</label>
                <input
                  required
                  value={novaRota.descricao}
                  onChange={(e) => setNovaRota({ ...novaRota, descricao: e.target.value })}
                  className="border border-slate-300 rounded-lg px-3 py-2 text-sm min-w-[200px]"
                  placeholder="Florianópolis"
                />
              </div>
              <button
                type="submit"
                className="bg-emerald-600 hover:bg-emerald-700 text-white text-sm px-4 py-2 rounded-lg"
              >
                Criar rota
              </button>
            </form>
          )}

          <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-slate-600">
                <tr>
                  <th className="px-4 py-3 font-medium">Valor</th>
                  <th className="px-4 py-3 font-medium">Descrição</th>
                  <th className="px-4 py-3 font-medium">Saída</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {mapeamentos.map((m) => (
                  <tr key={m.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-semibold text-indigo-700">{m.valor || m.rota_codigo}</td>
                    <td className="px-4 py-3 text-slate-600">{m.rota_descricao || m.valor}</td>
                    <td className="px-4 py-3">
                      <span className="bg-slate-800 text-white px-2.5 py-0.5 rounded-full text-xs font-bold">
                        {m.saida_numero}
                      </span>
                    </td>
                  </tr>
                ))}
                {mapeamentos.length === 0 && !loadingMapa && (
                  <tr>
                    <td colSpan={3} className="px-4 py-8 text-center text-slate-400">
                      Nenhum mapeamento neste mapa.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
