<template>
  <div class="fade-in module-manage-page workbench-page-shell">
    <section class="hero panel">
      <div class="release-hero-copy">
        <div class="release-hero-title-row">
          <span class="release-header-icon"><el-icon><Menu /></el-icon></span>
          <h2>模块管理</h2>
          <p class="page-inline-desc">配置左侧菜单模块的显示状态，必选模块保持固定展示。</p>
        </div>
      </div>
    </section>

    <div class="stats-grid module-stats-grid">
      <div class="stat-card release-stat-card">
        <div class="stat-value">{{ modules.length }}</div>
        <div class="stat-label">模块总数</div>
        <div class="release-stat-desc">当前可治理的侧栏模块配置项</div>
      </div>
      <div class="stat-card release-stat-card">
        <div class="stat-value">{{ requiredModuleCount }}</div>
        <div class="stat-label">必选模块</div>
        <div class="release-stat-desc">核心模块保持固定展示，不允许隐藏</div>
      </div>
      <div class="stat-card release-stat-card">
        <div class="stat-value">{{ optionalEnabledCount }}</div>
        <div class="stat-label">已显示模块</div>
        <div class="release-stat-desc">当前对外展示的可选功能模块数量</div>
      </div>
    </div>

    <section class="workbench-inline-tip--panel module-context-tip">
      <div class="tip-panel-head">
        <strong>导航治理上下文</strong>
        <span>模块显隐直接影响左侧导航与用户工作流，建议先确认核心模块固定展示，再按团队场景控制工单系统与容器管理等可选入口。</span>
      </div>
      <div class="tip-panel-list">
        <div class="tip-panel-item">必选模块 {{ requiredModuleCount }} 个，始终对所有具备权限的用户显示。</div>
        <div class="tip-panel-item">当前可隐藏模块中已有 {{ optionalEnabledCount }} 个保持展示，可按团队使用范围逐步收口。</div>
        <div class="tip-panel-item">修改后会即时影响侧栏导航，建议保存前先确认业务入口是否仍完整可达。</div>
        <div class="tip-panel-item">适合把低频模块按环境或组织习惯收起，减少默认导航密度。</div>
      </div>
    </section>

    <div class="workbench-card module-content-card">
      <div class="section-toolbar">
        <div class="toolbar-head">
          <span class="toolbar-title">菜单模块</span>
          <span class="toolbar-desc">工单系统和容器管理可按需隐藏，其余核心模块保持显示。</span>
        </div>
        <div class="workbench-card-actions">
          <el-button class="filter-refresh-btn" :loading="loading" @click="fetchSettings">
            <el-icon><RefreshRight /></el-icon>
            刷新
          </el-button>
          <el-button type="primary" :loading="saving" @click="handleSave">
            <el-icon><Check /></el-icon>
            保存配置
          </el-button>
        </div>
      </div>

      <div v-if="loading" class="console-skeleton">
        <div class="console-skeleton-card console-skeleton-table">
          <div v-for="n in 5" :key="`module-loading-${n}`" class="console-skeleton-row">
            <div class="console-skeleton-cell"></div>
            <div class="console-skeleton-cell"></div>
            <div class="console-skeleton-cell"></div>
            <div class="console-skeleton-cell"></div>
            <div class="console-skeleton-cell"></div>
          </div>
        </div>
      </div>
      <el-table v-else :data="modules" stripe style="width: 100%" class="module-table">
        <el-table-column label="模块" min-width="180">
          <template #default="{ row }">
            <div class="module-name-cell">
              <span class="module-name">{{ row.title }}</span>
              <span class="module-code">{{ row.code }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="说明" min-width="280" show-overflow-tooltip />
        <el-table-column label="配置类型" width="120">
          <template #default="{ row }">
            <el-tag size="small" :type="row.required ? 'info' : 'success'">
              {{ row.required ? '必选模块' : '可隐藏' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="显示状态" width="150">
          <template #default="{ row }">
            <el-switch
              v-model="row.enabled"
              inline-prompt
              active-text="显示"
              inactive-text="隐藏"
              :disabled="row.required"
            />
          </template>
        </el-table-column>
        <el-table-column label="最近更新" width="180">
          <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="更新人" width="120">
          <template #default="{ row }">{{ row.updated_by || '-' }}</template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Check, Menu, RefreshRight } from '@element-plus/icons-vue'
import { getModuleSettings, updateModuleSettings } from '@/api/modules/rbac'

const loading = ref(false)
const saving = ref(false)
const modules = ref([])
const requiredModuleCount = computed(() => modules.value.filter(item => item.required).length)
const optionalEnabledCount = computed(() => modules.value.filter(item => !item.required && item.enabled !== false).length)

function normalizeModules(list = []) {
  return list.map(item => ({
    ...item,
    enabled: item.required ? true : item.enabled !== false,
  }))
}

async function fetchSettings() {
  loading.value = true
  try {
    modules.value = normalizeModules(await getModuleSettings())
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    const payload = modules.value.map(item => ({
      code: item.code,
      enabled: item.required ? true : item.enabled,
    }))
    const response = await updateModuleSettings(payload)
    modules.value = normalizeModules(response.data || response || [])
    window.dispatchEvent(new Event('sxdevops-module-settings-updated'))
    ElMessage.success('模块显示配置已保存')
  } finally {
    saving.value = false
  }
}

function formatTime(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return date.toLocaleString('zh-CN', { hour12: false })
}

onMounted(fetchSettings)
</script>

<style scoped>
.module-manage-page {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.panel {
  background: #ffffff;
  border: 1px solid rgba(15,23,42,.08);
  border-radius: 14px;
  box-shadow: none;
  padding: 14px 16px;
}

.hero {
  margin-bottom: 0;
}

.release-hero-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.release-hero-title-row h2 {
  color: #0f172a;
  font-size: 23px;
  margin: 0;
}

.release-header-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: #245bdb;
  background: rgba(36,91,219,.1);
  border: 0;
}

.module-stats-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.module-stats-grid .release-stat-card {
  min-height: 0;
  padding: 10px 12px;
}

.module-stats-grid .stat-value {
  font-size: 22px;
}

.module-stats-grid .release-stat-desc {
  margin-top: 4px;
}

.module-context-tip {
  margin-top: -2px;
}

.page-inline-desc {
  color: #475569;
  font-size: 13px;
  line-height: 1.45;
  margin: 0;
  flex: 0 1 auto;
}

.module-content-card {
  display: flex;
  flex-direction: column;
}

.module-name-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.module-name {
  color: #0f172a;
  font-weight: 700;
}

.module-code {
  color: #94a3b8;
  font-size: 12px;
}

:deep(.module-table .el-switch.is-disabled) {
  opacity: 0.72;
}

:deep(.module-table .el-table__header-wrapper th.el-table__cell:last-child),
:deep(.module-table .el-table__body-wrapper td.el-table__cell:last-child) {
  padding-right: 20px;
}

:deep(.module-table .el-table__body-wrapper td.el-table__cell:last-child .cell),
:deep(.module-table .el-table__header-wrapper th.el-table__cell:last-child .cell) {
  padding-right: 4px;
}

@media (max-width: 760px) {
  .module-stats-grid {
    grid-template-columns: 1fr;
  }

  .section-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }
}

.hero.panel { border-radius: 14px; }
</style>
