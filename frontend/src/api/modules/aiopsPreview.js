const PREVIEW_KNOWLEDGE_ENVS_KEY = 'sxdevops_preview_knowledge_envs_v1'

const PREVIEW_KNOWLEDGE_CATALOG = {
  event_environments: ['交易生产', '交易预发'],
  grafana_folders: [
    { key: 'kp-trade-core', label: '交易核心链路', dashboard_count: 6 },
    { key: 'kp-checkout-runtime', label: '结算运行时', dashboard_count: 4 },
  ],
  metric_datasources: [
    { id: 101, name: 'Prometheus / 交易生产', provider: 'prometheus', provider_display: 'Prometheus' },
  ],
  log_datasources: [
    { id: 201, name: 'Loki / 交易生产', provider: 'loki', provider_display: 'Loki' },
  ],
  tracing_datasources: [
    { id: 301, name: 'Tempo / 交易生产', provider: 'tempo', provider_display: 'Tempo' },
  ],
  observability_links: [
    {
      id: 401,
      name: '交易核心观测链路',
      log_datasource_name: 'Loki / 交易生产',
      tracing_datasource_name: 'Tempo / 交易生产',
      grafana_dashboard_key: 'kp-trade-core',
    },
  ],
  alert_environments: ['交易生产'],
  k8s_clusters: [
    { id: 501, name: 'trade-prod-k8s', api_server: 'https://k8s.trade-prod.local', namespaces: ['gateway', 'checkout', 'infra'] },
  ],
  docker_hosts: [
    { id: 601, name: 'trade-edge-01', ip_address: '10.10.12.21' },
  ],
  task_resource_environments: [
    { id: 701, name: '交易生产资源底座', resource_count: 12 },
  ],
}

const DEFAULT_PREVIEW_ENVIRONMENTS = [
  {
    id: 1,
    name: '交易生产',
    aliases: ['生产', '线上', 'prod'],
    description: '本地预览模式下的交易核心生产环境样例',
    event_environments: ['交易生产'],
    grafana_folder_keys: ['kp-trade-core', 'kp-checkout-runtime'],
    metric_datasource_ids: [101],
    log_datasource_ids: [201],
    tracing_datasource_ids: [301],
    observability_link_ids: [401],
    alert_environments: ['交易生产'],
    k8s_cluster_ids: [501],
    k8s_namespaces: { '501': ['gateway', 'checkout', 'infra'] },
    docker_host_ids: [601],
    task_resource_environment_ids: [701],
    is_default: true,
    is_enabled: true,
  },
  {
    id: 2,
    name: '交易预发',
    aliases: ['staging', 'pre'],
    description: '用于展示筛选器和配置页的第二套样例环境',
    event_environments: ['交易预发'],
    grafana_folder_keys: ['kp-checkout-runtime'],
    metric_datasource_ids: [101],
    log_datasource_ids: [201],
    tracing_datasource_ids: [301],
    observability_link_ids: [401],
    alert_environments: [],
    k8s_cluster_ids: [501],
    k8s_namespaces: { '501': ['checkout'] },
    docker_host_ids: [],
    task_resource_environment_ids: [701],
    is_default: false,
    is_enabled: true,
  },
]

function clone(value) {
  return JSON.parse(JSON.stringify(value))
}

function getStorage() {
  if (typeof window === 'undefined') return null
  return window.localStorage
}

function readPreviewEnvironments() {
  const storage = getStorage()
  if (!storage) return clone(DEFAULT_PREVIEW_ENVIRONMENTS)
  const raw = storage.getItem(PREVIEW_KNOWLEDGE_ENVS_KEY)
  if (!raw) {
    const initial = clone(DEFAULT_PREVIEW_ENVIRONMENTS)
    storage.setItem(PREVIEW_KNOWLEDGE_ENVS_KEY, JSON.stringify(initial))
    return initial
  }
  try {
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) && parsed.length ? parsed : clone(DEFAULT_PREVIEW_ENVIRONMENTS)
  } catch {
    return clone(DEFAULT_PREVIEW_ENVIRONMENTS)
  }
}

function writePreviewEnvironments(items) {
  const storage = getStorage()
  if (!storage) return
  storage.setItem(PREVIEW_KNOWLEDGE_ENVS_KEY, JSON.stringify(items))
}

function nextEnvironmentId(items) {
  return items.reduce((max, item) => Math.max(max, Number(item.id) || 0), 0) + 1
}

function ensureSingleDefault(items, preferredId = null) {
  const nextItems = items.map(item => ({ ...item }))
  const targetId = preferredId ?? nextItems.find(item => item.is_default)?.id ?? nextItems[0]?.id
  nextItems.forEach((item) => {
    item.is_default = Number(item.id) === Number(targetId)
  })
  return nextItems
}

function getPreviewGraphSeed() {
  return {
    nodes: [
      { id: 'environment:交易生产', label: '交易生产', kind: 'environment', category: '环境', metric: 1, environment: '交易生产' },
      { id: 'system:交易生产:电商', label: '电商', kind: 'system', category: '系统', metric: 2, system_name: '电商', business_line: '电商', environment: '交易生产' },
      { id: 'service:交易生产:电商:api-gateway', label: 'api-gateway', kind: 'service', category: '服务', metric: 92, system_name: '电商', business_line: '电商', environment: '交易生产', service: 'api-gateway', route: '/deployments' },
      { id: 'service:交易生产:电商:checkout-service', label: 'checkout-service', kind: 'service', category: '服务', metric: 88, system_name: '电商', business_line: '电商', environment: '交易生产', service: 'checkout-service', route: '/deployments' },
      { id: 'infra:k8s:trade-prod-k8s', label: 'trade-prod-k8s', kind: 'infrastructure', category: 'K8s 集群', metric: 1, infra_type: 'k8s', environment: '交易生产' },
      { id: 'infra:host:trade-edge-01', label: 'trade-edge-01', kind: 'infrastructure', category: '节点主机', metric: 1, infra_type: 'k8s_host', environment: '交易生产' },
      { id: 'runtime:mysql-trade', label: 'mysql-trade', kind: 'runtime_component', category: 'MySQL', metric: 1, runtime_type: 'MySQL', environment: '交易生产' },
      { id: 'runtime:redis-trade', label: 'redis-trade', kind: 'runtime_component', category: 'Redis', metric: 1, runtime_type: 'Redis', environment: '交易生产' },
      { id: 'metric_ds:101', label: 'Prometheus / 交易生产', kind: 'datasource', category: '指标数据源', metric: 1, environment: '交易生产' },
      { id: 'log_ds:201', label: 'Loki / 交易生产', kind: 'datasource', category: '日志数据源', metric: 1, environment: '交易生产' },
      { id: 'trace_ds:301', label: 'Tempo / 交易生产', kind: 'datasource', category: '链路数据源', metric: 1, environment: '交易生产' },
      { id: 'dashboard:kp-trade-core', label: '交易核心链路', kind: 'dashboard', category: '看板', metric: 6, environment: '交易生产' },
      { id: 'alert:trade-core', label: '交易核心告警', kind: 'alert', category: '告警', metric: 3, environment: '交易生产' },
      { id: 'internal_event:trade-release', label: '最近一次发布', kind: 'internal_event', category: '内部事件', metric: 1, environment: '交易生产' },
    ],
    edges: [
      { id: 'e1', source: 'system:交易生产:电商', target: 'service:交易生产:电商:api-gateway', relation: 'system_service', label: '承载服务', weight: 1 },
      { id: 'e2', source: 'system:交易生产:电商', target: 'service:交易生产:电商:checkout-service', relation: 'system_service', label: '承载服务', weight: 1 },
      { id: 'e3', source: 'service:交易生产:电商:api-gateway', target: 'infra:k8s:trade-prod-k8s', relation: 'service_deployment', label: '部署在', weight: 1 },
      { id: 'e4', source: 'service:交易生产:电商:checkout-service', target: 'infra:k8s:trade-prod-k8s', relation: 'service_deployment', label: '部署在', weight: 1 },
      { id: 'e5', source: 'infra:k8s:trade-prod-k8s', target: 'infra:host:trade-edge-01', relation: 'infrastructure_member', label: '包含节点', weight: 1 },
      { id: 'e6', source: 'service:交易生产:电商:checkout-service', target: 'runtime:mysql-trade', relation: 'service_runtime', label: '依赖数据库', weight: 1 },
      { id: 'e7', source: 'service:交易生产:电商:checkout-service', target: 'runtime:redis-trade', relation: 'service_runtime', label: '依赖缓存', weight: 1 },
      { id: 'e8', source: 'system:交易生产:电商', target: 'runtime:redis-trade', relation: 'system_runtime', label: '共享组件', weight: 1 },
    ],
    relation_legend: [
      { key: 'system_service', label: '系统承载服务' },
      { key: 'service_deployment', label: '服务部署位置' },
      { key: 'infrastructure_member', label: '基础设施成员' },
      { key: 'service_runtime', label: '服务依赖组件' },
      { key: 'system_runtime', label: '系统共享组件' },
    ],
  }
}

function matchesFilter(value, expected) {
  return !expected || String(value || '') === String(expected)
}

function buildPreviewKnowledgeGraph(params = {}) {
  const environments = readPreviewEnvironments().filter(item => item.is_enabled !== false)
  const environmentNames = environments.map(item => item.name)
  const defaultEnvironment = environments.find(item => item.is_default)?.name || environmentNames[0] || '交易生产'
  const selectedEnvironment = params.environment || defaultEnvironment
  const selectedSystem = params.system || params.business_line || ''
  const selectedService = params.service || ''
  const seed = getPreviewGraphSeed()

  const nodes = seed.nodes.filter((node) => (
    matchesFilter(node.environment, selectedEnvironment)
    && matchesFilter(node.system_name || node.business_line || '', selectedSystem)
    && matchesFilter(node.service || '', selectedService)
  ) || node.kind === 'datasource' || node.kind === 'dashboard' || node.kind === 'alert' || node.kind === 'internal_event')

  const nodeIds = new Set(nodes.map(node => node.id))
  const edges = seed.edges.filter(edge => nodeIds.has(edge.source) && nodeIds.has(edge.target))
  const systems = [...new Set(seed.nodes.filter(node => node.kind === 'system' && matchesFilter(node.environment, selectedEnvironment)).map(node => node.label))]
  const services = [...new Set(seed.nodes.filter((node) => node.kind === 'service' && matchesFilter(node.environment, selectedEnvironment) && matchesFilter(node.system_name || '', selectedSystem)).map(node => node.label))]

  return {
    summary: {},
    filters: {
      environments: environmentNames,
      default_environment: defaultEnvironment,
      systems,
      services,
    },
    nodes,
    edges,
    relation_legend: clone(seed.relation_legend),
  }
}

export function getPreviewKnowledgeGraph(params = {}) {
  return Promise.resolve(buildPreviewKnowledgeGraph(params))
}

export function getPreviewKnowledgeEnvironments() {
  return Promise.resolve(readPreviewEnvironments())
}

export function getPreviewKnowledgeEnvironmentCatalog() {
  return Promise.resolve(clone(PREVIEW_KNOWLEDGE_CATALOG))
}

export function createPreviewKnowledgeEnvironment(data) {
  const items = readPreviewEnvironments()
  const next = {
    id: nextEnvironmentId(items),
    aliases: [],
    description: '',
    event_environments: [],
    grafana_folder_keys: [],
    metric_datasource_ids: [],
    log_datasource_ids: [],
    tracing_datasource_ids: [],
    observability_link_ids: [],
    alert_environments: [],
    k8s_cluster_ids: [],
    k8s_namespaces: {},
    docker_host_ids: [],
    task_resource_environment_ids: [],
    is_default: false,
    is_enabled: true,
    ...clone(data || {}),
  }
  const nextItems = ensureSingleDefault([...items, next], next.is_default ? next.id : undefined)
  writePreviewEnvironments(nextItems)
  return Promise.resolve(clone(next))
}

export function updatePreviewKnowledgeEnvironment(id, data) {
  const items = readPreviewEnvironments()
  const nextItems = items.map((item) => (
    Number(item.id) === Number(id)
      ? { ...item, ...clone(data || {}) }
      : { ...item }
  ))
  const normalized = ensureSingleDefault(nextItems, data?.is_default ? id : undefined)
  writePreviewEnvironments(normalized)
  const target = normalized.find(item => Number(item.id) === Number(id))
  return Promise.resolve(clone(target))
}

export function deletePreviewKnowledgeEnvironment(id) {
  const items = readPreviewEnvironments().filter(item => Number(item.id) !== Number(id))
  const normalized = ensureSingleDefault(items)
  writePreviewEnvironments(normalized)
  return Promise.resolve({ success: true })
}
