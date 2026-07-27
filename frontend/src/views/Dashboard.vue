<template>
  <div v-loading="pageLoading" class="dashboard-page workbench-page-shell fade-in">
    <section class="panel dashboard-hero">
      <div class="hero-copy">
        <span class="hero-eyebrow">Operations Console</span>
        <div class="hero-title-row">
          <span class="hero-icon">KP</span>
          <div class="hero-title-block">
            <h2>平台概览</h2>
            <p class="hero-desc">以统一工作台方式汇总资产、发布、告警与 AIOps 运行状态，让高频运维判断先于细节列表出现。</p>
          </div>
        </div>
        <div class="hero-meta">
          <span class="hero-chip">主机在线 {{ formatNumber(hostSummary.online) }}</span>
          <span class="hero-chip">待认领告警 {{ formatNumber(alertSummary.unacknowledged) }}</span>
          <span class="hero-chip">发布执行中 {{ formatNumber(deploymentSummary.running) }}</span>
          <span class="hero-chip">模型调用 {{ formatNumber(modelCostSummary.total_calls) }}</span>
        </div>
      </div>

      <div class="hero-side">
        <span class="hero-side-label">AIOps Snapshot</span>
        <strong>{{ canViewAiopsAudit ? formatModelCostSummary(modelCostSummary) : '未开启审计视角' }}</strong>
        <span>
          {{ canViewAiopsAudit ? `最近窗口共 ${formatNumber(modelCostSummary.total_calls)} 次模型调用，平均耗时 ${formatLatency(modelCostSummary.avg_latency_ms)}。` : '开启智能体审计权限后，可在首页同步观察 MCP、Skill 与模型成本。' }}
        </span>
      </div>
    </section>

    <section class="stats-grid dashboard-top-stats">
      <article v-for="card in resourceCards.slice(0, 4)" :key="card.key" class="release-stat-card" :class="`tone-${card.tone}`">
        <div class="stat-card-head">
          <span class="stat-card-label">{{ card.label }}</span>
          <span class="stat-card-badge">{{ card.badge }}</span>
        </div>
        <div class="stat-card-value">{{ card.value }}</div>
        <div class="stat-card-foot">
          <span>{{ card.caption }}</span>
          <span>{{ card.foot }}</span>
        </div>
      </article>
    </section>

    <section class="panel hint-strip">
      <div class="hint-strip-copy">
        <span class="hint-strip-title">当前优先事项</span>
        <span class="hint-strip-desc">首页先给出最需要处理的事故、发布窗口和异常资产，再把分析型内容下沉到审计面板。</span>
      </div>
      <div class="hint-strip-actions">
        <button
          v-for="item in opsFocusCards"
          :key="item.key"
          type="button"
          class="quick-action"
          @click="goRoute(item.routeName)"
        >
          <span class="quick-action__icon">{{ item.value }}</span>
          <span class="quick-action__text">
            <strong>{{ item.label }}</strong>
            <em>{{ item.desc }}</em>
          </span>
        </button>
      </div>
    </section>

    <section class="panel dashboard-workspace">
      <div class="dashboard-workspace__main">
        <section class="cloud-panel dashboard-section-panel">
          <div class="cloud-panel-head">
            <strong>发布与告警面板</strong>
            <span class="cloud-panel-sub">保持同屏对照，先看变更再看故障</span>
          </div>
          <div class="dashboard-activity-grid">
            <div class="dashboard-activity-panel">
              <div class="dashboard-panel-headline">
                <span>最近发布</span>
                <el-button text @click="goRoute('WorkOrderReleases')">查看全部</el-button>
              </div>
              <div v-if="recentDeployments.length" class="cloud-activity-list">
                <button
                  v-for="item in recentDeployments.slice(0, 5)"
                  :key="item.id"
                  type="button"
                  class="cloud-activity-item"
                  @click="goRoute('WorkOrderReleases')"
                >
                  <div class="cloud-activity-main">
                    <div class="cloud-activity-title">
                      <strong>{{ item.app_name || '未命名应用' }}</strong>
                      <el-tag size="small" :type="deploymentStatusType(item.status)">{{ item.status_display || item.status || '-' }}</el-tag>
                    </div>
                    <div class="cloud-activity-meta">
                      <span>{{ item.environment_display || '-' }}</span>
                      <span>{{ item.deploy_mode_display || '-' }}</span>
                      <span>{{ item.version || '-' }}</span>
                      <span>{{ item.cluster_name || item.host_name || item.docker_host_name || '未设置目标' }}</span>
                    </div>
                  </div>
                  <span class="cloud-activity-time">{{ formatDateTime(item.deployed_at || item.finished_at || item.executed_at) }}</span>
                </button>
              </div>
              <div v-else class="overview-empty">暂无最近发布数据</div>
            </div>

            <div class="dashboard-activity-panel">
              <div class="dashboard-panel-headline">
                <span>告警中心</span>
                <el-button text @click="goRoute('Alerts')">查看全部</el-button>
              </div>
              <div v-if="recentAlerts.length" class="cloud-activity-list">
                <button
                  v-for="item in recentAlerts.slice(0, 5)"
                  :key="item.id"
                  type="button"
                  class="cloud-activity-item"
                  @click="goRoute('Alerts')"
                >
                  <div class="cloud-activity-main">
                    <div class="cloud-activity-title">
                      <strong>{{ item.title || item.summary || '未命名告警' }}</strong>
                      <el-tag size="small" :type="alertLevelType(item.level)">{{ item.level_display || item.level || '-' }}</el-tag>
                    </div>
                    <div class="cloud-activity-meta">
                      <span>{{ item.host_name || item.integration_name || '平台事件' }}</span>
                      <span>{{ item.source_type_display || '告警源' }}</span>
                      <span>{{ item.status_display || item.status || '-' }}</span>
                    </div>
                  </div>
                  <span class="cloud-activity-time">{{ formatDateTime(item.last_received_at || item.created_at) }}</span>
                </button>
              </div>
              <div v-else class="overview-empty">暂无待处理告警</div>
            </div>
          </div>
        </section>

        <section class="cloud-panel dashboard-section-panel">
          <div class="cloud-panel-head">
            <strong>最近活动</strong>
            <span class="cloud-panel-sub">按时间线聚合发布与故障动态</span>
          </div>
          <div v-if="messageFeed.length" class="dashboard-feed-list">
            <button
              v-for="item in messageFeed.slice(0, 8)"
              :key="item.key"
              type="button"
              class="cloud-message-item"
              @click="goRoute(item.routeName)"
            >
              <div class="cloud-message-main">
                <div class="cloud-message-title">
                  <strong>{{ item.title }}</strong>
                  <el-tag size="small" effect="plain" :type="item.tagType">{{ item.tag }}</el-tag>
                </div>
                <div class="cloud-message-meta">
                  <span>{{ item.meta }}</span>
                </div>
              </div>
              <span class="cloud-message-time">{{ item.time }}</span>
            </button>
          </div>
          <div v-else class="overview-empty">暂无消息</div>
        </section>
      </div>

      <aside class="dashboard-workspace__side">
        <section class="cloud-panel dashboard-side-panel">
          <div class="cloud-panel-head">
            <strong>资源使用情况</strong>
            <span class="cloud-panel-sub">主机资源均值</span>
          </div>
          <div class="cloud-usage-list">
            <div v-for="item in hostUsageRows" :key="item.key" class="cloud-usage-row">
              <div class="cloud-usage-head">
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
              </div>
              <div class="cloud-usage-track" :aria-label="item.label">
                <span class="cloud-usage-bar" :style="{ width: `${item.percent}%` }"></span>
              </div>
            </div>
          </div>
        </section>

        <section class="cloud-panel dashboard-side-panel">
          <div class="cloud-panel-head">
            <strong>智能体运行态</strong>
            <span class="cloud-panel-sub">首页摘要</span>
          </div>
          <div class="dashboard-side-kpis">
            <div class="dashboard-side-kpi">
              <span>模型费用</span>
              <strong>{{ formatModelCostSummary(modelCostSummary) }}</strong>
            </div>
            <div class="dashboard-side-kpi">
              <span>MCP 调用</span>
              <strong>{{ formatNumber(overviewInvocationCharts.find(item => item.key === 'mcp')?.total || 0) }}</strong>
            </div>
            <div class="dashboard-side-kpi">
              <span>Skill 命中</span>
              <strong>{{ formatNumber(overviewInvocationCharts.find(item => item.key === 'skills')?.total || 0) }}</strong>
            </div>
          </div>
          <div class="dashboard-side-rank">
            <div v-for="item in modelProviderRows.slice(0, 4)" :key="`${item.provider}-${item.cost_currency || 'USD'}`" class="dashboard-side-rank-row">
              <div class="dashboard-side-rank-head">
                <span>{{ item.provider }}</span>
                <strong>{{ formatNumber(item.calls) }} 次</strong>
              </div>
              <div class="dashboard-side-rank-meta">
                <span>{{ formatTokenCount(item.tokens) }} Token</span>
                <span>{{ formatCost(item.estimated_cost_usd, item.cost_currency) }}</span>
              </div>
              <div class="overview-rank-bar"><span :style="{ width: `${item.percent}%` }"></span></div>
            </div>
            <div v-if="!modelProviderRows.length" class="overview-empty">暂无模型调用数据</div>
          </div>
        </section>
      </aside>
    </section>

    <section v-if="canViewAiopsAudit" class="workbench-card dashboard-audit-card">
      <div class="section-toolbar section-toolbar--audit">
        <div class="toolbar-head">
          <span class="toolbar-title">AI 调用审计</span>
          <span class="toolbar-desc">统一查看调用分布、模型成本与工具命中，支持同屏对照运行态势。</span>
        </div>
        <div class="overview-toolbar">
          <el-date-picker
            v-model="overviewTimeRange"
            class="overview-time-picker"
            size="small"
            type="datetimerange"
            format="YYYY-MM-DD HH:mm"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            :clearable="false"
            :shortcuts="overviewTimeShortcuts"
            @change="handleOverviewRangeChange"
          />
          <div class="overview-toolbar-actions">
            <el-button
              size="small"
              :type="overviewAllTime ? 'primary' : 'default'"
              plain
              class="toolbar-btn"
              @click="selectAllOverviewTime"
            >
              全部时间
            </el-button>
            <el-button
              class="toolbar-btn filter-refresh-btn"
              size="small"
              plain
              :loading="auditLoading"
              @click="loadAuditOverview"
            >
              <el-icon><RefreshRight /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </div>

      <div class="overview-dashboard-grid">
        <div class="overview-invocation-section">
          <div class="invocation-chart-grid">
            <div v-for="chart in overviewInvocationCharts" :key="chart.key" class="invocation-chart-card">
              <div class="invocation-chart-head">
                <strong>{{ chart.title }}</strong>
                <el-tag size="small" effect="plain">{{ formatNumber(chart.total) }} 次</el-tag>
              </div>
              <div v-if="chart.total" class="invocation-usage">
                <div class="invocation-usage-list">
                  <div v-for="item in chart.rows.slice(0, 6)" :key="item.key" class="invocation-usage-row">
                    <div class="invocation-usage-row-head">
                      <span class="invocation-dot" :style="{ background: item.color }"></span>
                      <span class="invocation-usage-label">{{ item.label }}</span>
                      <span class="invocation-usage-meta">{{ formatPercent(item.value, chart.total) }}</span>
                      <strong class="invocation-usage-value">{{ formatNumber(item.value) }}</strong>
                    </div>
                    <div class="invocation-usage-bar">
                      <span
                        :style="{
                          width: `${Math.min(100, chart.total ? (item.value / chart.total) * 100 : 0)}%`,
                          background: item.color,
                        }"
                      ></span>
                    </div>
                  </div>
                </div>
              </div>
              <div v-else class="overview-empty">{{ chart.emptyText }}</div>
            </div>
          </div>
        </div>

        <div class="overview-panel overview-panel--model">
          <div class="overview-panel-head">
            <span class="section-title">模型成本</span>
            <el-button text @click="goRoute('AIOpsAudit')">审计详情</el-button>
          </div>
          <div class="overview-mini-grid">
            <div class="overview-mini-stat">
              <span>模型调用</span>
              <strong>{{ formatNumber(modelCostSummary.total_calls) }}</strong>
            </div>
            <div class="overview-mini-stat">
              <span>Token</span>
              <strong>{{ formatTokenCount(modelCostSummary.total_tokens) }}</strong>
            </div>
            <div class="overview-mini-stat">
              <span>费用</span>
              <strong>{{ formatModelCostSummary(modelCostSummary) }}</strong>
            </div>
            <div class="overview-mini-stat">
              <span>平均耗时</span>
              <strong>{{ formatLatency(modelCostSummary.avg_latency_ms) }}</strong>
            </div>
          </div>
          <div class="overview-rank-list">
            <div v-for="item in modelProviderRows" :key="`${item.provider}-${item.cost_currency || 'USD'}`" class="overview-rank-row">
              <div class="overview-rank-main">
                <div class="overview-rank-title">
                  <span>{{ item.provider }}</span>
                  <strong>{{ formatNumber(item.calls) }} 次</strong>
                </div>
                <div class="overview-rank-meta">
                  <span>{{ formatTokenCount(item.tokens) }} Token</span>
                  <span>{{ formatCost(item.estimated_cost_usd, item.cost_currency) }}</span>
                  <span>平均 {{ formatLatency(item.avg_latency_ms) }}</span>
                </div>
                <div class="overview-rank-bar"><span :style="{ width: `${item.percent}%` }"></span></div>
              </div>
            </div>
            <div v-if="!modelProviderRows.length" class="overview-empty">暂无模型调用数据</div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  RefreshRight,
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { getAIOpsAuditCosts, getAIOpsAuditOverview } from '@/api/modules/aiops'
import { getDashboardStats } from '@/api/modules/ops'

const OVERVIEW_DEFAULT_DAYS = 7

const router = useRouter()
const authStore = useAuthStore()
const pageLoading = ref(false)
const auditLoading = ref(false)
const dashboardStats = ref({})
const auditOverview = ref({})
const auditCosts = ref({})
const overviewAllTime = ref(false)
const overviewRecentDays = ref(OVERVIEW_DEFAULT_DAYS)
const overviewTimeRange = ref(buildRecentTimeRange(OVERVIEW_DEFAULT_DAYS))
const overviewTimeShortcuts = [
  { text: '最近 24 小时', value: () => buildRecentTimeRange(1) },
  { text: '最近 7 天', value: () => buildRecentTimeRange(7) },
  { text: '最近 30 天', value: () => buildRecentTimeRange(30) },
  { text: '最近 90 天', value: () => buildRecentTimeRange(90) },
]

const canViewAiopsAudit = computed(() => authStore.hasPermission('aiops.audit.view'))
const hostSummary = computed(() => dashboardStats.value?.hosts || {})
const deploymentSummary = computed(() => dashboardStats.value?.deployments || {})
const alertSummary = computed(() => dashboardStats.value?.alerts || {})
const recentDeployments = computed(() => Array.isArray(dashboardStats.value?.recent_deploys) ? dashboardStats.value.recent_deploys : [])
const recentAlerts = computed(() => Array.isArray(dashboardStats.value?.recent_alerts) ? dashboardStats.value.recent_alerts : [])

const invocationPiePalettes = {
  mcp: ['#245bdb', '#3b82f6', '#60a5fa', '#93c5fd', '#1d4ed8', '#2563eb', '#38bdf8', '#0ea5e9'],
  skills: ['#16a34a', '#22c55e', '#4ade80', '#86efac', '#15803d', '#059669', '#34d399', '#10b981'],
  actions: ['#f59e0b', '#fbbf24', '#f97316', '#fb923c', '#d97706', '#ea580c', '#facc15', '#eab308'],
}

const modelCostSummary = computed(() => auditCosts.value?.model || {})
const toolCostSummary = computed(() => auditCosts.value?.tools || {})
const messageFeed = computed(() => {
  const rows = []
  recentDeployments.value.slice(0, 10).forEach((item) => {
    rows.push({
      key: `deploy-${item.id}`,
      routeName: 'WorkOrderReleases',
      title: item.app_name || '未命名应用',
      tag: item.status_display || item.status || '-',
      tagType: deploymentStatusType(item.status),
      meta: `${item.environment_display || '-'} · ${item.version || '-'} · ${item.cluster_name || item.host_name || item.docker_host_name || '未设置目标'}`,
      time: formatDateTime(item.deployed_at || item.finished_at || item.executed_at),
      ts: new Date(item.deployed_at || item.finished_at || item.executed_at || item.created_at || 0).getTime() || 0,
    })
  })
  recentAlerts.value.slice(0, 10).forEach((item) => {
    rows.push({
      key: `alert-${item.id}`,
      routeName: 'Alerts',
      title: item.title || item.summary || '未命名告警',
      tag: item.level_display || item.level || '-',
      tagType: alertLevelType(item.level),
      meta: `${item.host_name || item.integration_name || '平台事件'} · ${item.status_display || item.status || '-'}`,
      time: formatDateTime(item.last_received_at || item.created_at),
      ts: new Date(item.last_received_at || item.created_at || 0).getTime() || 0,
    })
  })
  return rows.sort((a, b) => b.ts - a.ts)
})
const summaryCards = computed(() => [
  {
    key: 'hosts-total',
    label: '主机总量',
    value: formatNumber(hostSummary.value.total),
    badge: '资产规模',
    caption: `在线 ${formatNumber(hostSummary.value.online)}`,
    foot: `离线 ${formatNumber(hostSummary.value.offline)}`,
    tone: 'info',
  },
  {
    key: 'hosts',
    label: '在线主机',
    value: formatNumber(hostSummary.value.online),
    badge: `共 ${formatNumber(hostSummary.value.total)}`,
    caption: `离线 ${formatNumber(hostSummary.value.offline)}`,
    foot: `告警 ${formatNumber(hostSummary.value.warning)}`,
    tone: toNumber(hostSummary.value.warning) ? 'warning' : 'info',
  },
  {
    key: 'deploy-total',
    label: '发布总量',
    value: formatNumber(deploymentSummary.value.total),
    badge: '工单链路',
    caption: `成功 ${formatNumber(deploymentSummary.value.success)}`,
    foot: `失败 ${formatNumber(deploymentSummary.value.failed)}`,
    tone: 'info',
  },
  {
    key: 'deploy-running',
    label: '运行中发布',
    value: formatNumber(deploymentSummary.value.running),
    badge: `总数 ${formatNumber(deploymentSummary.value.total)}`,
    caption: `成功 ${formatNumber(deploymentSummary.value.success)}`,
    foot: `失败 ${formatNumber(deploymentSummary.value.failed)}`,
    tone: toNumber(deploymentSummary.value.running) ? 'primary' : 'success',
  },
  {
    key: 'alerts',
    label: '待认领告警',
    value: formatNumber(alertSummary.value.unacknowledged),
    badge: `总数 ${formatNumber(alertSummary.value.total)}`,
    caption: `严重 ${formatNumber(alertSummary.value.critical)}`,
    foot: `预警 ${formatNumber(alertSummary.value.warning)}`,
    tone: toNumber(alertSummary.value.critical) ? 'danger' : 'warning',
  },
  {
    key: 'model-calls',
    label: '模型调用',
    value: formatNumber(modelCostSummary.value.total_calls),
    badge: canViewAiopsAudit.value ? '最近窗口' : '未授权',
    caption: `Token ${formatTokenCount(modelCostSummary.value.total_tokens)}`,
    foot: `均值 ${formatLatency(modelCostSummary.value.avg_latency_ms)}`,
    tone: 'primary',
  },
  {
    key: 'model-cost',
    label: '模型费用',
    value: formatModelCostSummary(modelCostSummary.value),
    badge: '成本视角',
    caption: `MCP ${formatNumber(toolCostSummary.value.total_calls)}`,
    foot: `工具数 ${formatNumber(Array.isArray(toolCostSummary.value.by_tool) ? toolCostSummary.value.by_tool.length : 0)}`,
    tone: 'success',
  },
  {
    key: 'skill-hits',
    label: 'Skill 命中',
    value: formatNumber(overviewInvocationCharts.value.find(item => item.key === 'skills')?.total || 0),
    badge: '智能体调用',
    caption: `Action ${formatNumber(overviewInvocationCharts.value.find(item => item.key === 'actions')?.total || 0)}`,
    foot: `MCP ${formatNumber(overviewInvocationCharts.value.find(item => item.key === 'mcp')?.total || 0)}`,
    tone: 'info',
  },
])
const resourceCards = computed(() => summaryCards.value.slice(0, 8))
const hostUsageRows = computed(() => [
  { key: 'cpu', label: 'CPU 均值', percent: clampPercent(hostSummary.value.avg_cpu), value: formatPercentValue(hostSummary.value.avg_cpu) },
  { key: 'memory', label: '内存均值', percent: clampPercent(hostSummary.value.avg_memory), value: formatPercentValue(hostSummary.value.avg_memory) },
  { key: 'disk', label: '磁盘均值', percent: clampPercent(hostSummary.value.avg_disk), value: formatPercentValue(hostSummary.value.avg_disk) },
])
const opsFocusCards = computed(() => [
  {
    key: 'focus-alerts',
    label: '严重告警',
    value: formatNumber(alertSummary.value.critical),
    desc: '需要先处理高优先级事故',
    tone: toNumber(alertSummary.value.critical) ? 'danger' : 'neutral',
    routeName: 'Alerts',
  },
  {
    key: 'focus-running',
    label: '发布执行中',
    value: formatNumber(deploymentSummary.value.running),
    desc: '持续关注当前发布窗口',
    tone: toNumber(deploymentSummary.value.running) ? 'primary' : 'neutral',
    routeName: 'WorkOrderReleases',
  },
  {
    key: 'focus-hosts',
    label: '异常主机',
    value: formatNumber(hostSummary.value.warning),
    desc: '建议进入资源底座排查',
    tone: toNumber(hostSummary.value.warning) ? 'warning' : 'neutral',
    routeName: 'TaskResources',
  },
])
const modelProviderRows = computed(() => {
  const rows = Array.isArray(modelCostSummary.value.by_provider) ? modelCostSummary.value.by_provider : []
  const maxCalls = Math.max(...rows.map(item => toNumber(item.calls)), 1)
  return rows.slice(0, 6).map(item => ({
    ...item,
    percent: Math.max(6, Math.round((toNumber(item.calls) / maxCalls) * 100)),
  }))
})

const overviewInvocationCharts = computed(() => {
  const distribution = auditOverview.value?.invocation_distribution || {}
  const fallbackMcpItems = Array.isArray(toolCostSummary.value.by_tool)
    ? toolCostSummary.value.by_tool.map(item => ({
      key: item.tool_name || 'unknown',
      label: item.tool_name || '未命名工具',
      count: item.calls,
    }))
    : []
  return [
    buildInvocationPieChart({
      key: 'mcp',
      title: 'MCP 工具调用',
      items: Array.isArray(distribution.mcp_tools) ? distribution.mcp_tools : fallbackMcpItems,
      palette: invocationPiePalettes.mcp,
      emptyText: '暂无 MCP 工具调用',
    }),
    buildInvocationPieChart({
      key: 'skills',
      title: 'Skill 命中',
      items: Array.isArray(distribution.skills) ? distribution.skills : [],
      palette: invocationPiePalettes.skills,
      emptyText: '暂无 Skill 命中记录',
    }),
    buildInvocationPieChart({
      key: 'actions',
      title: 'Action 命中',
      items: Array.isArray(distribution.actions) ? distribution.actions : [],
      palette: invocationPiePalettes.actions,
      emptyText: '暂无 Action 命中记录',
    }),
  ]
})

function toNumber(value) {
  const numberValue = Number(value)
  return Number.isFinite(numberValue) ? numberValue : 0
}

function clampPercent(value) {
  return Math.max(0, Math.min(100, Math.round(toNumber(value))))
}

function formatPercentValue(value) {
  const numberValue = toNumber(value)
  return `${numberValue.toFixed(numberValue % 1 === 0 ? 0 : 1)}%`
}

function normalizeInvocationPieRows(items, palette) {
  const rowMap = new Map()
  ;(Array.isArray(items) ? items : []).forEach((item, index) => {
    const value = toNumber(item?.count ?? item?.value ?? item?.calls)
    if (!value) return
    const label = String(item?.label || item?.name || item?.tool_name || item?.code || item?.key || '未命名').trim()
    const key = String(item?.key || item?.slug || item?.code || item?.tool_name || label || index).trim()
    const current = rowMap.get(key) || { key, label, value: 0 }
    current.value += value
    rowMap.set(key, current)
  })
  return Array.from(rowMap.values())
    .sort((left, right) => right.value - left.value || left.label.localeCompare(right.label, 'zh-CN'))
    .map((item, index) => ({
      ...item,
      color: palette[index % palette.length],
    }))
}

function buildInvocationPieStyle(rows, total) {
  if (!total) return { background: 'conic-gradient(#e2e8f0 0deg 360deg)' }
  let cursor = 0
  const segments = rows.map((item) => {
    const start = cursor
    cursor += (item.value / total) * 360
    return `${item.color} ${start.toFixed(2)}deg ${cursor.toFixed(2)}deg`
  })
  return { background: `conic-gradient(${segments.join(', ')})` }
}

function buildInvocationPieChart({ key, title, items, palette, emptyText }) {
  const rows = normalizeInvocationPieRows(items, palette)
  const total = rows.reduce((sum, item) => sum + item.value, 0)
  return {
    key,
    title,
    rows,
    total,
    emptyText,
    pieStyle: buildInvocationPieStyle(rows, total),
  }
}

function buildRecentTimeRange(days) {
  const end = new Date()
  const start = new Date(end.getTime() - days * 24 * 60 * 60 * 1000)
  return [start, end]
}

function formatDateTimeParam(value) {
  if (!value) return ''
  const date = value instanceof Date ? value : new Date(value)
  return Number.isNaN(date.getTime()) ? '' : date.toISOString()
}

function formatDateTime(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

function buildOverviewCostParams() {
  if (overviewAllTime.value) return { range: 'all' }
  if (overviewRecentDays.value) return { days: overviewRecentDays.value }
  const [start, end] = Array.isArray(overviewTimeRange.value) ? overviewTimeRange.value : []
  const startParam = formatDateTimeParam(start)
  const endParam = formatDateTimeParam(end)
  if (startParam && endParam) return { start: startParam, end: endParam }
  return { days: OVERVIEW_DEFAULT_DAYS }
}

function inferRecentDaysFromRange(range) {
  if (!Array.isArray(range) || range.length !== 2) return null
  const [start, end] = range
  const startDate = start instanceof Date ? start : new Date(start)
  const endDate = end instanceof Date ? end : new Date(end)
  if (Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) return null
  const now = Date.now()
  const endDelta = Math.abs(now - endDate.getTime())
  const diffDays = (endDate.getTime() - startDate.getTime()) / (24 * 60 * 60 * 1000)
  if (endDelta > 10 * 60 * 1000) return null
  return [1, 7, 14, 30, 90].find(days => Math.abs(diffDays - days) < 0.02) || null
}

function formatNumber(value) {
  return toNumber(value).toLocaleString('zh-CN')
}

function formatPercent(value, total) {
  const totalValue = toNumber(total)
  if (!totalValue) return '0%'
  const percent = (toNumber(value) / totalValue) * 100
  return `${percent >= 10 ? Math.round(percent) : percent.toFixed(1)}%`
}

function formatTokenCount(value) {
  const numberValue = Math.round(toNumber(value))
  if (Math.abs(numberValue) < 1000000) return formatNumber(numberValue)
  const millionValue = numberValue / 1000000
  const digits = Math.abs(millionValue) < 10 ? 2 : 1
  return `${millionValue.toFixed(digits).replace(/\.0+$/, '').replace(/(\.\d*?)0+$/, '$1')}M`
}

function normalizeCostCurrency(currency) {
  return String(currency || '').toUpperCase() === 'CNY' ? 'CNY' : 'USD'
}

function currencySymbol(currency) {
  return normalizeCostCurrency(currency) === 'CNY' ? '¥' : '$'
}

function formatCost(value, currency = 'USD') {
  const numberValue = toNumber(value)
  const symbol = currencySymbol(currency)
  if (!numberValue) return `${symbol}0`
  return `${symbol}${numberValue.toFixed(numberValue < 1 ? 4 : 2)}`
}

function formatModelCostSummary(summary = {}) {
  const byCurrency = Array.isArray(summary.by_currency) ? summary.by_currency.filter(item => toNumber(item.estimated_cost_usd)) : []
  if (byCurrency.length > 1) return byCurrency.map(item => formatCost(item.estimated_cost_usd, item.currency)).join(' / ')
  const currency = byCurrency[0]?.currency || summary.cost_currency || 'USD'
  return formatCost(summary.estimated_cost_usd, currency)
}

function formatLatency(value) {
  const numberValue = Math.round(toNumber(value))
  return numberValue ? `${formatNumber(numberValue)} ms` : '-'
}

function deploymentStatusType(status) {
  if (['failed', 'rejected'].includes(status)) return 'danger'
  if (['running', 'pending'].includes(status)) return 'warning'
  if (['stopped', 'removed'].includes(status)) return 'info'
  return 'success'
}

function alertLevelType(level) {
  if (level === 'critical') return 'danger'
  if (level === 'warning') return 'warning'
  return 'info'
}

function goRoute(routeName) {
  if (!routeName) return
  router.push({ name: routeName })
}

async function loadDashboardOverview() {
  const result = await getDashboardStats()
  dashboardStats.value = result || {}
}

async function loadAuditOverview() {
  if (!canViewAiopsAudit.value) return
  auditLoading.value = true
  try {
    const params = buildOverviewCostParams()
    const [overviewData, costData] = await Promise.all([
      getAIOpsAuditOverview(params, { skipErrorMessage: true }),
      getAIOpsAuditCosts(params, { skipErrorMessage: true }),
    ])
    auditOverview.value = overviewData || {}
    auditCosts.value = costData || {}
  } finally {
    auditLoading.value = false
  }
}

async function handleOverviewRangeChange() {
  overviewAllTime.value = false
  overviewRecentDays.value = inferRecentDaysFromRange(overviewTimeRange.value)
  await loadAuditOverview()
}

async function selectAllOverviewTime() {
  overviewAllTime.value = true
  overviewRecentDays.value = null
  overviewTimeRange.value = []
  await loadAuditOverview()
}

async function loadHome() {
  pageLoading.value = true
  try {
    const tasks = [loadDashboardOverview()]
    if (canViewAiopsAudit.value) {
      tasks.push(loadAuditOverview())
    }
    await Promise.allSettled(tasks)
  } finally {
    pageLoading.value = false
  }
}

onMounted(loadHome)
</script>

<style scoped>
.dashboard-page {
  display: flex;
  flex-direction: column;
  gap: 10px;
  --dashboard-accent: var(--primary, #2563eb);
  --dashboard-accent-soft: rgba(0, 82, 217, 0.16);
  --dashboard-border: var(--border-color);
  --dashboard-shadow: var(--card-shadow);
}

.cloud-dashboard-top {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 12px;
  padding: 12px;
}

.cloud-dashboard-main {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}

.cloud-dashboard-side {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}

.cloud-resource-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.cloud-metric-card {
  border: 1px solid var(--dashboard-border);
  border-radius: var(--card-radius, 6px);
  background: var(--card-bg);
  padding: 10px 10px 9px;
  min-width: 0;
}

.cloud-metric-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.cloud-metric-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.22);
  flex: 0 0 auto;
}

.tone-danger .cloud-metric-dot {
  background: rgba(239, 68, 68, 0.85);
}

.tone-warning .cloud-metric-dot {
  background: rgba(245, 158, 11, 0.88);
}

.tone-success .cloud-metric-dot {
  background: rgba(22, 163, 74, 0.82);
}

.tone-primary .cloud-metric-dot,
.tone-info .cloud-metric-dot {
  background: var(--dashboard-accent);
}

.cloud-metric-label {
  color: var(--text-secondary);
  font-size: 12px;
}

.cloud-metric-badge {
  margin-left: auto;
  color: var(--text-muted);
  font-size: 11px;
}

.cloud-metric-value {
  margin-top: 10px;
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--text-primary);
}

.cloud-metric-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 8px;
  color: var(--text-muted);
  font-size: 11px;
}

.cloud-panel {
  border: 1px solid var(--dashboard-border);
  border-radius: var(--card-radius, 6px);
  background: var(--card-bg);
  padding: 12px;
  min-width: 0;
}

.cloud-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.cloud-panel-head strong {
  font-size: 13px;
  color: var(--text-primary);
  font-weight: 700;
}

.cloud-panel-sub {
  color: var(--text-muted);
  font-size: 11px;
  margin-left: auto;
}

.cloud-dashboard-lower {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px;
}

.cloud-activity-list,
.cloud-message-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.cloud-activity-item,
.cloud-message-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  width: 100%;
  padding: 10px 10px;
  border: 1px solid var(--border-color);
  border-radius: 3px;
  background: rgba(0, 0, 0, 0.018);
  cursor: pointer;
  text-align: left;
}

.cloud-activity-item:hover,
.cloud-message-item:hover {
  background: rgba(0, 0, 0, 0.04);
}

.cloud-activity-main,
.cloud-message-main {
  flex: 1 1 auto;
  min-width: 0;
}

.cloud-activity-title,
.cloud-message-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.cloud-activity-title strong,
.cloud-message-title strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  color: var(--text-primary);
  font-weight: 650;
}

.cloud-activity-meta,
.cloud-message-meta {
  margin-top: 6px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: var(--text-muted);
  font-size: 11px;
}

.cloud-activity-time,
.cloud-message-time {
  flex: 0 0 auto;
  color: var(--text-muted);
  font-size: 11px;
  white-space: nowrap;
}

.cloud-usage-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.cloud-usage-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--text-secondary);
  font-size: 12px;
  margin-bottom: 6px;
}

.cloud-usage-head strong {
  color: var(--text-primary);
  font-size: 12px;
}

.cloud-usage-track {
  height: 8px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.cloud-usage-bar {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: var(--dashboard-accent);
}

.dashboard-audit-card {
  padding: 14px 16px;
}

.panel,
.workbench-card {
  background: var(--card-bg);
  border: 1px solid var(--dashboard-border);
  border-radius: var(--card-radius, 6px);
  box-shadow: none;
  padding: 12px 12px;
}

@media (max-width: 1220px) {
  .dashboard-workspace {
    grid-template-columns: 1fr;
  }

  .dashboard-workspace__side {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .dashboard-side-kpis {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .cloud-dashboard-top {
    grid-template-columns: 1fr;
  }

  .cloud-dashboard-side {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .dashboard-top-stats,
  .dashboard-activity-grid,
  .dashboard-workspace__side,
  .dashboard-side-kpis {
    grid-template-columns: 1fr;
  }

  .cloud-resource-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .cloud-dashboard-lower {
    grid-template-columns: 1fr;
  }

  .cloud-dashboard-side {
    grid-template-columns: 1fr;
  }
}

.dashboard-hero {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: 18px;
  position: relative;
  overflow: hidden;
  background: var(--card-bg);
  border-color: var(--dashboard-border);
  box-shadow: var(--card-shadow);
}

.dashboard-hero::before {
  content: '';
  position: absolute;
  inset: 0;
  background: transparent;
  pointer-events: none;
  opacity: 0;
}

.dashboard-hero::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 0;
  background: transparent;
  pointer-events: none;
  opacity: 0;
}

.hero-copy,
.hero-side {
  min-width: 0;
  position: relative;
  z-index: 1;
}

.hero-copy {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.hero-eyebrow {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  min-height: 24px;
  padding: 0 9px;
  border-radius: 999px;
  border: 1px solid var(--dashboard-border);
  background: rgba(0, 0, 0, 0.02);
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.03em;
}

.hero-title-row {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

.hero-title-block {
  min-width: 0;
}

.hero-icon {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--dashboard-accent);
  font-size: 18px;
  background: rgba(37, 99, 235, 0.08);
  border: 1px solid rgba(37, 99, 235, 0.16);
  box-shadow: none;
}

.dashboard-hero h2 {
  margin: 0;
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 650;
  letter-spacing: -0.02em;
}

.hero-desc {
  margin: 6px 0 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
  max-width: 720px;
}

.hero-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.hero-chip {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 0 9px;
  border-radius: 999px;
  border: 1px solid var(--dashboard-border);
  background: rgba(0, 0, 0, 0.02);
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 600;
  box-shadow: none;
}

.hint-strip-actions .quick-action__text em {
  display: none;
}

.hero-side {
  width: 248px;
  flex: 0 0 248px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
  padding: 14px 16px;
  border-radius: 14px;
  background: rgba(0, 0, 0, 0.015);
  border: 1px solid var(--dashboard-border);
  color: var(--text-primary);
  box-shadow: none;
}

.hero-side-label {
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.hero-side strong {
  font-size: 15px;
  line-height: 1.45;
  font-weight: 650;
}

.hero-side span {
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-secondary);
}

.dashboard-top-stats {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.dashboard-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 12px;
  padding: 12px;
}

.dashboard-workspace__main,
.dashboard-workspace__side {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}

.dashboard-section-panel,
.dashboard-side-panel {
  padding: 14px;
}

.dashboard-activity-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.dashboard-activity-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}

.dashboard-panel-headline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.dashboard-panel-headline span {
  font-size: 12px;
  font-weight: 650;
  color: var(--text-primary);
}

.dashboard-feed-list,
.dashboard-side-rank {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dashboard-side-kpis {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.dashboard-side-kpi {
  padding: 10px 10px 9px;
  border: 1px solid var(--dashboard-border);
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.018);
}

.dashboard-side-kpi span {
  display: block;
  font-size: 11px;
  color: var(--text-muted);
}

.dashboard-side-kpi strong {
  display: block;
  margin-top: 8px;
  font-size: 18px;
  line-height: 1.1;
  color: var(--text-primary);
}

.dashboard-side-rank-row {
  padding: 10px;
  border: 1px solid var(--dashboard-border);
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.018);
}

.dashboard-side-rank-head,
.dashboard-side-rank-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.dashboard-side-rank-head {
  font-size: 12px;
  color: var(--text-primary);
  font-weight: 600;
}

.dashboard-side-rank-meta {
  margin-top: 6px;
  margin-bottom: 8px;
  font-size: 11px;
  color: var(--text-muted);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
}

.release-stat-card {
  min-width: 0;
  padding: 12px 12px 11px;
  border-radius: 14px;
  border: 1px solid var(--dashboard-border);
  background: var(--card-bg);
  box-shadow: none;
  position: relative;
  overflow: hidden;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.release-stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 12px;
  right: 12px;
  height: 2px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.06);
}

.release-stat-card:hover {
  border-color: var(--border-color-strong);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.release-stat-card.tone-danger::before {
  background: rgba(239, 68, 68, 0.8);
}

.release-stat-card.tone-warning::before {
  background: rgba(245, 158, 11, 0.85);
}

.release-stat-card.tone-success::before {
  background: rgba(16, 185, 129, 0.8);
}

.release-stat-card.tone-primary::before,
.release-stat-card.tone-info::before {
  background: rgba(37, 99, 235, 0.82);
}

.stat-card-head,
.stat-card-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.stat-card-label,
.stat-card-foot span {
  color: var(--text-secondary);
  font-size: 11px;
}

.stat-card-badge {
  display: inline-flex;
  align-items: center;
  min-height: 20px;
  padding: 0 7px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.03);
  color: var(--text-muted);
  font-size: 10px;
  font-weight: 600;
}

.stat-card-value {
  margin-top: 12px;
  color: var(--text-primary);
  font-size: 24px;
  font-weight: 650;
  letter-spacing: -0.03em;
  line-height: 1.05;
}

.stat-card-foot {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
}

.hint-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-top: 10px;
  padding-bottom: 10px;
  border-style: solid;
  border-width: 1px;
  border-color: var(--dashboard-border);
  background: rgba(255, 255, 255, 0.72);
}

.hint-strip-copy {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.hint-strip-title {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 600;
}

.hint-strip-desc {
  color: var(--text-secondary);
  font-size: 12px;
}

.hint-strip-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.quick-action {
  appearance: none;
  border: 1px solid var(--dashboard-border);
  background: rgba(255, 255, 255, 0.92);
  border-radius: 10px;
  min-height: 34px;
  padding: 6px 10px;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  transition: all 0.18s ease;
}

.quick-action:hover {
  border-color: var(--border-color-strong);
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.quick-action__icon {
  width: 24px;
  height: 24px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--dashboard-accent);
  background: rgba(37, 99, 235, 0.08);
  border: 1px solid rgba(37, 99, 235, 0.14);
}

.quick-action__text {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
}

.quick-action__text strong {
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 600;
}

.quick-action__text em {
  color: var(--text-secondary);
  font-size: 11px;
  font-style: normal;
}

.dashboard-content-card {
  min-height: calc(100vh - 276px);
}

.dashboard-section-stack {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.dashboard-section--audit {
  padding-top: 0;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.section-toolbar--audit {
  margin-bottom: 14px;
}

.dashboard-page :deep(.el-button.is-text) {
  font-weight: 600;
  color: var(--text-secondary);
}

.dashboard-page :deep(.el-button.is-text:hover) {
  color: var(--text-primary);
}

.dashboard-page :deep(.el-tag) {
  border-radius: 999px;
  border-color: var(--dashboard-border);
  color: var(--text-secondary);
  background: rgba(0, 0, 0, 0.02);
  font-weight: 600;
}

.dashboard-page :deep(.el-tag--success) {
  border-color: rgba(16, 185, 129, 0.18);
  color: rgba(16, 185, 129, 0.92);
  background: rgba(16, 185, 129, 0.08);
}

.dashboard-page :deep(.el-tag--danger) {
  border-color: rgba(239, 68, 68, 0.16);
  color: rgba(239, 68, 68, 0.92);
  background: rgba(239, 68, 68, 0.07);
}

.dashboard-page :deep(.el-tag--warning) {
  border-color: rgba(245, 158, 11, 0.16);
  color: rgba(217, 119, 6, 0.92);
  background: rgba(245, 158, 11, 0.08);
}

.dashboard-page :deep(.el-tag--info),
.dashboard-page :deep(.el-tag--primary) {
  border-color: rgba(37, 99, 235, 0.16);
  color: rgba(37, 99, 235, 0.92);
  background: rgba(37, 99, 235, 0.08);
}

.ops-grid {
  display: grid;
  grid-template-columns: 0.92fr 1.08fr;
  gap: 10px;
}

.ops-column {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}

.module-card {
  border-radius: 14px;
  border: 1px solid var(--dashboard-border);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(255, 255, 255, 0.94));
  box-shadow: none;
  padding: 14px;
}

.module-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.module-head h3 {
  margin: 0;
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 600;
}

.module-head p {
  margin: 4px 0 0;
  color: var(--text-secondary);
  font-size: 11px;
  line-height: 1.5;
}

.health-grid,
.focus-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.health-stat,
.focus-card {
  border-radius: 14px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  background: rgba(0, 0, 0, 0.01);
  padding: 10px 10px 9px;
  position: relative;
  overflow: hidden;
}

.health-stat::before,
.focus-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 10px;
  right: 10px;
  height: 1.5px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.06);
}

.health-stat span,
.focus-card span {
  color: var(--text-secondary);
  font-size: 11px;
}

.health-stat strong,
.focus-card strong {
  display: block;
  margin-top: 5px;
  color: var(--text-primary);
  font-size: 20px;
  font-weight: 650;
  line-height: 1.05;
}

.health-stat em,
.focus-card em {
  display: block;
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 11px;
  font-style: normal;
}

.focus-card.tone-danger::before {
  background: rgba(239, 68, 68, 0.78);
}

.focus-card.tone-danger {
  border-color: rgba(239, 68, 68, 0.14);
}

.focus-card.tone-warning::before {
  background: rgba(245, 158, 11, 0.82);
}

.focus-card.tone-warning {
  border-color: rgba(245, 158, 11, 0.14);
}

.focus-card.tone-primary::before {
  background: rgba(37, 99, 235, 0.82);
}

.focus-card.tone-primary {
  border-color: rgba(37, 99, 235, 0.14);
}

.usage-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 10px;
}

.usage-row-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 5px;
}

.usage-row-head span {
  color: var(--text-secondary);
  font-size: 11px;
}

.usage-row-head strong {
  color: var(--text-primary);
  font-size: 11px;
}

.usage-bar {
  overflow: hidden;
  height: 6px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.18);
}

.usage-bar span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, rgba(96, 165, 250, 0.92), var(--dashboard-accent));
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.activity-item {
  width: 100%;
  appearance: none;
  border: 1px solid rgba(0, 0, 0, 0.05);
  background: rgba(0, 0, 0, 0.012);
  border-radius: 10px;
  padding: 9px 10px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  cursor: pointer;
  transition: all 0.18s ease;
  text-align: left;
}

.activity-item:hover {
  border-color: var(--border-color-strong);
  background: rgba(0, 0, 0, 0.02);
}

.activity-main {
  min-width: 0;
  flex: 1 1 auto;
}

.activity-title-row {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  min-width: 0;
}

.activity-title-row strong {
  min-width: 0;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 11px;
  font-weight: 600;
  text-overflow: ellipsis;
  line-height: 1.45;
}

.activity-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 4px;
}

.activity-meta span,
.activity-time {
  color: var(--text-secondary);
  font-size: 10px;
}

.activity-time {
  flex: 0 0 auto;
  min-width: 58px;
  text-align: right;
  padding-top: 1px;
}

.section-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.section-toolbar {
  padding-top: 2px;
}

.section-toolbar--tab {
  margin-bottom: 18px;
}

.toolbar-head {
  display: inline-flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
  min-width: 0;
}

.toolbar-title,
.section-title {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 650;
}

.toolbar-desc {
  color: var(--text-secondary);
  font-size: 11px;
  line-height: 1.4;
}

.overview-time-picker {
  width: 290px;
}

.dashboard-page :deep(.overview-time-picker .el-input__wrapper) {
  min-height: 28px;
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 0 0 1px var(--dashboard-border) inset;
}

.dashboard-page :deep(.overview-time-picker .el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--border-color-strong) inset;
}

.dashboard-page :deep(.overview-time-picker .el-input__wrapper.is-focus) {
  box-shadow:
    0 0 0 1px rgba(37, 99, 235, 0.35) inset,
    0 0 0 4px rgba(37, 99, 235, 0.16);
}

.dashboard-page :deep(.overview-time-picker .el-input__inner) {
  font-size: 12px;
  color: var(--text-primary);
}

.dashboard-page :deep(.overview-time-picker .el-range-separator) {
  color: var(--text-muted);
  font-size: 12px;
}

.dashboard-page :deep(.overview-time-picker .el-icon) {
  color: var(--text-muted);
}

.filter-refresh-btn {
  min-height: 26px;
}

.overview-toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  flex-wrap: wrap;
}

.overview-toolbar-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.toolbar-btn {
  min-height: 28px;
  padding: 0 9px;
  border-radius: 9px;
  font-weight: 600;
}

.dashboard-page :deep(.toolbar-btn.el-button.is-plain) {
  background: rgba(255, 255, 255, 0.92);
  border-color: var(--dashboard-border);
  color: var(--text-primary);
}

.dashboard-page :deep(.toolbar-btn.el-button.is-plain:hover) {
  background: #fff;
  border-color: var(--border-color-strong);
}

.dashboard-page :deep(.toolbar-btn.el-button.is-plain.is-loading) {
  opacity: 0.9;
}

.dashboard-page :deep(.toolbar-btn.el-button--primary.is-plain) {
  background: rgba(37, 99, 235, 0.08);
  border-color: rgba(37, 99, 235, 0.20);
  color: rgba(37, 99, 235, 0.92);
}

.overview-dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.32fr) minmax(280px, 0.72fr);
  gap: 8px;
  align-items: start;
}

.overview-invocation-section {
  min-width: 0;
}

.invocation-chart-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.invocation-chart-card,
.overview-panel {
  min-width: 0;
  border-radius: 12px;
  border: 1px solid var(--dashboard-border);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(255, 255, 255, 0.94));
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
  padding: 12px 12px;
}

.overview-panel--model {
  min-width: 0;
}

.invocation-chart-head,
.overview-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 7px;
  padding-bottom: 7px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.invocation-chart-head strong {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 650;
}

.invocation-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.03);
}

.invocation-usage {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.invocation-usage-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.invocation-usage-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 7px 8px;
  border-radius: 10px;
  border: 1px solid rgba(0, 0, 0, 0.05);
  background: rgba(0, 0, 0, 0.012);
}

.invocation-usage-row-head {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 6px;
}

.invocation-usage-label {
  min-width: 0;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 11px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.invocation-usage-meta {
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 600;
}

.invocation-usage-value {
  color: var(--text-primary);
  font-size: 11px;
  font-weight: 650;
}

.invocation-usage-bar {
  height: 4px;
  border-radius: 999px;
  overflow: hidden;
  background: rgba(0, 0, 0, 0.06);
}

.invocation-usage-bar span {
  display: block;
  height: 100%;
  border-radius: inherit;
  opacity: 0.92;
}

.overview-mini-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
}

.overview-mini-stat {
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  background: var(--card-bg);
  padding: 9px 10px;
}

.overview-mini-stat span {
  display: block;
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 600;
  margin-bottom: 6px;
}

.overview-mini-stat strong {
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 650;
}

.overview-rank-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-top: 7px;
}

.overview-rank-row {
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  background: var(--card-bg);
  padding: 8px 9px;
}

.overview-rank-title,
.overview-rank-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.overview-rank-title span {
  min-width: 0;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.overview-rank-title strong {
  color: var(--text-primary);
  flex: 0 0 auto;
  font-size: 12px;
}

.overview-rank-meta {
  justify-content: flex-start;
  flex-wrap: wrap;
  color: var(--text-secondary);
  font-size: 11px;
  margin-top: 4px;
}

.overview-rank-bar {
  overflow: hidden;
  height: 4px;
  margin-top: 6px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.06);
}

.overview-rank-bar span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: rgba(37, 99, 235, 0.92);
}

.overview-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 80px;
  color: var(--text-muted);
  font-size: 12px;
}

@media (max-width: 1240px) {
  .overview-dashboard-grid {
    grid-template-columns: 1fr;
  }

  .invocation-chart-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 980px) {
  .dashboard-hero,
  .hint-strip,
  .ops-grid {
    grid-template-columns: 1fr;
    flex-direction: column;
  }

  .hero-side {
    width: 100%;
    flex-basis: auto;
  }

  .stats-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .overview-dashboard-grid {
    grid-template-columns: 1fr;
  }

  .invocation-chart-grid {
    grid-template-columns: 1fr;
  }

  .overview-mini-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .stats-grid,
  .health-grid,
  .focus-grid,
  .section-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .stats-grid,
  .health-grid,
  .focus-grid,
  .invocation-chart-grid,
  .overview-mini-grid {
    grid-template-columns: 1fr;
  }

  .activity-item {
    align-items: flex-start;
    flex-direction: column;
  }

  .quick-action {
    width: 100%;
  }

  .overview-time-picker {
    width: 100%;
  }
}
</style>
