<template>
  <EntityListShell :title="activeTabMeta?.label || '主机中心'" :description="heroSubtitle" eyebrow="Ops Assets">
    <template #icon>
      <span class="host-header-icon">
        <el-icon><component :is="activeTabMeta?.icon || Monitor" /></el-icon>
      </span>
    </template>
    <template #meta>
      <span v-for="chip in metaChips" :key="chip" class="hero-chip">{{ chip }}</span>
    </template>
    <template #actions>
      <el-button size="small" :loading="overviewLoading" @click="reloadOverview">刷新</el-button>
    </template>

    <template #stats>
      <div class="stats-grid host-stats">
        <div v-for="card in summaryCards" :key="card.label" class="stat-card release-stat-card" :class="card.tone">
          <div class="stat-value">{{ card.value }}</div>
          <div class="stat-label">{{ card.label }}</div>
          <div class="release-stat-desc">{{ card.desc }}</div>
        </div>
      </div>
    </template>

    <template #hint>
      <section class="workbench-inline-tip--panel host-context-tip">
        <div class="tip-panel-head">
          <strong>主机运维上下文</strong>
          <span>在主机资产与定时任务之间共享同一份资源视图，先锁定当前模块，再进入资产清单或调度中心继续操作。</span>
        </div>
        <div class="tip-panel-list">
          <div class="tip-panel-item">{{ activeTab === 'schedule-center' ? '当前聚焦定时任务中心，适合先确认启用状态和即将到点的编排。' : '当前聚焦主机资产，适合先排查在线状态、归属和待关注主机。' }}</div>
          <div class="tip-panel-item">资源树与主机状态共享同一套环境和系统归属，减少资产与调度口径偏差。</div>
          <div class="tip-panel-item">切换到 {{ activeTab === 'schedule-center' ? '主机资产' : '定时任务' }} 可继续处理关联资源和执行计划。</div>
          <div class="tip-panel-item">概览指标会随当前模块同步变化，便于先在首屏完成筛查再进入详情。</div>
        </div>
      </section>
    </template>

    <template #tabs>
      <div class="neo-tabs theme-blue host-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          type="button"
          class="neo-tab-btn"
          :class="{ active: activeTab === tab.key }"
          @click="switchTab(tab.key)"
        >
          <el-icon><component :is="tab.icon" /></el-icon>
          {{ tab.label }}
        </button>
      </div>
    </template>

    <div class="host-center-content">
      <CmdbHostsPanel v-if="activeTab === 'assets'" :resource-tree="resourceTree" />
      <CmdbHostScheduleCenter v-else-if="activeTab === 'schedule-center'" :resource-tree="resourceTree" />
    </div>
  </EntityListShell>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Monitor, Timer } from '@element-plus/icons-vue'
import EntityListShell from '@/components/layout/EntityListShell.vue'
import CmdbHostsPanel from '@/components/cmdb/CmdbHostsPanel.vue'
import CmdbHostScheduleCenter from '@/components/cmdb/CmdbHostScheduleCenter.vue'
import { useAuthStore } from '@/stores/auth'
import { getHosts, getHostTaskScheduleStats } from '@/api/modules/ops'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const resourceTree = ref([])
const hostSummary = ref({ total: 0, online: 0, offline: 0, warning: 0 })
const scheduleSummary = ref({ total: 0, enabled: 0, due_soon: 0, success_rate: 0 })
const overviewLoading = ref(false)

const canViewAssets = computed(() => authStore.hasAnyPermission(['ops.host.view', 'ops.host.manage', 'ops.host.terminal']))
const canViewSchedules = computed(() => authStore.hasAnyPermission(['ops.host.schedule.view', 'ops.host.schedule.manage', 'ops.host.schedule.execute']))

const tabs = computed(() => [
  canViewAssets.value && { key: 'assets', label: '主机资产', icon: Monitor, path: '/hosts/assets' },
  canViewSchedules.value && { key: 'schedule-center', label: '定时任务', icon: Timer, path: '/hosts/schedules' },
].filter(Boolean))

const routeTabMap = {
  HostsAssets: 'assets',
  HostSchedules: 'schedule-center',
}

const activeTab = computed(() => routeTabMap[route.name] || tabs.value[0]?.key || 'assets')
const activeTabMeta = computed(() => tabs.value.find(item => item.key === activeTab.value))
const heroSubtitle = computed(() => {
  if (activeTab.value === 'schedule-center') return '支持 SSH 与 Ansible 两种执行方式，可按 Cron、间隔或单次触发。'
  return '统一查看主机状态、归属与基础运行信息。'
})

const metaChips = computed(() => {
  if (activeTab.value === 'schedule-center' && canViewSchedules.value) {
    return [
      `编排总数 ${scheduleSummary.value.total}`,
      `已启用 ${scheduleSummary.value.enabled}`,
      `1 小时内到点 ${scheduleSummary.value.due_soon}`,
    ]
  }
  if (canViewAssets.value) {
    return [
      `主机总数 ${hostSummary.value.total}`,
      `在线 ${hostSummary.value.online}`,
      `待关注 ${hostSummary.value.offline + hostSummary.value.warning}`,
    ]
  }
  return []
})

const summaryCards = computed(() => {
  if (activeTab.value === 'schedule-center' && canViewSchedules.value) {
    return [
      { label: '编排总数', value: scheduleSummary.value.total, desc: '定时任务中心当前纳管的自动化编排数量', tone: '' },
      { label: '已启用', value: scheduleSummary.value.enabled, desc: '正在等待调度器触发的编排任务数量', tone: 'success-card' },
      { label: '1 小时内到点', value: scheduleSummary.value.due_soon, desc: '未来 1 小时内即将触发的编排数量', tone: 'warning-card' },
    ]
  }
  if (canViewAssets.value) {
    return [
      { label: '主机总数', value: hostSummary.value.total, desc: '纳入主机中心的资产总量', tone: '' },
      { label: '在线主机', value: hostSummary.value.online, desc: '当前状态为在线的主机数', tone: 'success-card' },
      { label: '待关注', value: hostSummary.value.offline + hostSummary.value.warning, desc: '离线与告警主机需要优先排查', tone: 'warning-card' },
    ]
  }
  return []
})

async function fetchResourceTree() {
  resourceTree.value = []
}

async function fetchHostSummary() {
  if (!canViewAssets.value) return
  try {
    const [totalRes, onlineRes, offlineRes, warningRes] = await Promise.all([
      getHosts({ page: 1 }),
      getHosts({ page: 1, status: 'online' }),
      getHosts({ page: 1, status: 'offline' }),
      getHosts({ page: 1, status: 'warning' }),
    ])
    hostSummary.value = {
      total: totalRes.count || (totalRes.results || totalRes).length,
      online: onlineRes.count || (onlineRes.results || onlineRes).length,
      offline: offlineRes.count || (offlineRes.results || offlineRes).length,
      warning: warningRes.count || (warningRes.results || warningRes).length,
    }
  } catch (error) {}
}

async function fetchScheduleSummary() {
  if (!canViewSchedules.value) return
  try { scheduleSummary.value = await getHostTaskScheduleStats() } catch (error) {}
}

function switchTab(tabKey) {
  const matched = tabs.value.find(item => item.key === tabKey)
  if (matched && matched.path !== route.path) router.push(matched.path)
}

function ensureAccessibleRoute() {
  const currentTab = routeTabMap[route.name]
  if (!tabs.value.length) return router.replace('/403')
  if (!tabs.value.some(item => item.key === currentTab)) router.replace(tabs.value[0].path)
}

watch(tabs, ensureAccessibleRoute, { immediate: true })
watch(() => route.name, () => { reloadOverview() })

async function reloadOverview() {
  overviewLoading.value = true
  try {
    await Promise.all([
      fetchResourceTree(),
      fetchHostSummary(),
      fetchScheduleSummary(),
    ])
  } finally {
    overviewLoading.value = false
  }
}

onMounted(async () => { await reloadOverview() })
</script>

<style scoped>
.host-center-content {
  min-width: 0;
}

.host-tabs :deep(.neo-tab-btn) {
  height: 34px;
}

.hero-chip {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid var(--border-color);
  background: rgba(0, 0, 0, 0.02);
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 600;
}
</style>
