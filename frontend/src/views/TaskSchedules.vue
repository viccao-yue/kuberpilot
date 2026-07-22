<template>
  <div class="fade-in task-page-shell workbench-page-shell">
    <section class="hero panel task-hero-panel">
      <div class="hero-copy">
        <div class="hero-title-row">
          <span class="hero-icon hero-icon-timer"><el-icon><Timer /></el-icon></span>
          <h2>计划任务</h2>
          <p class="page-inline-desc">承载周期编排、单次触发与执行记录，面向自动化调度与结果追踪场景。</p>
        </div>
      </div>
      <div class="hero-actions">
        <el-button size="small" :icon="Refresh" :loading="loading" @click="reloadResourceTree">刷新资源</el-button>
      </div>
    </section>

    <div class="stats-grid task-page-stats">
      <div class="stat-card release-stat-card">
        <div class="stat-value">{{ environmentCount }}</div>
        <div class="stat-label">环境分层</div>
        <div class="release-stat-desc">当前资源树纳入的执行环境数量</div>
      </div>
      <div class="stat-card release-stat-card">
        <div class="stat-value">{{ systemCount }}</div>
        <div class="stat-label">系统归属</div>
        <div class="release-stat-desc">可直接用于任务编排的系统节点数</div>
      </div>
      <div class="stat-card release-stat-card">
        <div class="stat-value">Cron / 间隔 / 单次</div>
        <div class="stat-label">调度方式</div>
        <div class="release-stat-desc">支持周期调度与手动触发混合编排</div>
      </div>
    </div>

    <section class="workbench-inline-tip--panel task-page-tip">
      <div class="tip-panel-head">
        <strong>调度编排上下文</strong>
        <span>先同步资源树，再进入计划任务中心维护 Cron、间隔或单次触发编排，保证执行目标和运行归属始终一致。</span>
      </div>
      <div class="tip-panel-list">
        <div class="tip-panel-item">资源树已同步 {{ environmentCount }} 个环境、{{ systemCount }} 个系统节点。</div>
        <div class="tip-panel-item">计划任务默认复用资源底座，不再单独维护目标清单。</div>
        <div class="tip-panel-item">适合把周期巡检、批量脚本和一次性操作统一纳入调度中心。</div>
        <div class="tip-panel-item">刷新资源后即可在右侧工作台按最新归属关系创建或调整编排。</div>
      </div>
    </section>

    <CmdbHostScheduleCenter :resource-tree="resourceTree" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { Refresh, Timer } from '@element-plus/icons-vue'
import CmdbHostScheduleCenter from '@/components/cmdb/CmdbHostScheduleCenter.vue'
import { getTaskResourceTree } from '@/api/modules/ops'

const loading = ref(false)
const resourceTree = ref([])
const environmentCount = computed(() => resourceTree.value.length)
const systemCount = computed(() => resourceTree.value.reduce((sum, item) => sum + (item.children || []).length, 0))

function normalizeTree(list = []) {
  return list.map((env) => ({
    ...env,
    treeKey: `environment:${env.id}`,
    children: (env.children || []).map((system) => ({
      ...system,
      treeKey: `system:${system.id}`,
      children: [],
    })),
  }))
}

async function reloadResourceTree() {
  loading.value = true
  try {
    const tree = await getTaskResourceTree()
    resourceTree.value = normalizeTree(tree || [])
  } finally {
    loading.value = false
  }
}

onMounted(reloadResourceTree)
</script>

<style scoped>
.task-page-shell {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.hero.panel.task-hero-panel {
  align-items: center;
  display: flex;
  justify-content: space-between;
  padding: 10px 14px;
}

.hero-copy,
.hero-actions {
  display: flex;
  gap: 4px;
}

.hero-copy {
  flex-wrap: wrap;
}

.hero-title-row {
  align-items: center;
  display: flex;
  gap: 10px;
}

.hero-title-row h2 {
  color: #0f172a;
  font-size: 23px;
  font-weight: 700;
  line-height: 1.1;
  margin: 0;
}

.page-inline-desc {
  color: #475569;
  font-size: 13px;
  line-height: 1.45;
  margin: 0;
  flex: 0 1 auto;
}

.hero-icon {
  align-items: center;
  border-radius: 12px;
  color: #245bdb;
  display: inline-flex;
  font-size: 18px;
  height: 36px;
  justify-content: center;
  width: 36px;
}

.hero-icon-timer {
  background: rgba(36, 91, 219, 0.1);
}

.hero-actions .el-button {
  border-radius: 10px;
  font-weight: 500;
  min-height: 30px;
  padding: 0 12px;
}

.task-page-stats {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.task-page-tip {
  margin-top: -2px;
}

@media (max-width: 980px) {
  .task-page-stats {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .hero.panel.task-hero-panel {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
