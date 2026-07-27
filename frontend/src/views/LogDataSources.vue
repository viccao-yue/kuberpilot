<template>
  <EntityListShell
    class="log-datasource-page"
    title="日志数据源"
    description="统一管理 Loki、ELK 和阿里云 SLS 的连接配置，查询页可以直接复用已保存的数据源。"
    eyebrow="Logs Governance"
  >
    <template #icon>
      <span class="hero-icon"><el-icon><DataBoard /></el-icon></span>
    </template>
    <template #meta>
      <span v-for="chip in heroChips" :key="chip" class="hero-chip">{{ chip }}</span>
    </template>
    <template #actions>
      <el-button size="small" @click="fetchDataSources" :loading="loading">
        <el-icon><RefreshRight /></el-icon>
        刷新数据源
      </el-button>
    </template>

    <template #stats>
      <section class="stats-grid log-datasource-top-stats">
        <div v-for="card in statCards" :key="card.key" class="release-stat-card" :class="card.tone">
          <div class="stat-card-head">
            <span class="stat-card-label">{{ card.label }}</span>
            <span class="stat-card-badge">{{ card.badge }}</span>
          </div>
          <div class="stat-card-value">{{ card.value }}</div>
          <div class="stat-card-foot">
            <span>{{ card.meta }}</span>
            <span>{{ card.foot }}</span>
          </div>
        </div>
      </section>
    </template>

    <template #hint>
      <section class="panel log-datasource-context-strip">
        <div class="log-datasource-context-copy">
          <span class="log-datasource-context-title">数据源治理提示</span>
          <span class="log-datasource-context-desc">优先维护默认数据源和启用状态；敏感字段编辑时留空可保持原值，避免误覆盖。</span>
        </div>
        <div class="log-datasource-context-items">
          <span v-for="item in contextItems" :key="item" class="log-datasource-context-item">{{ item }}</span>
        </div>
      </section>
    </template>

    <template #tabs>
      <section class="panel log-datasource-nav-panel">
        <div class="log-datasource-nav-head">
          <span class="log-datasource-nav-title">可观测导航</span>
          <span class="log-datasource-nav-desc">切换到指标、链路、关联配置等数据源治理模块。</span>
        </div>
        <ObservabilityRouteTabs group="datasources" />
      </section>
    </template>

    <section class="workbench-card log-datasource-card">
      <div class="section-toolbar">
        <div class="toolbar-head">
          <span class="toolbar-title">数据源清单</span>
          <span class="toolbar-desc">维护日志查询可复用的数据源连接和默认入口。</span>
        </div>
        <div class="workbench-card-actions">
          <el-button v-if="canManageLogDataSources" type="primary" @click="openDialog()">
            <el-icon><Plus /></el-icon>
            新增数据源
          </el-button>
        </div>
      </div>

      <div class="workbench-toolbar workbench-toolbar--history datasource-filter-bar">
        <div class="workbench-toolbar-left">
          <el-input v-model="keyword" size="small" placeholder="搜索名称或描述" clearable style="width: 260px">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-select v-model="providerFilter" size="small" clearable placeholder="全部类型" style="width: 160px">
            <el-option v-for="provider in providers" :key="provider.id" :label="providerLabel(provider.id)" :value="provider.id" />
          </el-select>
          <el-switch v-model="enabledOnly" active-text="仅看启用" inactive-text="全部状态" />
        </div>
        <div class="workbench-toolbar-right">
          <span class="toolbar-count">共 {{ filteredItems.length }} 个数据源</span>
        </div>
      </div>

      <el-table :data="filteredItems" v-loading="loading" stripe size="small" style="width: 100%" class="data-table">
        <el-table-column prop="name" label="名称" min-width="220">
          <template #default="{ row }">
            <div class="name-cell">
              <span class="name-text">{{ row.name }}</span>
              <el-tag v-if="row.is_default" size="small" type="warning">默认</el-tag>
            </div>
            <div class="sub-text">{{ row.description || '未填写描述' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="180">
          <template #default="{ row }">
            <el-tag :type="providerTagType(row.provider)" size="small">{{ providerLabel(row.provider) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="连接摘要" min-width="280">
          <template #default="{ row }">
            <div class="summary-text">{{ formatSummary(row) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.is_enabled ? 'success' : 'info'" size="small">{{ row.is_enabled ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" width="180">
          <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column v-if="canManageLogDataSources" label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button link type="success" size="small" @click="handleTest(row)" :loading="testingId === row.id">测试连接</el-button>
            <el-button link type="primary" size="small" @click="openDialog(row)">编辑</el-button>
            <el-popconfirm title="确定删除该日志数据源吗？" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button link type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑日志数据源' : '新增日志数据源'"
      width="720px"
      top="6vh"
      append-to-body
      destroy-on-close
    >
      <el-form :model="form" label-width="110px">
        <el-form-item label="数据源名称">
          <el-input v-model="form.name" placeholder="例如：生产 ELK" />
        </el-form-item>
        <el-form-item label="日志类型">
          <el-select v-model="form.provider" style="width: 100%" @change="onProviderChange">
            <el-option v-for="provider in providers" :key="provider.id" :label="providerLabel(provider.id)" :value="provider.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="说明该数据源的用途，例如生产业务日志" />
        </el-form-item>
        <div class="switch-row">
          <el-switch v-model="form.is_enabled" active-text="启用" inactive-text="停用" />
          <el-switch v-model="form.is_default" active-text="设为默认" inactive-text="普通数据源" />
        </div>

        <template v-if="form.provider === 'loki'">
          <el-form-item label="Loki 地址">
            <el-input v-model="form.config.endpoint" placeholder="http://localhost:3100" />
          </el-form-item>
        </template>

        <template v-else-if="form.provider === 'elk'">
          <el-form-item label="ES 地址">
            <el-input v-model="form.config.endpoint" placeholder="https://es.example.com:9200" />
          </el-form-item>
          <el-form-item label="认证方式">
            <el-select v-model="form.config.auth_type" style="width: 100%">
              <el-option label="无认证" value="none" />
              <el-option label="Basic Auth" value="basic" />
              <el-option label="API Key" value="api_key" />
              <el-option label="Bearer Token" value="bearer" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="form.config.auth_type === 'basic'" label="用户名">
            <el-input v-model="form.config.username" placeholder="elastic" />
          </el-form-item>
          <el-form-item v-if="form.config.auth_type === 'basic'" label="密码">
            <el-input v-model="form.config.password" show-password :placeholder="secretPlaceholder('password')" />
          </el-form-item>
          <el-form-item v-if="form.config.auth_type === 'api_key'" label="API Key">
            <el-input v-model="form.config.api_key" show-password :placeholder="secretPlaceholder('api_key')" />
          </el-form-item>
          <el-form-item v-if="form.config.auth_type === 'bearer'" label="Bearer Token">
            <el-input v-model="form.config.bearer_token" show-password :placeholder="secretPlaceholder('bearer_token')" />
          </el-form-item>
          <el-form-item label="索引模式">
            <el-input v-model="form.config.index_pattern" placeholder="logs-*" />
          </el-form-item>
          <el-form-item label="时间字段">
            <el-input v-model="form.config.time_field" placeholder="@timestamp" />
          </el-form-item>
          <el-form-item label="消息字段">
            <el-input v-model="form.config.message_fields" placeholder="message,log,msg" />
          </el-form-item>
        </template>

        <template v-else-if="form.provider === 'sls'">
          <el-form-item label="SLS Endpoint">
            <el-input v-model="form.config.endpoint" placeholder="cn-hangzhou.log.aliyuncs.com" />
          </el-form-item>
          <el-form-item label="Project">
            <el-input v-model="form.config.project" placeholder="project-name" />
          </el-form-item>
          <el-form-item label="Logstore">
            <el-input v-model="form.config.logstore" placeholder="app-logstore" />
          </el-form-item>
          <el-form-item label="Topic">
            <el-input v-model="form.config.topic" placeholder="可选" />
          </el-form-item>
          <el-form-item label="AccessKey ID">
            <el-input v-model="form.config.access_key_id" :placeholder="secretPlaceholder('access_key_id')" />
          </el-form-item>
          <el-form-item label="AccessKey Secret">
            <el-input v-model="form.config.access_key_secret" show-password :placeholder="secretPlaceholder('access_key_secret')" />
          </el-form-item>
        </template>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </EntityListShell>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { DataBoard, Plus, RefreshRight, Search } from '@element-plus/icons-vue'
import {
  createLogDataSource,
  deleteLogDataSource,
  getLogDataSources,
  getLogProviders,
  testLogDataSource,
  updateLogDataSource,
} from '@/api/modules/ops'
import { useAuthStore } from '@/stores/auth'
import ObservabilityRouteTabs from '@/components/observability/ObservabilityRouteTabs.vue'
import EntityListShell from '@/components/layout/EntityListShell.vue'

const authStore = useAuthStore()
const loading = ref(false)
const saving = ref(false)
const testingId = ref(null)
const dialogVisible = ref(false)
const editingId = ref(null)
const keyword = ref('')
const providerFilter = ref('')
const enabledOnly = ref(true)
const items = ref([])
const providers = ref([])
const providerDefaults = ref({})
const secretFlags = ref({})
const form = ref(createEmptyForm())

function createEmptyForm(provider = 'loki') {
  return {
    name: '',
    provider,
    description: '',
    is_enabled: true,
    is_default: false,
    config: getProviderDefaults(provider),
  }
}

function getProviderDefaults(provider) {
  const defaults = providerDefaults.value[provider] || {}
  const config = {}
  Object.entries(defaults).forEach(([key, value]) => {
    if (value !== 'configured') config[key] = value
  })
  if (provider === 'elk') {
    config.auth_type = config.auth_type || 'none'
    config.index_pattern = config.index_pattern || 'logs-*'
    config.time_field = config.time_field || '@timestamp'
    config.message_fields = config.message_fields || 'message,log,msg'
  }
  return config
}

const filteredItems = computed(() => {
  return items.value.filter((item) => {
    if (providerFilter.value && item.provider !== providerFilter.value) return false
    if (enabledOnly.value && !item.is_enabled) return false
    if (!keyword.value) return true
    const text = `${item.name} ${item.description || ''}`.toLowerCase()
    return text.includes(keyword.value.toLowerCase())
  })
})
const canManageLogDataSources = computed(() => authStore.hasPermission('ops.log.datasource.manage'))

const enabledCount = computed(() => items.value.filter((item) => item.is_enabled).length)
const defaultCount = computed(() => items.value.filter((item) => item.is_default).length)
const providerCount = computed(() => new Set(items.value.map((item) => item.provider)).size)

const currentProviderLabel = computed(() => {
  if (!providerFilter.value) return '全部类型'
  return providerLabel(providerFilter.value)
})

const heroChips = computed(() => [
  `类型 · ${currentProviderLabel.value}`,
  enabledOnly.value ? '状态 · 仅启用' : '状态 · 全部',
  keyword.value.trim() ? `检索 · ${keyword.value.trim()}` : '检索 · 未启用',
])

const contextItems = computed(() => [
  `总数 ${items.value.length}`,
  `启用 ${enabledCount.value}`,
  `默认 ${defaultCount.value}`,
  `类型 ${providerCount.value}`,
])

const statCards = computed(() => [
  {
    key: 'total',
    label: '数据源总数',
    value: items.value.length,
    badge: 'ALL',
    meta: `当前筛选 ${filteredItems.value.length}`,
    foot: '统一复用入口',
    tone: '',
  },
  {
    key: 'enabled',
    label: '启用中',
    value: enabledCount.value,
    badge: 'ON',
    meta: enabledOnly.value ? '列表锁定启用态' : '可切换仅看启用',
    foot: '影响可见性',
    tone: 'audit-card--success',
  },
  {
    key: 'defaults',
    label: '默认数据源',
    value: defaultCount.value,
    badge: 'DEFAULT',
    meta: '查询页优先复用默认配置',
    foot: '建议保持 1 个',
    tone: 'audit-card--warning',
  },
  {
    key: 'providers',
    label: '类型覆盖',
    value: providerCount.value,
    badge: 'PROVIDERS',
    meta: providers.value.length ? `支持 ${providers.value.length} 种` : '加载中',
    foot: 'Loki / ELK / SLS',
    tone: '',
  },
])

function providerLabel(provider) {
  return {
    loki: 'Loki',
    elk: 'ELK / Elasticsearch',
    sls: '阿里云 SLS',
  }[provider] || provider
}

function providerTagType(provider) {
  return {
    loki: 'success',
    elk: 'warning',
    sls: 'info',
  }[provider] || 'info'
}

function formatSummary(row) {
  const config = row.config || {}
  if (row.provider === 'loki') return config.endpoint || '未配置 Loki 地址'
  if (row.provider === 'elk') {
    return [config.endpoint, config.index_pattern && `索引 ${config.index_pattern}`].filter(Boolean).join(' / ') || '未配置 ELK 连接'
  }
  return [config.project && `项目 ${config.project}`, config.logstore && `日志库 ${config.logstore}`, config.endpoint].filter(Boolean).join(' / ') || '未配置 SLS 连接'
}

function formatTime(value) {
  if (!value) return '--'
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

function secretPlaceholder(key) {
  return secretFlags.value[key] ? '已配置，留空则保持不变' : '请输入敏感信息'
}

async function fetchProviders() {
  const response = await getLogProviders()
  providers.value = response.providers || []
  const defaults = {}
  providers.value.forEach((provider) => {
    defaults[provider.id] = provider.defaults || {}
  })
  providerDefaults.value = defaults
}

async function fetchDataSources() {
  loading.value = true
  try {
    const response = await getLogDataSources()
    items.value = Array.isArray(response) ? response : response.results || []
  } finally {
    loading.value = false
  }
}

function onProviderChange(provider) {
  form.value.config = {
    ...getProviderDefaults(provider),
    ...form.value.config,
  }
  if (provider !== 'elk') {
    delete form.value.config.username
    delete form.value.config.password
    delete form.value.config.api_key
    delete form.value.config.bearer_token
  }
}

function openDialog(row) {
  if (row) {
    editingId.value = row.id
    const config = { ...(row.config || {}) }
    secretFlags.value = {
      password: config.password === 'configured',
      api_key: config.api_key === 'configured',
      bearer_token: config.bearer_token === 'configured',
      access_key_id: config.access_key_id === 'configured',
      access_key_secret: config.access_key_secret === 'configured',
    }
    Object.keys(secretFlags.value).forEach((key) => {
      if (secretFlags.value[key]) config[key] = ''
    })
    form.value = {
      id: row.id,
      name: row.name,
      provider: row.provider,
      description: row.description,
      is_enabled: row.is_enabled,
      is_default: row.is_default,
      config,
    }
  } else {
    editingId.value = null
    secretFlags.value = {}
    form.value = createEmptyForm(providers.value[0]?.id || 'loki')
  }
  dialogVisible.value = true
}

async function handleSave() {
  if (!form.value.name) return ElMessage.warning('请填写数据源名称')
  saving.value = true
  try {
    const payload = {
      name: form.value.name,
      provider: form.value.provider,
      description: form.value.description,
      is_enabled: form.value.is_enabled,
      is_default: form.value.is_default,
      config: form.value.config,
    }
    if (editingId.value) {
      await updateLogDataSource(editingId.value, payload)
      ElMessage.success('日志数据源已更新')
    } else {
      await createLogDataSource(payload)
      ElMessage.success('日志数据源已创建')
    }
    dialogVisible.value = false
    await fetchDataSources()
  } finally {
    saving.value = false
  }
}

async function handleDelete(id) {
  await deleteLogDataSource(id)
  ElMessage.success('日志数据源已删除')
  await fetchDataSources()
}

async function handleTest(row) {
  testingId.value = row.id
  try {
    const response = await testLogDataSource(row.id)
    if (response.success) ElMessage.success(`${response.message}，发现 ${response.preview_count || 0} 条目录项`)
    else ElMessage.error(response.message || '连接测试失败')
  } finally {
    testingId.value = null
  }
}

onMounted(async () => {
  await fetchProviders()
  await fetchDataSources()
})
</script>

<style scoped>
.hero-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 14px;
  background: rgba(51, 112, 255, 0.1);
  color: #245bdb;
  box-shadow: inset 0 0 0 1px rgba(36, 91, 219, 0.08);
}

.hero-chip {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(36, 91, 219, 0.08);
  color: #245bdb;
  font-size: 12px;
  font-weight: 500;
}

.log-datasource-top-stats {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.log-datasource-context-strip {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.log-datasource-context-copy {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.log-datasource-context-title {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 600;
}

.log-datasource-context-desc {
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
}

.log-datasource-context-items {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.log-datasource-context-item {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.04);
  color: var(--text-secondary);
  font-size: 12px;
  white-space: nowrap;
}

.log-datasource-nav-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.log-datasource-nav-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.log-datasource-nav-title {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 600;
}

.log-datasource-nav-desc {
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.log-datasource-card {
  padding: 14px;
}

.datasource-filter-bar {
  margin-bottom: 8px;
}

.toolbar-count {
  color: #64748b;
  font-size: 12px;
}

.name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.name-text {
  font-weight: 700;
}

.sub-text,
.summary-text {
  color: var(--text-secondary);
  font-size: 12px;
  margin-top: 6px;
  word-break: break-word;
}

.switch-row {
  display: flex;
  gap: 24px;
  margin-bottom: 18px;
  padding-left: 110px;
}

@media (max-width: 960px) {
  .log-datasource-top-stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .log-datasource-context-strip,
  .log-datasource-nav-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .log-datasource-context-items {
    justify-content: flex-start;
  }

  .switch-row {
    flex-direction: column;
    gap: 12px;
    padding-left: 0;
  }
}

@media (max-width: 640px) {
  .log-datasource-top-stats {
    grid-template-columns: 1fr;
  }
}
</style>
