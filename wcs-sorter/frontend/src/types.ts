export type UserRole = 'admin' | 'gestor' | 'operador'

export interface User {
  id: string
  username: string
  email: string
  nome_completo: string
  role: UserRole
  ativo: boolean
  last_login?: string | null
  created_at?: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface Pedido {
  id: string
  codigo_externo?: string | null
  etiqueta: string
  sigla?: string | null
  uf?: string | null
  filial?: string | null
  rota_codigo: string
  status: string
  created_at: string
  processado_em?: string | null
  confirmado_em?: string | null
  altura_cm?: number | null
  largura_cm?: number | null
  comprimento_cm?: number | null
  peso_kg?: number | null
  saida_confirmada?: number | null
}

export interface PedidoList {
  total: number
  page: number
  size: number
  items: Pedido[]
}

export interface Mapa {
  id: number
  nome: string
  descricao?: string | null
  quantidade_saidas: number
  criterio_roteamento: 'sigla' | 'uf' | 'filial'
  habilitado: boolean
  created_at: string
  updated_at: string
}

export interface Rota {
  id: number
  codigo: string
  descricao: string
  ativo: boolean
  created_at: string
}

export interface Saida {
  id: number
  numero: number
  descricao?: string | null
  ativo: boolean
}

export interface Mapeamento {
  id: number
  mapa_id: number
  valor: string
  rota_codigo?: string | null
  rota_descricao?: string | null
  saida_numero: number
  saida_descricao?: string | null
  ativo: boolean
}

export interface ConfigSorter {
  id: number
  quantidade_saidas: number
  descricao?: string | null
  ativo: boolean
  updated_at: string
}

export interface DashboardKpis {
  pendentes: number
  separados_hoje: number
  por_status: Record<string, number>
  consultas_24h: number
  taxa_sucesso_percent: number
  tempo_medio_resposta_ms: number
  atualizado_em: string
}


export interface LogSorter {
  id: string
  tipo: string
  codigo_encontrado?: string | null
  saida_retornada?: number | null
  tempo_ms?: number | null
  sucesso: boolean
  mensagem?: string | null
  payload_entrada?: Record<string, unknown> | null
  payload_saida?: Record<string, unknown> | null
  created_at: string
}

export interface LogWms {
  id: string
  pedido_id?: string | null
  tipo: string
  sucesso?: boolean | null
  mensagem_erro?: string | null
  payload?: Record<string, unknown> | null
  resposta?: Record<string, unknown> | null
  created_at: string
}

export interface LogsPage<T> {
  total: number
  page: number
  size: number
  items: T[]
}
