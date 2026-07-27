<template>
  <EntityListShell
    class="observability-page"
    title="可观测总览"
    description="统一维护日志、链路、指标、看板与告警的关联配置，让诊断入口与跨模块跳转保持同一工作台节奏。"
    eyebrow="Observability Console"
  >
    <template #icon>
      <span class="hero-icon"><el-icon><Share /></el-icon></span>
    </template>
    <template #meta>
      <span v-for="chip in heroChips" :key="chip" class="hero-chip">{{ chip }}</span>
    </template>
    <template #actions>
      <el-button size="small" :loading="loading" @click="loadOverview">
        <el-icon><RefreshRight /></el-icon>
        刷新
      </el-button>
    </template>

    <template #stats>
      <section class="stats-grid observability-summary-grid">
        <button
          v-for="card in capabilityCards"
          :key="card.key"
          type="button"
          class="release-stat-card observability-summary-card"
          :class="card.tone"
          @click="goToEntry(card.to)"
        >
          <div class="stat-card-head">
            <span class="stat-card-label">{{ card.label }}</span>
            <span class="stat-card-badge">{{ card.badge }}</span>
          </div>
          <div class="stat-card-value">{{ card.value }}</div>
          <div class="stat-card-foot">
            <span>{{ card.desc }}</span>
            <span>{{ card.foot }}</span>
          </div>
        </button>
      </section>
    </template>

    <template #hint>
      <section class="panel observability-context-strip">
        <div class="observability-context-copy">
          <span class="observability-context-title">可观测治理上下文</span>
          <span class="observability-context-desc">先确认接入规模、待处理告警与模块权限，再进入日志、链路、指标、看板和关联配置，减少跨页面跳读。</span>
        </div>
        <div class="observability-context-items">
          <span v-for="item in contextItems" :key="item" class="observability-context-item">{{ item }}</span>
        </div>
      </section>
    </template>

    <template #tabs>
      <section class="panel observability-nav-panel">
        <div class="observability-nav-head">
          <span class="observability-nav-title">模块导航</span>
          <span class="observability-nav-desc">从总览直接切换到可观测核心域，保持总览页与各模块同一导航骨架。</span>
        </div>
        <ObservabilityRouteTabs group="overview" />
      </section>
    </template>

    <section class="observability-entry-grid">
      <button
        v-for="entry in moduleEntryCards"
        :key="entry.key"
        type="button"
        class="workbench-card observability-entry-card"
        :class="entry.tone"
        @click="goToEntry(entry.to)"
      >
        <div class="observability-entry-head">
          <span class="observability-entry-icon">
            <el-icon><component :is="entry.icon" /></el-icon>
          </span>
          <div class="observability-entry-title-block">
            <strong>{{ entry.title }}</strong>
            <span>{{ entry.badge }}</span>
          </div>
        </div>
        <p class="observability-entry-desc">{{ entry.desc }}</p>
        <div class="observability-entry-meta">
          <span>{{ entry.meta }}</span>
          <span class="observability-entry-action">
            进入模块
            <el-icon><ArrowRight /></el-icon>
          </span>
        </div>
      </button>
    </section>

    <section v-if="canViewLinks" class="workbench-card observability-link-card">
      <div class="section-toolbar">
        <div class="toolbar-head">
          <span class="toolbar-title">关联配置</span>
          <span class="toolbar-desc">日志、链路和看板之间的跳转关系会作为 AIOps 分析上下文，建议在数据源变更后同步校对。</span>
        </div>
        <div class="workbench-card-actions">
          <el-button size="small" plain @click="goToEntry('/observability/datasource-links')">独立维护</el-button>
        </div>
      </div>
      <div v-if="loading" class="console-skeleton">
        <div class="console-skeleton-card">
          <div class="console-skeleton-toolbar">
            <div class="console-skeleton-cell"></div>
            <div class="console-skeleton-cell"></div>
            <div class="console-skeleton-cell"></div>
          </div>
        </div>
        <div class="console-skeleton-card console-skeleton-table">
          <div v-for="n in 4" :key="`overview-loading-${n}`" class="console-skeleton-row console-skeleton-row--wide">
            <div class="console-skeleton-cell"></div>
            <div class="console-skeleton-cell"></div>
            <div class="console-skeleton-cell"></div>
            <div class="console-skeleton-cell"></div>
            <div class="console-skeleton-cell"></div>
            <div class="console-skeleton-cell"></div>
          </div>
        </div>
      </div>
      <ObservabilityDataSourceLinks v-else embedded />
    </section>

    <section v-else class="panel observability-permission-panel">
      <div class="observability-permission-copy">
        <strong>当前账号未开通关联配置权限</strong>
        <span>仍可从上方入口进入日志、链路、指标、看板和告警模块；如需维护跨模块跳转映射，请补充 `ops.observability.link.view`。</span>
      </div>
    </section>
  </EntityListShell>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowRight,
  Bell,
  Connection,
  DataAnalysis,
  Histogram,
  RefreshRight,
  Search,
  Share,
} from '@element-plus/icons-vue'
import { getObservabilityOverview } from '@/api/modules/ops'
import EntityListShell from '@/components/layout/EntityListShell.vue'
import ObservabilityRouteTabs from '@/components/observability/ObservabilityRouteTabs.vue'
import { useAuthStore } from '@/stores/auth'
import ObservabilityDataSourceLinks from './ObservabilityDataSourceLinks.vue'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const overview = ref({ modules: {}, summary: {} })

const canViewLinks = computed(() => authStore.hasPermission('ops.observability.link.view'))
const canViewMetrics = computed(() => authStore.hasAnyPermission(['ops.metric.query', 'ops.metric.datasource.view']))
const canViewLogs = computed(() => authStore.hasAnyPermission(['ops.log.query', 'ops.log.datasource.view']))
const canViewTracing = computed(() => authStore.hasAnyPermission(['ops.trace.view', 'ops.trace.datasource.view', 'ops.observability.link.view']))
const canViewGrafana = computed(() => authStore.hasPermission('ops.grafana.view'))
const canViewAlerts = computed(() => authStore.hasAnyPermission(['ops.alert.view', 'ops.alert.config.view']))

const modules = computed(() => overview.value.modules || {})

function metricsEntryTarget() {
  if (authStore.hasPermission('ops.metric.query')) return '/observability/metrics'
  return { path: '/observability/metrics', query: { tab: 'datasources' } }
}

function logsEntryTarget() {
  if (authStore.hasPermission('ops.log.query')) return '/logs/query'
  return '/logs/datasources'
}

function tracingEntryTarget() {
  if (authStore.hasPermission('ops.trace.view')) return '/observability/tracing'
  return { path: '/observability/tracing', query: { tab: 'datasources' } }
}

const capabilityCards = computed(() => [
  canViewGrafana.value
    ? {
        key: 'grafana',
        label: '监控看板',
        value: modules.value.grafana?.dashboard_count || 0,
        desc: '承载 Grafana 看板目录与业务视图',
        badge: 'Grafana',
        foot: '进入看板目录',
        tone: '',
        to: '/observability/grafana',
      }
    : null,
  canViewLogs.value
    ? {
        key: 'logs',
        label: authStore.hasPermission('ops.log.query') ? '日志中心' : '日志数据源',
        value: modules.value.logs?.datasource_count || 0,
        desc: '日志检索、回溯与接入配置入口',
        badge: authStore.hasPermission('ops.log.query') ? 'Query' : 'Source',
        foot: authStore.hasPermission('ops.log.query') ? '进入日志中心' : '进入数据源',
        tone: 'audit-card--success',
        to: logsEntryTarget(),
      }
    : null,
  canViewTracing.value
    ? {
        key: 'tracing',
        label: authStore.hasPermission('ops.trace.view') ? '链路追踪' : '链路数据源',
        value: modules.value.tracing?.datasource_count || 0,
        desc: '服务链路、拓扑与链路源治理入口',
        badge: authStore.hasPermission('ops.trace.view') ? 'Trace' : 'Source',
        foot: authStore.hasPermission('ops.trace.view') ? '进入链路工作台' : '进入数据源',
        tone: 'audit-card--warning',
        to: tracingEntryTarget(),
      }
    : null,
  canViewAlerts.value
    ? {
        key: 'alerts',
        label: '待处理告警',
        value: modules.value.alerts?.unacknowledged || 0,
        desc: '待继续排障、认领或确认的告警数',
        badge: 'Alerts',
        foot: '进入告警中心',
        tone: 'audit-card--danger',
        to: '/alerts',
      }
    : null,
]).filter(Boolean)

const moduleEntryCards = computed(() => [
  canViewMetrics.value
    ? {
        key: 'metrics',
        title: authStore.hasPermission('ops.metric.query') ? '指标查询' : '指标数据源',
        badge: authStore.hasPermission('ops.metric.query') ? 'PromQL / 视图分析' : '指标接入治理',
        desc: '统一查看时序指标、切换查询条件，并维护 Prometheus 指标源接入。',
        meta: authStore.hasPermission('ops.metric.query') ? '支持查询与数据源两种工作模式' : '当前进入数据源维护视图',
        icon: DataAnalysis,
        tone: 'is-metrics',
        to: metricsEntryTarget(),
      }
    : null,
  canViewLogs.value
    ? {
        key: 'logs',
        title: authStore.hasPermission('ops.log.query') ? '日志中心' : '日志数据源',
        badge: authStore.hasPermission('ops.log.query') ? 'Loki / 查询回溯' : '日志源配置',
        desc: '处理日志检索、关键字回溯与日志源接入，衔接告警和链路排障上下文。',
        meta: `${modules.value.logs?.datasource_count || 0} 个日志数据源`,
        icon: Search,
        tone: 'is-logs',
        to: logsEntryTarget(),
      }
    : null,
  canViewTracing.value
    ? {
        key: 'tracing',
        title: authStore.hasPermission('ops.trace.view') ? '链路追踪' : '链路数据源',
        badge: authStore.hasPermission('ops.trace.view') ? 'Trace / 拓扑分析' : 'Trace 接入治理',
        desc: '聚焦 Trace 查询、调用拓扑与服务链路，向日志和看板继续串联诊断路径。',
        meta: `${modules.value.tracing?.datasource_count || 0} 个链路数据源`,
        icon: Connection,
        tone: 'is-tracing',
        to: tracingEntryTarget(),
      }
    : null,
  canViewGrafana.value
    ? {
        key: 'grafana',
        title: '仪表盘',
        badge: 'Grafana / 看板目录',
        desc: '统一维护目录树、看板 URL 与标签，为业务视图和外部嵌入提供单一入口。',
        meta: `${modules.value.grafana?.dashboard_count || 0} 个纳管看板`,
        icon: Histogram,
        tone: 'is-grafana',
        to: '/observability/grafana',
      }
    : null,
  canViewAlerts.value
    ? {
        key: 'alerts',
        title: '告警中心',
        badge: '事件处理 / 策略编排',
        desc: '统一处理事件聚合、认领、屏蔽与通知编排，把告警压回到同一运维工作台。',
        meta: `${modules.value.alerts?.unacknowledged || 0} 条未确认告警`,
        icon: Bell,
        tone: 'is-alerts',
        to: '/alerts',
      }
    : null,
  canViewLinks.value
    ? {
        key: 'links',
        title: '关联配置',
        badge: 'Logs ↔ Trace ↔ Grafana',
        desc: '维护日志、链路与看板之间的跳转映射，让 AIOps 与人工排障都能走同一条上下文链。',
        meta: '建议数据源变更后同步复核映射',
        icon: Share,
        tone: 'is-links',
        to: '/observability/datasource-links',
      }
    : null,
]).filter(Boolean)

const heroChips = computed(() => [
  `可访问模块 · ${moduleEntryCards.value.length}`,
  `待处理告警 · ${modules.value.alerts?.unacknowledged || 0}`,
  canViewLinks.value ? '关联配置 · 已启用' : '关联配置 · 未授权',
])

const contextItems = computed(() => [
  canViewGrafana.value ? `看板 ${modules.value.grafana?.dashboard_count || 0} 个` : '看板模块未授权',
  canViewLogs.value ? `日志数据源 ${modules.value.logs?.datasource_count || 0} 个` : '日志模块未授权',
  canViewTracing.value ? `链路数据源 ${modules.value.tracing?.datasource_count || 0} 个` : '链路模块未授权',
  `当前可直达 ${moduleEntryCards.value.length} 个可观测模块`,
])

function goToEntry(to) {
  if (!to) return
  router.push(to)
}

async function loadOverview() {
  loading.value = true
  try {
    overview.value = await getObservabilityOverview()
  } finally {
    loading.value = false
  }
}

onMounted(loadOverview)
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

.observability-summary-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.observability-summary-card {
  width: 100%;
  border: none;
  text-align: left;
  cursor: pointer;
}

.observability-summary-card .stat-card-foot {
  gap: 12px;
}

.observability-context-strip {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.observability-context-copy {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.observability-context-title {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 600;
}

.observability-context-desc {
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
}

.observability-context-items {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.observability-context-item {
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

.observability-nav-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.observability-nav-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.observability-nav-title {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 600;
}

.observability-nav-desc {
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.observability-entry-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.observability-entry-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: #ffffff;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.observability-entry-card:hover {
  border-color: rgba(36, 91, 219, 0.18);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.06);
  transform: translateY(-1px);
}

.observability-entry-card.is-metrics {
  background: linear-gradient(180deg, rgba(54, 124, 255, 0.05), #ffffff 42%);
}

.observability-entry-card.is-logs {
  background: linear-gradient(180deg, rgba(22, 163, 74, 0.06), #ffffff 42%);
}

.observability-entry-card.is-tracing {
  background: linear-gradient(180deg, rgba(245, 158, 11, 0.07), #ffffff 42%);
}

.observability-entry-card.is-grafana {
  background: linear-gradient(180deg, rgba(88, 93, 255, 0.05), #ffffff 42%);
}

.observability-entry-card.is-alerts {
  background: linear-gradient(180deg, rgba(239, 68, 68, 0.06), #ffffff 42%);
}

.observability-entry-card.is-links {
  background: linear-gradient(180deg, rgba(14, 116, 144, 0.06), #ffffff 42%);
}

.observability-entry-head {
  display: flex;
  align-items: center;
  gap: 12px;
}

.observability-entry-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.05);
  color: var(--text-primary);
  font-size: 18px;
}

.observability-entry-title-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.observability-entry-title-block strong {
  color: var(--text-primary);
  font-size: 15px;
  line-height: 1.3;
}

.observability-entry-title-block span {
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.4;
}

.observability-entry-desc {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
  min-height: 42px;
}

.observability-entry-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--text-muted);
  font-size: 12px;
}

.observability-entry-action {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #245bdb;
  font-weight: 500;
  white-space: nowrap;
}

.observability-link-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.observability-permission-panel {
  display: flex;
  align-items: center;
  min-height: 108px;
}

.observability-permission-copy {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.observability-permission-copy strong {
  color: var(--text-primary);
  font-size: 15px;
}

.observability-permission-copy span {
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
}

.observability-link-card :deep(.datasource-link-page) {
  gap: 0;
  padding: 0;
}

.observability-link-card :deep(.datasource-link-page > .hero),
.observability-link-card :deep(.datasource-link-page > .observability-route-tabs) {
  display: none;
}

.observability-link-card :deep(.datasource-link-card) {
  border: none;
  box-shadow: none;
  padding: 0;
  background: transparent;
}

@media (max-width: 1080px) {
  .observability-summary-grid,
  .observability-entry-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .observability-context-strip,
  .observability-nav-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .observability-context-items {
    justify-content: flex-start;
  }
}

@media (max-width: 640px) {
  .observability-summary-grid,
  .observability-entry-grid {
    grid-template-columns: 1fr;
  }

  .observability-entry-meta {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
