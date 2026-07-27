const ENV_LABELS = {
  prod: '生产',
  test: '测试',
  dev: '开发',
  staging: '预发',
  production: '生产',
  testing: '测试',
  development: '开发',
}

const CAPABILITY_LABELS = {
  logs: '日志',
  tracing: '链路',
  dashboards: '看板',
  alerts: '告警',
  internal_events: '内部事件',
  external_events: '外部事件',
}

const NODE_KIND_LABELS = {
  observability: '可观测性',
  logs: '日志',
  tracing: '链路',
  dashboard: '看板',
  alert: '告警',
  internal_event: '内部事件',
  external_event: '外部事件',
  environment: '环境',
  system: '系统',
  service: '服务',
  infrastructure: '基础设施',
  runtime_component: '中间件 / DB',
  datasource: '数据源',
  event_source: '事件源',
}

const EDGE_RELATION_LABELS = {
  system_service: '系统承载服务',
  service_deployment: '部署在',
  infrastructure_member: '集群包含主机',
  service_runtime: '服务依赖',
  system_runtime: '系统依赖组件',
  environment_system: '环境包含系统',
  environment_observability: '环境关联可观测性',
  environment_infrastructure: '环境运行于基础设施',
}

const LANE_TINTS = [
  { fill: 'rgba(59, 130, 246, 0.13)', border: 'rgba(59, 130, 246, 0.28)' },
  { fill: 'rgba(16, 185, 129, 0.13)', border: 'rgba(16, 185, 129, 0.28)' },
  { fill: 'rgba(245, 158, 11, 0.13)', border: 'rgba(245, 158, 11, 0.28)' },
  { fill: 'rgba(236, 72, 153, 0.11)', border: 'rgba(236, 72, 153, 0.26)' },
  { fill: 'rgba(14, 165, 233, 0.13)', border: 'rgba(14, 165, 233, 0.28)' },
]

const LANE_TINT_BY_KIND = {
  service: { fill: 'rgba(245, 158, 11, 0.13)', border: 'rgba(245, 158, 11, 0.28)' },
  observability: { fill: 'rgba(16, 185, 129, 0.08)', border: 'rgba(16, 185, 129, 0.18)' },
  event_source: { fill: 'rgba(16, 185, 129, 0.08)', border: 'rgba(16, 185, 129, 0.18)' },
}

export const hiddenNodeKinds = new Set(['environment', 'external_event'])

export const palette = {
  observability: '#0ea5e9',
  logs: '#0ea5e9',
  tracing: '#8b5cf6',
  dashboard: '#10b981',
  alert: '#ef4444',
  internal_event: '#64748b',
  summary: '#94a3b8',
  environment: '#2563eb',
  system: '#334155',
  service: '#0f766e',
  infrastructure: '#f97316',
  runtime_component: '#0891b2',
  datasource: '#7c3aed',
  event_source: '#db2777',
}

export const laneDefinitions = [
  { kind: 'infrastructure', label: '基础设施' },
  { kind: 'system', label: '系统' },
  { kind: 'service', label: '服务' },
  { kind: 'runtime_component', label: '中间件 / DB' },
  { kind: 'observability', label: '可观测性', kinds: ['datasource', 'dashboard', 'logs', 'tracing'] },
  { kind: 'alert', label: '告警' },
  { kind: 'event_source', label: '事件源' },
  { kind: 'internal_event', label: '内部事件' },
]

export function envLabel(value) {
  return ENV_LABELS[value] || value || '-'
}

export function capabilityLabel(value) {
  return CAPABILITY_LABELS[value] || value
}

export function nodeKindLabel(value) {
  return NODE_KIND_LABELS[value] || value || '-'
}

export function edgeRelationLabel(value) {
  return EDGE_RELATION_LABELS[value] || value || '关联'
}

export function laneKinds(lane) {
  return lane.kinds || [lane.kind]
}

export function datasourceBadgeType(node) {
  const id = String(node.id || '')
  const category = String(node.category || '')
  if (id.startsWith('metric_ds:') || category.includes('指标')) return 'metrics'
  if (id.startsWith('log_ds:') || category.includes('日志')) return 'logs'
  if (id.startsWith('trace_ds:') || category.includes('链路')) return 'tracing'
  return ''
}

export function nodeTypeBadge(node) {
  if (!['datasource', 'dashboard', 'logs', 'tracing', 'infrastructure', 'runtime_component'].includes(node.kind)) return ''
  const category = String(node.category || '')
  if (node.kind === 'infrastructure') {
    if (node.infra_type === 'k8s') return 'K8s'
    if (node.infra_type === 'k8s_host') return '主机'
    if (node.infra_type === 'docker') return 'Docker'
    if (node.infra_type === 'task_resource_host') return '主机'
    if (node.infra_type === 'task_resource_k8s') return 'K8s'
    if (node.infra_type === 'task_resource_environment') return ''
    return '主机'
  }
  if (node.kind === 'runtime_component') return node.runtime_type || '组件'
  if (node.kind === 'dashboard') return '看板'
  if (node.kind === 'logs' || category.includes('日志')) return '日志'
  if (node.kind === 'tracing' || category.includes('链路')) return '链路'
  const datasourceType = datasourceBadgeType(node)
  if (datasourceType === 'metrics') return '指标'
  if (datasourceType === 'logs') return '日志'
  if (datasourceType === 'tracing') return '链路'
  return '数据源'
}

export function laneNodeSortWeight(node) {
  if (node.kind === 'datasource') {
    const datasourceType = datasourceBadgeType(node)
    if (datasourceType === 'metrics') return 10
    if (datasourceType === 'logs') return 20
    if (datasourceType === 'tracing') return 30
    return 40
  }
  if (node.kind === 'dashboard') return 50
  if (node.kind === 'logs') return 70
  if (node.kind === 'tracing') return 80
  if (node.kind !== 'infrastructure') return 100
  if (node.infra_type === 'k8s') return 1
  if (node.infra_type === 'k8s_host') return 2
  if (node.infra_type === 'docker') return 3
  if (node.infra_type === 'task_resource_k8s') return 4
  if (node.infra_type === 'task_resource_host') return 5
  return 9
}

export function getLaneTint(lane) {
  if (LANE_TINT_BY_KIND[lane.kind]) return LANE_TINT_BY_KIND[lane.kind]
  const name = lane.label || lane.kind || ''
  let hash = 0
  for (let index = 0; index < name.length; index += 1) {
    hash = (hash * 31 + name.charCodeAt(index)) >>> 0
  }
  return LANE_TINTS[hash % LANE_TINTS.length]
}
