<template>
  <div class="observability-page workbench-page-shell">
    <section class="hero panel">
      <div class="hero-copy">
        <div class="hero-title-row">
          <span class="hero-icon"><el-icon><Share /></el-icon></span>
          <h2>可观测总览</h2>
          <span class="page-inline-desc">统一维护日志、链路、指标、看板与告警的关联配置。</span>
        </div>
      </div>
      <div class="hero-actions">
        <el-button size="small" :loading="loading" @click="loadOverview">
          <el-icon><RefreshRight /></el-icon>
          刷新
        </el-button>
      </div>
    </section>

    <div class="stats-grid observability-summary-grid">
      <div v-for="card in capabilityCards" :key="card.label" class="stat-card release-stat-card" :class="card.tone">
        <div class="stat-value">{{ card.value }}</div>
        <div class="stat-label">{{ card.label }}</div>
        <div class="release-stat-desc">{{ card.desc }}</div>
      </div>
    </div>

    <section class="workbench-inline-tip--panel observability-context-tip">
      <div class="tip-panel-head">
        <strong>可观测治理上下文</strong>
        <span>先确认日志、链路、看板和告警的接入规模，再进入关联配置维护跨模块跳转，让 AIOps 能沿同一条诊断链路追踪线索。</span>
      </div>
      <div class="tip-panel-list">
        <div class="tip-panel-item">当前纳管看板 {{ capabilityCards[0].value }} 个、日志数据源 {{ capabilityCards[1].value }} 个、链路数据源 {{ capabilityCards[2].value }} 个。</div>
        <div class="tip-panel-item">未确认告警 {{ capabilityCards[3].value }} 条，适合优先校对告警与日志、链路的跳转关联。</div>
        <div class="tip-panel-item">关联配置会作为智能体排障上下文，建议在变更数据源后同步维护映射关系。</div>
        <div class="tip-panel-item">完成首屏巡检后，再进入下方关联配置处理日志、链路与仪表盘跳转。</div>
      </div>
    </section>

    <section v-if="canViewLinks" class="workbench-card">
      <div class="section-toolbar">
        <div class="toolbar-head">
          <span class="toolbar-title">关联配置</span>
          <span class="toolbar-desc">日志、链路和看板之间的跳转关系会作为 AIOps 分析上下文。</span>
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
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { RefreshRight, Share } from '@element-plus/icons-vue'
import { getObservabilityOverview } from '@/api/modules/ops'
import { useAuthStore } from '@/stores/auth'
import ObservabilityDataSourceLinks from './ObservabilityDataSourceLinks.vue'

const authStore = useAuthStore()
const loading = ref(false)
const overview = ref({ modules: {}, summary: {} })
const canViewLinks = computed(() => authStore.hasPermission('ops.observability.link.view'))

const capabilityCards = computed(() => [
  {
    label: '监控看板',
    value: overview.value.modules?.grafana?.dashboard_count || 0,
    desc: '承载 Grafana 看板目录与业务视图',
    tone: '',
  },
  {
    label: '日志数据源',
    value: overview.value.modules?.logs?.datasource_count || 0,
    desc: '日志检索与事件回溯入口',
    tone: 'audit-card--success',
  },
  {
    label: '链路数据源',
    value: overview.value.modules?.tracing?.datasource_count || 0,
    desc: '服务链路与拓扑追踪数据源',
    tone: 'audit-card--warning',
  },
  {
    label: '未确认告警',
    value: overview.value.modules?.alerts?.unacknowledged || 0,
    desc: '待继续排障或确认的告警数',
    tone: 'audit-card--danger',
  },
])

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
.observability-page {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.panel {
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 14px;
  box-shadow: none;
  padding: 14px 16px;
}

.hero {
  align-items: center;
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.hero-title-row {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.hero-icon {
  align-items: center;
  background: rgba(51, 112, 255, 0.1);
  border-radius: 14px;
  color: #245bdb;
  display: inline-flex;
  height: 42px;
  justify-content: center;
  width: 42px;
}

.observability-page h2 {
  color: #0f172a;
  font-size: 23px;
  margin: 0;
}

.page-inline-desc {
  color: #475569;
  font-size: 13px;
}

.observability-summary-grid {
  display: grid;
  gap: 8px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.observability-summary-grid .release-stat-card {
  align-items: flex-start;
}

.observability-summary-grid .release-stat-desc {
  min-height: 34px;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.hero-actions :deep(.el-button) {
  border-radius: 10px;
  font-weight: 500;
  min-height: 32px;
  padding: 0 14px;
}

@media (max-width: 900px) {
  .observability-summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .hero {
    align-items: flex-start;
    flex-direction: column;
  }

  .observability-summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
