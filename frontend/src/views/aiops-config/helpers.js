export const providerCurrencyOptions = [
  { label: '人民币', value: 'CNY' },
  { label: '美元', value: 'USD' },
]

export function formatMcpType(serverType) {
  if (serverType === 'platform_builtin') return '平台内置'
  if (serverType === 'stdio') return 'STDIO'
  return 'HTTP'
}

export function mcpRuntimeMode(row = {}) {
  if (row.server_type === 'platform_builtin') return { label: '平台内置', type: 'success' }
  return row.auth_config?.allow_write ? { label: '可写', type: 'warning' } : { label: '只读', type: 'info' }
}

export function mcpDiagnosticType(status) {
  if (status === 'connected') return 'success'
  if (status === 'failed') return 'danger'
  return 'info'
}

export function mcpDiagnosticLabel(status) {
  if (status === 'connected') return '已连接'
  if (status === 'failed') return '失败'
  return '未知'
}

export function formatMcpToolSchema(row = {}) {
  const properties = row.inputSchema?.properties || {}
  const names = Object.keys(properties)
  if (!names.length) return '无参数'
  return names.slice(0, 6).join('、') + (names.length > 6 ? '…' : '')
}

export function formatSkillSource(row = {}) {
  if (row.is_builtin) return '平台内置'
  if (row.source_type === 'local') return '本地文件'
  return '自定义'
}

export function formatSkillType(row = {}) {
  return formatSkillSource(row)
}

export function getSkillTypeClass(row = {}) {
  if (row.is_builtin) return 'platform_builtin'
  return row.source_type === 'local' ? 'local' : 'custom'
}

export function formatSkillRiskLabel(risk) {
  if (risk === 'read_only') return '只读'
  if (risk === 'draft') return '草稿'
  if (risk === 'write') return '写入'
  if (risk === 'execute') return '执行'
  return risk || '只读'
}

export function skillRiskTagType(risk) {
  if (risk === 'read_only') return 'info'
  if (risk === 'draft') return 'warning'
  if (risk === 'write') return 'warning'
  if (risk === 'execute') return 'danger'
  return 'info'
}

export function skillRecommendedTools(skill = {}) {
  return Array.from(new Set([...(skill.builtin_tools || []), ...(skill.recommended_tools || [])])).filter(Boolean)
}

export function skillRecommendedToolCount(skill = {}) {
  return skillRecommendedTools(skill).length
}

export function actionSkillCount(action = {}) {
  return new Set(action.skills || []).size
}

export function formatEnabledTools(tools) {
  if (!Array.isArray(tools) || !tools.length) return '--'
  return tools.join('、')
}

export function formatActionList(items) {
  if (!Array.isArray(items) || !items.length) return '--'
  return items.join('、')
}

export function formatActionMode(mode) {
  if (mode === 'direct') return 'Direct'
  if (mode === 'react') return 'ReAct'
  if (mode === 'plan_react') return 'Plan+ReAct'
  return mode || '--'
}

export function actionModeTagType(mode) {
  if (mode === 'direct') return 'info'
  if (mode === 'plan_react') return 'warning'
  return 'success'
}

export function actionRiskLabel(risk) {
  if (risk === 'read_only') return '只读'
  if (risk === 'draft') return '草稿'
  if (risk === 'write') return '写入'
  if (risk === 'execute') return '执行'
  return risk || '--'
}

export function actionRiskTagType(risk) {
  if (risk === 'read_only') return 'info'
  if (risk === 'draft') return 'warning'
  if (risk === 'execute') return 'danger'
  return 'warning'
}

export function actionAvailabilityLabel(available) {
  return available === false ? '受限' : '可用'
}

export function actionAvailabilityTagType(available) {
  return available === false ? 'warning' : 'success'
}

export function formatProviderModelLabel(item = {}) {
  const owner = item.owned_by ? ` · ${item.owned_by}` : ''
  return `${item.id}${owner}`
}

export function currencySymbol(currency) {
  return String(currency || '').toUpperCase() === 'CNY' ? '¥' : '$'
}

export function formatProviderCurrency(currency) {
  return String(currency || '').toUpperCase() === 'CNY' ? '人民币' : '美元'
}

export function providerOptionLabel(provider = {}) {
  if (provider.runtime_ready) return provider.name
  return `${provider.name}（${provider.is_enabled ? '待配置' : '停用'}）`
}

export function providerRuntimeTagType(row = {}) {
  if (row.runtime_ready) return 'success'
  return row.is_enabled ? 'warning' : 'info'
}

export function providerRuntimeLabel(row = {}) {
  if (row.runtime_ready) return '可用'
  return row.is_enabled ? '待配置' : '停用'
}

export function providerRuntimeHint(row = {}) {
  if (row.runtime_ready) return '可作为智能助手运行模型'
  return row.setup_hint || (row.is_enabled ? '请补全模型配置后使用' : '当前已停用，启用后可作为运行模型')
}

export function detectProviderPreset(provider = {}, providerPresets = []) {
  if (provider.provider_preset) return provider.provider_preset
  const normalizedBaseUrl = String(provider.base_url || '').replace(/\/+$/, '').toLowerCase()
  const defaultModel = String(provider.default_model || '').toLowerCase()
  const backupModel = String(provider.backup_model || '').toLowerCase()
  const matchedPreset = providerPresets.find((preset) => {
    if (preset.key === 'custom_openai_compatible') return false
    const presetBaseUrl = String(preset.base_url || '').replace(/\/+$/, '').toLowerCase()
    const presetDefaultModel = String(preset.default_model || '').toLowerCase()
    const presetBackupModel = String(preset.backup_model || '').toLowerCase()
    return Boolean(
      (presetBaseUrl && normalizedBaseUrl === presetBaseUrl)
      || (presetDefaultModel && defaultModel === presetDefaultModel)
      || (presetBackupModel && backupModel === presetBackupModel)
    )
  })
  if (matchedPreset) return matchedPreset.key
  const baseUrl = (provider.base_url || '').toLowerCase()
  if (baseUrl.includes('deepseek')) return 'deepseek'
  if (baseUrl.includes('bigmodel') || /^glm-/i.test(provider.default_model || '')) return 'zhipu_glm'
  if (baseUrl.includes('minimax') || /^minimax/i.test(provider.default_model || '')) return 'minimax'
  if (baseUrl.includes('xiaomimimo') || baseUrl.includes('mimo.mi.com')) return 'xiaomi_mimo'
  if (baseUrl.includes('volces.com') || baseUrl.includes('volcengine') || baseUrl.includes('doubao')) return 'volcengine_doubao'
  if (baseUrl.includes('dashscope') || baseUrl.includes('aliyuncs.com') || /^qwen/i.test(provider.default_model || '')) return 'aliyun_qwen'
  if (baseUrl.includes('moonshot') || /^kimi/i.test(provider.default_model || '')) return 'moonshot_kimi'
  if (String(provider.provider_type || '').toLowerCase() === 'openai_compatible') return 'custom_openai_compatible'
  return ''
}

export function normalizeProviderList(data, providerPresets = []) {
  const items = Array.isArray(data) ? data : (Array.isArray(data?.results) ? data.results : [])
  return items.map(item => ({
    ...item,
    provider_preset: detectProviderPreset(item, providerPresets),
  }))
}

export function createProviderForm() {
  return {
    id: null,
    name: '',
    provider_type: 'openai_compatible',
    base_url: '',
    api_key: '',
    default_model: '',
    backup_model: '',
    temperature: 0.2,
    max_tokens: 10000,
    timeout_seconds: 30,
    price_currency: 'CNY',
    input_token_price_per_1m: 0,
    output_token_price_per_1m: 0,
    provider_preset: '',
    is_enabled: true,
  }
}

export function createMcpForm() {
  return {
    id: null,
    name: '',
    server_type: 'http',
    endpoint_or_command: '',
    description: '',
    auth_config: {},
    auth_config_text: '{}',
    tool_whitelist: [],
    is_enabled: true,
  }
}

export function createSkillForm() {
  return {
    id: null,
    name: '',
    slug: '',
    source_type: 'inline',
    description: '',
    category: '',
    applicable_actions: [],
    examples: [],
    builtin_tools: [],
    recommended_tools: [],
    max_iterations: 0,
    risk_level: 'read_only',
    output_contract: {},
    output_contract_text: '{}',
    content: '',
    allowed_role_codes: [],
    is_builtin: false,
    is_enabled: true,
  }
}

export function createA2AForm() {
  return {
    source_agent: 'web-console',
    title: '',
    action_code: 'slo.analysis',
    input_payload_text: '{\n  "environment": "电商测试环境",\n  "service": "order-service"\n}',
  }
}

export function createRunbookForm() {
  return {
    title: '',
    environment: '',
    service: '',
    source_session: '',
    content: '',
    tags: [],
    source_refs_text: '[]',
  }
}
