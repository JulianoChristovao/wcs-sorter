import axios from 'axios'
import type {
  LoginResponse,
  User,
  PedidoList,
  Pedido,
  Rota,
  Saida,
  Mapeamento,
  ConfigSorter,
  DashboardKpis,
  Mapa,
  LogSorter,
  LogWms,
  LogsPage,
} from '../types'

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('wcs_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('wcs_token')
      localStorage.removeItem('wcs_user')
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export const authApi = {
  login: (username: string, password: string) =>
    api.post<LoginResponse>('/auth/login', { username, password }),
  me: () => api.get<User>('/auth/me'),
}

export const dashboardApi = {
  kpis: (params?: { inicio?: string; fim?: string }) =>
    api.get<DashboardKpis>('/dashboard/kpis', { params }),
}

export const pedidosApi = {
  list: (params?: { status?: string; rota?: string; codigo?: string; page?: number; size?: number }) =>
    api.get<PedidoList>('/pedidos', { params }),
  get: (id: string) => api.get<Pedido>(`/pedidos/${id}`),
  create: (data: {
    codigo_externo?: string
    etiqueta: string
    sigla?: string
    UF?: string
    Filial?: string
    rota_codigo?: string
    prioridade?: number
  }) => api.post<Pedido>('/pedidos', data),
  remove: (id: string, force = false) =>
    api.delete(`/pedidos/${id}`, { params: force ? { force: true } : undefined }),
}

export const mapeamentoApi = {
  listMapas: () => api.get<Mapa[]>('/mapeamento/mapas'),
  createMapa: (data: {
    nome: string
    descricao?: string
    quantidade_saidas: number
    criterio_roteamento: 'sigla' | 'uf' | 'filial'
    habilitado?: boolean
  }) => api.post<Mapa>('/mapeamento/mapas', data),
  updateMapa: (id: number, data: {
    nome?: string
    descricao?: string
    quantidade_saidas?: number
    criterio_roteamento?: 'sigla' | 'uf' | 'filial'
  }) => api.patch<Mapa>(`/mapeamento/mapas/${id}`, data),
  habilitarMapa: (id: number) => api.post<Mapa>(`/mapeamento/mapas/${id}/habilitar`),
  desabilitarMapa: (id: number) => api.post<Mapa>(`/mapeamento/mapas/${id}/desabilitar`),
  deleteMapa: (id: number) => api.delete(`/mapeamento/mapas/${id}`),
  list: (mapaId?: number) =>
    mapaId
      ? api.get<Mapeamento[]>(`/mapeamento/mapas/${mapaId}/mapeamentos`)
      : api.get<Mapeamento[]>('/mapeamento'),
  create: (data: { mapa_id: number; valor: string; saida_numero: number }) =>
    api.post<Mapeamento>('/mapeamento', data),
  remove: (id: number) => api.delete(`/mapeamento/${id}`),
  rotas: () => api.get<Rota[]>('/mapeamento/rotas'),
  saidas: () => api.get<Saida[]>('/mapeamento/saidas'),
  config: () => api.get<ConfigSorter>('/mapeamento/config'),
  updateConfig: (data: { quantidade_saidas: number; descricao?: string }) =>
    api.put<ConfigSorter>('/mapeamento/config', data),
  createRota: (data: { codigo: string; descricao: string }) =>
    api.post<Rota>('/mapeamento/rotas', data),
  deleteRota: (id: number) => api.delete(`/mapeamento/rotas/${id}`),
}

export const usuariosApi = {
  list: () => api.get<User[]>('/usuarios'),
  create: (data: {
    username: string
    email: string
    nome_completo: string
    password: string
    role: string
  }) => api.post<User>('/usuarios', data),
  update: (id: string, data: Partial<{
    email: string
    nome_completo: string
    password: string
    role: string
    ativo: boolean
  }>) => api.patch<User>(`/usuarios/${id}`, data),
}

export default api


export const logsApi = {
  sorter: (params?: { sucesso?: boolean; tipo?: string; codigo?: string; page?: number; size?: number }) =>
    api.get<LogsPage<LogSorter>>('/logs/sorter', { params }),
  wms: (params?: { sucesso?: boolean; tipo?: string; page?: number; size?: number }) =>
    api.get<LogsPage<LogWms>>('/logs/wms', { params }),
}
