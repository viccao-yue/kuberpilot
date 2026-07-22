<template>
  <div class="fade-in task-page-shell workbench-page-shell">
    <section class="hero panel task-hero-panel">
      <div class="release-hero-copy">
        <span class="task-hero-eyebrow">Execution Console</span>
        <div class="release-hero-title-row release-hero-title-inline">
          <span class="task-header-icon"><el-icon><Operation /></el-icon></span>
          <div class="task-hero-title-block">
            <h2>任务工作台</h2>
            <p class="page-inline-desc">集中处理任务下发、AIOps 建议联动、模板复用与执行回溯，提供更直接的控制台操作入口。</p>
          </div>
        </div>
      </div>
      <div class="task-hero-meta">
        <span class="task-hero-chip">环境组 · {{ environmentCount }}</span>
        <span class="task-hero-chip">系统树 · {{ systemCount }}</span>
        <span class="task-hero-chip">{{ loading ? '资源树 · 加载中' : '资源树 · 已就绪' }}</span>
      </div>
    </section>

    <CmdbHostTaskCenter
      :resource-tree="resourceTree"
      :resource-loading="loading"
      :on-reload-resources="reloadResourceTree"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { Operation } from '@element-plus/icons-vue'
import CmdbHostTaskCenter from '@/components/cmdb/CmdbHostTaskCenter.vue'
import { getTaskResourceTree } from '@/api/modules/ops'

const loading = ref(false)
const resourceTree = ref([])
const environmentCount = computed(() => resourceTree.value.length)
const systemCount = computed(() => resourceTree.value.reduce((total, item) => total + (item.children?.length || 0), 0))

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

.panel {
  background: linear-gradient(180deg, rgba(255,255,255,.98) 0%, rgba(250,252,255,.96) 100%);
  border: 1px solid rgba(15,23,42,.08);
  border-radius: 18px;
  box-shadow: 0 8px 24px rgba(15,23,42,.04);
  padding: 14px 16px;
}

.task-hero-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 0;
  background: linear-gradient(135deg, #fbfdff 0%, #f7faff 52%, #f9fbfd 100%);
  border-color: rgba(36,91,219,.09);
}

.task-hero-eyebrow {
  display: inline-flex;
  margin-bottom: 6px;
  color: #245bdb;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .08em;
  text-transform: uppercase;
}

.release-hero-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.task-hero-title-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.task-hero-panel h2 {
  color: #0f172a;
  font-size: 23px;
  margin: 0;
}

.page-inline-desc {
  color: #475569;
  font-size: 13px;
  line-height: 1.45;
  margin: 0;
  flex: 0 1 auto;
  transform: translateY(1px);
}

.task-header-icon {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  color: #245bdb;
  background: linear-gradient(180deg,#f3f7ff 0%,#ebf2ff 100%);
  border: 1px solid rgba(36,91,219,.12);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.8);
}

.task-hero-meta {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.task-hero-chip {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid rgba(36,91,219,.1);
  background: rgba(255,255,255,.78);
  color: #475569;
  font-size: 11px;
}

@media (max-width: 760px) {
  .task-hero-panel {
    align-items: flex-start;
    flex-direction: column;
  }

  .task-hero-meta {
    justify-content: flex-start;
  }
}

.hero.panel {
  border-radius: 20px;
}
</style>
