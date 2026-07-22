<template>
  <div class="fade-in task-page-shell workbench-page-shell">
    <section class="hero panel task-hero-panel">
      <div class="hero-copy">
        <div class="hero-title-row">
          <span class="hero-icon hero-icon-monitor"><el-icon><Monitor /></el-icon></span>
          <h2>资源底座</h2>
          <p class="page-inline-desc">维护任务执行目标、资源分组与集群归属，作为工作台与计划任务的统一资源入口。</p>
        </div>
      </div>
    </section>

    <div class="stats-grid task-page-stats">
      <div v-for="card in summaryCards" :key="card.label" class="stat-card release-stat-card">
        <div class="stat-value">{{ card.value }}</div>
        <div class="stat-label">{{ card.label }}</div>
        <div class="release-stat-desc">{{ card.desc }}</div>
      </div>
    </div>

    <section class="workbench-inline-tip--panel task-page-tip">
      <div class="tip-panel-head">
        <strong>资源治理上下文</strong>
        <span>先梳理环境、系统与目标分组，再进入资源面板维护主机、容器与集群归属，避免任务入口重复分散。</span>
      </div>
      <div class="tip-panel-list">
        <div class="tip-panel-item">统一纳管主机、容器和集群资源，减少入口重复维护。</div>
        <div class="tip-panel-item">资源归属与任务工作台、计划任务共享，调度口径保持一致。</div>
        <div class="tip-panel-item">建议先整理环境与系统分层，再批量处理资源分组和标签。</div>
        <div class="tip-panel-item">资源治理完成后，工作台与计划任务会直接复用这些目标对象。</div>
      </div>
    </section>

    <TaskResourceBase />
  </div>
</template>

<script setup>
import { Monitor } from '@element-plus/icons-vue'
import TaskResourceBase from '@/components/tasks/TaskResourceBase.vue'

const summaryCards = [
  { label: '资源类型', value: '主机 + 容器', desc: '统一纳管任务执行目标与运行载体' },
  { label: '归属维度', value: '环境 / 系统', desc: '按环境与业务系统建立资源分层' },
  { label: '执行入口', value: '工作台复用', desc: '任务工作台与计划任务共享同一资源底座' },
]
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

.hero-copy {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
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

.hero-icon-monitor {
  background: rgba(36, 91, 219, 0.1);
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
