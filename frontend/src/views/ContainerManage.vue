<template>
  <div class="fade-in workbench-page-shell docker-page-shell">
    <section class="hero panel docker-hero">
      <div class="release-hero-copy">
        <span class="docker-hero-eyebrow">Container Console</span>
        <div class="release-hero-title-row release-hero-title-inline">
          <span class="release-header-icon docker-header-icon"><el-icon><Platform /></el-icon></span>
          <div class="docker-hero-title-block">
            <h2>Docker 环境</h2>
            <p class="subtitle inline-subtitle docker-hero-desc">统一管理 Docker 主机、容器与镜像资源。</p>
          </div>
        </div>
      </div>
      <div class="docker-hero-meta">
        <span class="docker-hero-chip">当前视图 · {{ activeTabLabel }}</span>
        <span class="docker-hero-chip">环境 · {{ currentHostLabel }}</span>
        <span class="docker-hero-chip">{{ dockerConnectionLabel }}</span>
      </div>
    </section>

    <section class="stats-grid docker-top-stats">
      <article v-for="card in summaryCards" :key="card.key" class="release-stat-card docker-summary-card" :class="card.tone">
        <div class="stat-card-head">
          <span class="stat-card-label">{{ card.label }}</span>
          <span class="stat-card-badge">{{ card.badge }}</span>
        </div>
        <div class="stat-card-value">{{ card.value }}</div>
        <div class="stat-card-foot">
          <span>{{ card.meta }}</span>
          <span>{{ card.foot }}</span>
        </div>
      </article>
    </section>

    <section class="panel docker-context-strip">
      <div class="docker-context-copy">
        <span class="docker-context-title">当前操作上下文</span>
        <span class="docker-context-desc">先确认当前视图、选中环境与连接状态，再进入环境、容器或镜像工作台。</span>
      </div>
      <div class="docker-context-items">
        <span class="docker-context-item">{{ activeTabLabel }}</span>
        <span class="docker-context-item">{{ currentHostLabel }}</span>
        <span class="docker-context-item">{{ dockerConnectionLabel }}</span>
        <span class="docker-context-item">{{ currentScopeLabel }}</span>
      </div>
    </section>

    <section class="panel docker-nav-panel">
      <div class="docker-nav-head">
        <span class="docker-nav-title">功能视图</span>
        <span class="docker-nav-desc">在同一工作台内切换主机环境、运行容器和镜像资产，统一筛选与操作密度。</span>
      </div>
      <div class="neo-tabs theme-blue docker-main-tabs">
      <button v-for="tab in mainTabs" :key="tab.key" class="neo-tab-btn" :class="{ active: activeTab === tab.key }" @click="switchTab(tab.key)">
        <el-icon style="margin-right:4px;"><component :is="tab.icon" /></el-icon>
        {{ tab.label }}
      </button>
      </div>
    </section>

    <div v-if="activeTab !== 'hosts' && selectedHostId && !selectedHostConnected" class="empty-state">
      <div class="empty-icon">⚙</div>
      <div class="empty-text">当前环境未连接，请先测试连接或切换到已连接的 Docker 环境。</div>
      <div style="display:flex;gap:8px;margin-top:8px;">
        <el-button type="primary" @click="switchTab('hosts')">前往环境管理</el-button>
        <el-button @click="refreshView">重新加载</el-button>
      </div>
    </div>

    <template v-if="activeTab === 'hosts'">
      <div class="workbench-card docker-host-card">
        <div class="section-toolbar">
          <div class="toolbar-head">
            <span class="toolbar-title">环境列表</span>
            <span class="toolbar-desc">统一管理已接入的 Docker 主机环境。</span>
          </div>
          <div class="workbench-card-actions">
            <el-button class="filter-refresh-btn" @click="fetchHosts">
              <el-icon><RefreshRight /></el-icon>
              刷新
            </el-button>
            <el-button v-if="canManageDocker" class="filter-refresh-btn" @click="openHostDialog()">
              <el-icon><Plus /></el-icon>
              新增环境
            </el-button>
          </div>
        </div>

        <div class="workbench-toolbar workbench-toolbar--history docker-host-toolbar">
          <div class="workbench-toolbar-left">
            <el-input v-model="hostSearchKeyword" clearable placeholder="搜索环境名称、IP、描述" style="width: 320px" />
          </div>
          <div class="workbench-toolbar-right">
            <el-tag size="large" type="info">环境总数 {{ dockerHostStats.total }}</el-tag>
            <el-tag size="large" type="success">运行中 {{ dockerHostStats.connected }}</el-tag>
          </div>
        </div>

        <el-table :data="filteredHosts" stripe v-loading="loading" style="width:100%" class="docker-host-table">
          <el-table-column label="环境资源" min-width="320">
            <template #default="{ row }">
              <div class="docker-resource-cell">
                <div class="docker-resource-title">
                <span class="state-pulse" :class="row.status === 'connected' ? 'running' : 'exited'"></span>
                  <span>{{ row.name }}</span>
                </div>
                <div class="docker-resource-sub">{{ row.ip_address || '-' }} · SSH {{ row.ssh_port || 22 }} · {{ row.ssh_user || '-' }}</div>
                <div class="docker-resource-meta">{{ row.description || '用于承载 Docker 主机环境接入与状态管理。' }}</div>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="110">
            <template #default="{ row }">
              <el-tag :type="row.status === 'connected' ? 'success' : 'danger'" size="small" class="docker-inline-tag">{{ row.status === 'connected' ? '运行中' : '未连接' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="docker_api_version" label="Docker 版本" width="120" />
          <el-table-column v-if="canManageDocker" label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" class="docker-row-action" @click="testHost(row)">测试连接</el-button>
              <el-button link type="info" size="small" class="docker-row-action" @click="openHostDialog(row)">编辑</el-button>
              <el-popconfirm title="确定删除该环境？" @confirm="delHost(row)">
                <template #reference><el-button link type="danger" size="small" class="docker-row-action">删除</el-button></template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </template>

    <template v-else-if="activeTab === 'containers'">
      <div v-if="!selectedHostId" class="empty-state">
        <div class="empty-icon">📦</div>
        <div class="empty-text">请先选择一个 Docker 环境</div>
      </div>
      <div v-else class="workbench-card docker-resource-card">
        <div class="section-toolbar">
          <div class="toolbar-head">
            <span class="toolbar-title">{{ resourcePanelTitle }}</span>
            <span class="toolbar-desc">{{ resourcePanelDesc }}</span>
          </div>
          <div class="workbench-card-actions">
            <el-button @click="refreshView"><el-icon><RefreshRight /></el-icon>刷新</el-button>
          </div>
        </div>

        <div class="workbench-toolbar workbench-toolbar--history filter-bar--context">
          <div class="workbench-toolbar-left">
            <el-input v-model="containerKeyword" clearable placeholder="搜索容器名称、镜像、端口" style="width: 320px" />
            <el-select v-model="containerStateFilter" style="width: 140px">
              <el-option label="全部状态" value="all" />
              <el-option label="运行中" value="running" />
              <el-option label="已停止" value="stopped" />
              <el-option label="需关注" value="attention" />
            </el-select>
          </div>
          <div class="workbench-toolbar-right docker-context-toolbar-right">
            <div class="filter-inline-context">
              <span class="filter-inline-label">当前环境</span>
              <el-select
                v-model="selectedHostId"
                placeholder="选择环境"
                @change="onHostChange"
                class="industrial-select toolbar-filter-select filter-inline-select"
                popper-class="docker-context-popper"
              >
                <el-option v-for="h in dockerHosts" :key="h.id" :label="h.name" :value="h.id">
                  <div class="context-option-row">
                    <div class="context-option-main">
                      <div class="context-option-head">
                        <div class="context-option-main context-option-main--host">
                          <span class="state-pulse" :class="h.status === 'connected' ? 'running' : 'exited'"></span>
                          <span class="context-option-title">{{ h.name }}</span>
                        </div>
                        <span class="context-status-pill" :class="h.status === 'connected' ? 'context-status-pill--success' : 'context-status-pill--info'">
                          {{ h.status === 'connected' ? '在线' : '离线' }}
                        </span>
                      </div>
                      <span class="context-option-subtitle">{{ hostOptionMeta(h) }}</span>
                    </div>
                  </div>
                </el-option>
              </el-select>
            </div>
          </div>
        </div>

        <el-table :data="filteredContainers" stripe v-loading="loading" style="width:100%" class="docker-container-table">
          <el-table-column label="容器资源" min-width="360">
            <template #default="{ row }">
              <div class="docker-resource-cell">
                <div class="docker-resource-title">
                <span class="state-pulse" :class="row.state"></span>
                  <span>{{ row.name }}</span>
                </div>
                <div class="docker-resource-sub">{{ row.image || '-' }}</div>
                <div class="docker-resource-meta">{{ row.ports || '未暴露端口' }}</div>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="150">
            <template #default="{ row }">
              <el-tag :type="containerStateType(row.state)" size="small" class="docker-inline-tag">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="280" fixed="right">
            <template #default="{ row }">
              <el-button v-if="canManageDocker && row.state !== 'running'" link type="success" size="small" class="docker-row-action" @click="doAction(row, 'start')">启动</el-button>
              <el-button v-if="canManageDocker && row.state === 'running'" link type="warning" size="small" class="docker-row-action" @click="doAction(row, 'stop')">停止</el-button>
              <el-button v-if="canManageDocker && row.state === 'running'" link type="primary" size="small" class="docker-row-action" @click="doAction(row, 'restart')">重启</el-button>
              <el-button link type="info" size="small" class="docker-row-action" @click="viewContainerLogs(row)">日志</el-button>
              <el-button link type="info" size="small" class="docker-row-action" @click="inspectContainer(row)">详情</el-button>
              <el-popconfirm v-if="canManageDocker" title="确定删除该容器？" @confirm="removeContainer(row)">
                <template #reference><el-button link type="danger" size="small" class="docker-row-action">删除</el-button></template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </template>

    <template v-else-if="activeTab === 'images'">
      <div v-if="!selectedHostId" class="empty-state">
        <div class="empty-icon">🖼️</div>
        <div class="empty-text">请先选择一个 Docker 环境</div>
      </div>
      <div v-else class="workbench-card docker-resource-card">
        <div class="section-toolbar">
          <div class="toolbar-head">
            <span class="toolbar-title">{{ resourcePanelTitle }}</span>
            <span class="toolbar-desc">{{ resourcePanelDesc }}</span>
          </div>
          <div class="workbench-card-actions">
            <el-button @click="refreshView"><el-icon><RefreshRight /></el-icon>刷新</el-button>
          </div>
        </div>

        <div class="workbench-toolbar workbench-toolbar--history filter-bar--context">
          <div class="workbench-toolbar-left">
            <el-input v-model="imageKeyword" clearable placeholder="搜索仓库、标签、镜像 ID" style="width: 320px" />
          </div>
          <div class="workbench-toolbar-right docker-context-toolbar-right docker-image-toolbar-right">
            <div class="filter-inline-context">
              <span class="filter-inline-label">当前环境</span>
              <el-select
                v-model="selectedHostId"
                placeholder="选择环境"
                @change="onHostChange"
                class="industrial-select toolbar-filter-select filter-inline-select"
                popper-class="docker-context-popper"
              >
                <el-option v-for="h in dockerHosts" :key="h.id" :label="h.name" :value="h.id">
                  <div class="context-option-row">
                    <div class="context-option-main">
                      <div class="context-option-head">
                        <div class="context-option-main context-option-main--host">
                          <span class="state-pulse" :class="h.status === 'connected' ? 'running' : 'exited'"></span>
                          <span class="context-option-title">{{ h.name }}</span>
                        </div>
                        <span class="context-status-pill" :class="h.status === 'connected' ? 'context-status-pill--success' : 'context-status-pill--info'">
                          {{ h.status === 'connected' ? '在线' : '离线' }}
                        </span>
                      </div>
                      <span class="context-option-subtitle">{{ hostOptionMeta(h) }}</span>
                    </div>
                  </div>
                </el-option>
              </el-select>
            </div>
            <el-tag v-if="imageSelection.length" type="info" size="large">已选 {{ imageSelection.length }} 个镜像</el-tag>
            <el-button v-if="canManageDocker" type="warning" plain @click="pruneDanglingImages">清理悬空镜像</el-button>
            <el-button v-if="canManageDocker" type="danger" plain :disabled="!imageSelection.length" @click="removeSelectedImages">批量删除</el-button>
          </div>
        </div>

        <el-table :data="filteredImages" stripe v-loading="loading" style="width:100%" class="docker-image-table" @selection-change="handleImageSelectionChange">
          <el-table-column v-if="canManageDocker" type="selection" width="48" />
          <el-table-column label="镜像资源" min-width="360">
            <template #default="{ row }">
              <div class="docker-resource-cell">
                <div class="docker-resource-title">
                  <span>{{ row.repository || '<none>' }}</span>
                </div>
                <div class="docker-resource-sub">{{ row.tag || '<none>' }}</div>
                <div class="docker-resource-meta">{{ row.created || '创建时间未知' }}</div>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="id" label="镜像 ID" width="160">
            <template #default="{ row }">
              <span class="docker-mono-id">{{ row.id?.slice(0, 12) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="size" label="大小" width="110" />
        </el-table>
      </div>
    </template>

    <el-dialog v-model="logVisible" class="docker-console-dialog docker-console-dialog--wide" :title="'容器日志 - ' + logContainerName" width="90%" style="max-width:900px;" top="3vh" append-to-body destroy-on-close>
      <template #header>
        <div class="docker-dialog-header docker-dialog-header--compact">
          <span class="docker-dialog-eyebrow">Container Logs</span>
          <strong>容器日志</strong>
          <span>{{ logContainerName || '-' }}</span>
        </div>
      </template>
      <div class="docker-console-log-toolbar">
        <el-select v-model="logTailLines" size="small" style="width: 132px" @change="reloadContainerLogs">
          <el-option :value="100" label="最近 100 行" />
          <el-option :value="200" label="最近 200 行" />
          <el-option :value="500" label="最近 500 行" />
          <el-option :value="1000" label="最近 1000 行" />
        </el-select>
        <el-button size="small" class="filter-refresh-btn" @click="reloadContainerLogs" :disabled="!logContainerId"><el-icon><RefreshRight /></el-icon>刷新日志</el-button>
      </div>
      <pre class="docker-console-log">{{ logContent || '加载中...' }}</pre>
      <template #footer>
        <div class="docker-dialog-footer">
          <el-button size="small" @click="logVisible = false">关闭</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="inspectVisible" class="docker-console-dialog docker-console-dialog--wide" :title="'容器详情 - ' + inspectContainerName" width="90%" style="max-width:900px;" top="3vh" append-to-body destroy-on-close>
      <template #header>
        <div class="docker-dialog-header docker-dialog-header--compact">
          <span class="docker-dialog-eyebrow">Container Inspect</span>
          <strong>容器详情</strong>
          <span>{{ inspectContainerName || '-' }}</span>
        </div>
      </template>
      <pre class="docker-console-log">{{ inspectContent || '加载中...' }}</pre>
      <template #footer>
        <div class="docker-dialog-footer">
          <el-button size="small" @click="inspectVisible = false">关闭</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="hostDialogVisible" class="docker-console-dialog docker-console-dialog--host" :title="editingHostId ? '编辑 Docker 环境' : '新增 Docker 环境'" width="90%" style="max-width:560px;" top="5vh" append-to-body destroy-on-close>
      <template #header>
        <div class="docker-dialog-header">
          <span class="docker-dialog-eyebrow">Docker Host</span>
          <strong>{{ editingHostId ? '编辑 Docker 环境' : '新增 Docker 环境' }}</strong>
          <span>用于接入 Docker 主机，支持环境级连接测试与容器/镜像工作台。</span>
        </div>
      </template>
      <el-form :model="hostForm" label-width="100px" class="docker-host-form">
        <el-form-item label="环境名称"><el-input v-model="hostForm.name" size="small" placeholder="例如 prod-docker-01" /></el-form-item>
        <el-form-item label="IP 地址"><el-input v-model="hostForm.ip_address" size="small" placeholder="例如 192.168.1.100" /></el-form-item>
        <el-form-item label="SSH 端口"><el-input-number v-model="hostForm.ssh_port" size="small" :min="1" :max="65535" controls-position="right" style="width: 150px" /></el-form-item>
        <el-form-item label="SSH 用户"><el-input v-model="hostForm.ssh_user" size="small" placeholder="root" /></el-form-item>
        <el-form-item label="SSH 密码"><el-input v-model="hostForm.ssh_password" size="small" type="password" show-password :placeholder="editingHostId ? '留空则不更新' : '请输入 SSH 密码'" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="hostForm.description" size="small" placeholder="环境用途简述" /></el-form-item>
      </el-form>
      <template #footer>
        <div class="docker-dialog-footer">
          <el-button size="small" @click="hostDialogVisible = false">取消</el-button>
          <el-button size="small" type="primary" @click="saveHost" :loading="savingHost">保存</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useRouteTabState } from '@/composables/useRouteTabState'
import {
  createDockerHost,
  deleteDockerHost,
  dockerContainerAction,
  dockerContainerRemove,
  dockerPruneDanglingImages,
  dockerRemoveImages,
  getDockerContainerInspect,
  getDockerContainerLogs,
  getDockerContainers,
  getDockerHosts,
  getDockerImages,
  testDockerConnection,
  updateDockerHost,
} from '@/api/modules/container'

const authStore = useAuthStore()
const canManageDocker = computed(() => authStore.hasPermission('ops.docker.manage'))

const mainTabs = [
  { key: 'hosts', label: '环境管理', icon: 'OfficeBuilding' },
  { key: 'containers', label: '容器管理', icon: 'Box' },
  { key: 'images', label: '镜像管理', icon: 'Files' },
]

const tabState = useRouteTabState({
  tabs: () => mainTabs.map(item => item.key),
  defaultTab: 'hosts',
})
const activeTab = tabState.activeTab
const loading = ref(false)

const dockerHosts = ref([])
const selectedHostId = ref(null)
const hostSearchKeyword = ref('')

const containers = ref([])
const images = ref([])
const containerKeyword = ref('')
const containerStateFilter = ref('all')
const imageKeyword = ref('')
const imageSelection = ref([])

const selectedHost = computed(() => dockerHosts.value.find(item => item.id === selectedHostId.value) || null)
const selectedHostConnected = computed(() => selectedHost.value?.status === 'connected')
const activeTabLabel = computed(() => mainTabs.find(item => item.key === activeTab.value)?.label || '环境管理')
const currentHostLabel = computed(() => selectedHost.value?.name || '未选择环境')
const dockerConnectionLabel = computed(() => {
  if (!selectedHost.value) return '连接状态 · 未选择'
  return selectedHostConnected.value ? '连接状态 · 在线' : '连接状态 · 离线'
})
const currentScopeLabel = computed(() => {
  if (activeTab.value === 'hosts') return `环境总数 · ${dockerHostStats.value.total}`
  if (activeTab.value === 'containers') return `容器总数 · ${containerStats.value.total}`
  return `镜像总数 · ${imageStats.value.total}`
})

const dockerHostStats = computed(() => ({
  total: dockerHosts.value.length,
  connected: dockerHosts.value.filter(item => item.status === 'connected').length,
  attention: dockerHosts.value.filter(item => item.status !== 'connected').length,
  selected: selectedHost.value?.name || '未选择',
}))

const filteredHosts = computed(() => {
  const keyword = hostSearchKeyword.value.trim().toLowerCase()
  if (!keyword) return dockerHosts.value
  return dockerHosts.value.filter((item) =>
    [item.name, item.ip_address, item.description, item.docker_api_version].some((field) => String(field || '').toLowerCase().includes(keyword)),
  )
})

const containerStats = computed(() => {
  const total = containers.value.length
  const running = containers.value.filter(item => item.state === 'running').length
  const attention = containers.value.filter((item) => ['restarting', 'dead'].includes(item.state) || String(item.status || '').toLowerCase().includes('unhealthy')).length
  const uniqueImages = new Set(containers.value.map(item => item.image).filter(Boolean)).size
  return { total, running, attention, uniqueImages }
})

const filteredContainers = computed(() => {
  const keyword = containerKeyword.value.trim().toLowerCase()
  return containers.value.filter((item) => {
    const matchesKeyword = !keyword || [item.name, item.image, item.ports, item.status].some((field) => String(field || '').toLowerCase().includes(keyword))
    if (!matchesKeyword) return false
    if (containerStateFilter.value === 'all') return true
    if (containerStateFilter.value === 'running') return item.state === 'running'
    if (containerStateFilter.value === 'stopped') return ['exited', 'dead'].includes(item.state)
    return ['restarting', 'dead'].includes(item.state) || String(item.status || '').toLowerCase().includes('unhealthy')
  })
})

const imageStats = computed(() => ({
  total: images.value.length,
  repositories: new Set(images.value.map(item => item.repository).filter(item => item && item !== '<none>')).size,
  dangling: images.value.filter(item => item.repository === '<none>' || item.tag === '<none>').length,
  version: selectedHost.value?.docker_api_version || '未知',
}))

const filteredImages = computed(() => {
  const keyword = imageKeyword.value.trim().toLowerCase()
  if (!keyword) return images.value
  return images.value.filter((item) =>
    [item.repository, item.tag, item.id, item.size, item.created].some((field) => String(field || '').toLowerCase().includes(keyword)),
  )
})

const summaryCards = computed(() => {
  if (activeTab.value === 'hosts') {
    return [
      { key: 'hosts-total', label: '环境总数', value: dockerHostStats.value.total, badge: 'Hosts', meta: '已接入 Docker 主机', foot: '统一环境池', tone: 'tone-slate' },
      { key: 'hosts-connected', label: '运行中', value: dockerHostStats.value.connected, badge: 'Online', meta: '连接正常的环境', foot: '可直接进入资源面板', tone: 'tone-emerald' },
      { key: 'hosts-attention', label: '待处理', value: dockerHostStats.value.attention, badge: 'Alert', meta: '连接异常或待检查', foot: '建议先测试连接', tone: 'tone-amber' },
      { key: 'hosts-current', label: '当前环境', value: dockerHostStats.value.selected, badge: 'Scope', meta: dockerConnectionLabel.value, foot: currentScopeLabel.value, tone: 'tone-blue' },
    ]
  }
  if (activeTab.value === 'containers') {
    return [
      { key: 'containers-total', label: '容器总数', value: containerStats.value.total, badge: 'Containers', meta: currentHostLabel.value, foot: '当前环境容器池', tone: 'tone-slate' },
      { key: 'containers-running', label: '运行中', value: containerStats.value.running, badge: 'Healthy', meta: '处于运行态的容器', foot: '持续提供服务', tone: 'tone-emerald' },
      { key: 'containers-attention', label: '需关注', value: containerStats.value.attention, badge: 'Attention', meta: '重启、故障或不健康', foot: '优先处理异常实例', tone: 'tone-amber' },
      { key: 'containers-images', label: '镜像种类', value: containerStats.value.uniqueImages, badge: 'Images', meta: dockerConnectionLabel.value, foot: currentScopeLabel.value, tone: 'tone-blue' },
    ]
  }
  return [
    { key: 'images-total', label: '镜像总数', value: imageStats.value.total, badge: 'Images', meta: currentHostLabel.value, foot: '当前环境镜像池', tone: 'tone-slate' },
    { key: 'images-repositories', label: '仓库数', value: imageStats.value.repositories, badge: 'Repos', meta: '有效仓库数量', foot: '关注仓库分布', tone: 'tone-emerald' },
    { key: 'images-dangling', label: '悬空镜像', value: imageStats.value.dangling, badge: 'Cleanup', meta: '待清理镜像', foot: '降低磁盘占用', tone: 'tone-amber' },
    { key: 'images-version', label: 'Docker 版本', value: imageStats.value.version, badge: 'Engine', meta: dockerConnectionLabel.value, foot: currentScopeLabel.value, tone: 'tone-blue' },
  ]
})

const resourcePanelMeta = computed(() => {
  const map = {
    containers: {
      title: '容器列表',
      desc: '统一查看当前环境容器状态、镜像、端口与常用运维操作。',
    },
    images: {
      title: '镜像列表',
      desc: '统一管理当前环境镜像、仓库分布与悬空镜像清理。',
    },
  }
  return map[activeTab.value] || {
    title: '资源列表',
    desc: '统一使用工作台式布局承载筛选与列表。',
  }
})

const resourcePanelTitle = computed(() => resourcePanelMeta.value.title)
const resourcePanelDesc = computed(() => resourcePanelMeta.value.desc)

function switchTab(tab) {
  tabState.switchTab(tab)
}

function onHostChange() {
  fetchCurrentTab()
}

function hostOptionMeta(host) {
  const ip = host?.ip_address || '未配置 IP'
  const version = host?.docker_api_version || '未知版本'
  return `${ip} · Docker ${version}`
}

async function fetchHosts() {
  loading.value = true
  try {
    const res = await getDockerHosts()
    dockerHosts.value = res.results || res
    const hasSelection = dockerHosts.value.some(item => item.id === selectedHostId.value)
    selectedHostId.value = hasSelection ? selectedHostId.value : (dockerHosts.value[0]?.id || null)
  } finally {
    loading.value = false
  }
}

async function fetchCurrentTab() {
  if (!selectedHostId.value && activeTab.value !== 'hosts') return
  loading.value = true
  try {
    if (activeTab.value === 'containers') {
      containers.value = await getDockerContainers(selectedHostId.value)
    } else if (activeTab.value === 'images') {
      images.value = await getDockerImages(selectedHostId.value)
      imageSelection.value = []
    }
  } catch (error) {
    ElMessage.error('获取数据失败')
  } finally {
    loading.value = false
  }
}

function refreshView() {
  if (activeTab.value === 'hosts') {
    fetchHosts()
    return
  }
  fetchCurrentTab()
}

function handleImageSelectionChange(rows) {
  imageSelection.value = rows || []
}

function containerStateType(state) {
  const mapping = { running: 'success', exited: 'danger', paused: 'warning', created: 'info', restarting: 'warning', dead: 'danger' }
  return mapping[state] || 'info'
}

async function doAction(row, action) {
  if (!canManageDocker.value) return
  try {
    const res = await dockerContainerAction(row.id, selectedHostId.value, action)
    ElMessage.success(res.message || `${action} 成功`)
    fetchCurrentTab()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

async function removeContainer(row) {
  if (!canManageDocker.value) return
  try {
    await dockerContainerRemove(row.id, selectedHostId.value)
    ElMessage.success('容器已删除')
    fetchCurrentTab()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

const logVisible = ref(false)
const logContainerId = ref('')
const logContainerName = ref('')
const logContent = ref('')
const logTailLines = ref(200)

async function viewContainerLogs(row) {
  logContainerId.value = row.id
  logContainerName.value = row.name
  logContent.value = ''
  logVisible.value = true
  await reloadContainerLogs()
}

async function reloadContainerLogs() {
  if (!logContainerId.value || !selectedHostId.value) return
  try {
    const res = await getDockerContainerLogs(logContainerId.value, selectedHostId.value, logTailLines.value)
    logContent.value = res.logs
  } catch (error) {
    logContent.value = '获取日志失败'
  }
}

const inspectVisible = ref(false)
const inspectContainerName = ref('')
const inspectContent = ref('')

async function inspectContainer(row) {
  inspectContainerName.value = row.name
  inspectContent.value = ''
  inspectVisible.value = true
  try {
    const res = await getDockerContainerInspect(row.id, selectedHostId.value)
    inspectContent.value = JSON.stringify(res, null, 2)
  } catch (error) {
    inspectContent.value = '获取详情失败'
  }
}

async function removeSelectedImages() {
  if (!canManageDocker.value || !selectedHostId.value || !imageSelection.value.length) return
  try {
    const res = await dockerRemoveImages(selectedHostId.value, imageSelection.value.map(item => item.id))
    ElMessage.success(res.message || '镜像已删除')
    await fetchCurrentTab()
  } catch (error) {
    ElMessage.error('批量删除镜像失败')
  }
}

async function pruneDanglingImages() {
  if (!canManageDocker.value || !selectedHostId.value) return
  try {
    const res = await dockerPruneDanglingImages(selectedHostId.value)
    ElMessage.success(res.message || '悬空镜像已清理')
    await fetchCurrentTab()
  } catch (error) {
    ElMessage.error('清理悬空镜像失败')
  }
}

const hostDialogVisible = ref(false)
const editingHostId = ref(null)
const savingHost = ref(false)
const hostForm = ref({ name: '', ip_address: '', ssh_port: 22, ssh_user: 'root', ssh_password: '', description: '' })

function openHostDialog(host) {
  if (!canManageDocker.value) return
  if (host) {
    editingHostId.value = host.id
    hostForm.value = {
      name: host.name,
      ip_address: host.ip_address,
      ssh_port: host.ssh_port,
      ssh_user: host.ssh_user,
      ssh_password: '',
      description: host.description,
    }
  } else {
    editingHostId.value = null
    hostForm.value = { name: '', ip_address: '', ssh_port: 22, ssh_user: 'root', ssh_password: '', description: '' }
  }
  hostDialogVisible.value = true
}

async function saveHost() {
  if (!canManageDocker.value) return
  if (!hostForm.value.name) return ElMessage.warning('请填写环境名称')
  if (!hostForm.value.ip_address) return ElMessage.warning('请填写 IP 地址')
  savingHost.value = true
  try {
    const data = { ...hostForm.value }
    if (!data.ssh_password) delete data.ssh_password
    if (editingHostId.value) {
      await updateDockerHost(editingHostId.value, data)
      ElMessage.success('环境已更新')
    } else {
      await createDockerHost(data)
      ElMessage.success('环境已添加')
    }
    hostDialogVisible.value = false
    fetchHosts()
  } finally {
    savingHost.value = false
  }
}

async function testHost(row) {
  if (!canManageDocker.value) return
  try {
    const res = await testDockerConnection(row.id)
    if (res.success) ElMessage.success(res.message)
    else ElMessage.error(res.message)
    fetchHosts()
  } catch (error) {
    ElMessage.error('连接测试失败')
  }
}

async function delHost(row) {
  if (!canManageDocker.value) return
  try {
    await deleteDockerHost(row.id)
    ElMessage.success('环境已删除')
    if (selectedHostId.value === row.id) selectedHostId.value = null
    fetchHosts()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

watch(activeTab, (tab, prev) => {
  if (!tab || tab === prev) return
  if (tab === 'hosts') {
    fetchHosts()
  } else if (selectedHostId.value) {
    fetchCurrentTab()
  }
})

onMounted(() => {
  fetchHosts().then(() => {
    if (activeTab.value !== 'hosts') {
      fetchCurrentTab()
    }
  })
})
</script>

<style scoped>
.docker-hero {
  background: linear-gradient(135deg, #fbfdff 0%, #f7faff 52%, #f9fbfd 100%);
  border-color: rgba(36, 91, 219, 0.09);
  display: flex;
  gap: 12px;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0;
}

.docker-hero-eyebrow {
  display: inline-flex;
  margin-bottom: 6px;
  color: #245bdb;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.docker-hero-title-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.docker-hero-desc {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.45;
}

.docker-hero-meta {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.docker-hero-chip,
.docker-context-item {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid rgba(36, 91, 219, 0.1);
  background: rgba(255, 255, 255, 0.8);
  color: #475569;
  font-size: 11px;
}

.docker-page-shell :deep(.release-hero-title-row) {
  display: flex;
  align-items: center;
  gap: 12px;
}

.docker-page-shell :deep(.release-hero-title-inline) {
  flex-wrap: wrap;
}

.docker-page-shell :deep(.hero h2) {
  margin: 0;
  font-size: 23px;
  color: #0f172a;
}

.docker-header-icon {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  color: #245bdb;
  background: linear-gradient(180deg, #f3f7ff 0%, #ebf2ff 100%);
  border: 1px solid rgba(36, 91, 219, 0.12);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.docker-main-tabs {
  margin-top: 0;
  margin-bottom: 0;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
}

.docker-page-shell :deep(.neo-tab-btn) {
  min-height: 42px;
  padding: 0 16px;
  border-radius: 8px;
  font-size: 13px;
}

.docker-page-shell :deep(.neo-tabs) {
  padding: 3px;
  border-radius: 12px;
  background: rgba(248, 250, 252, 0.88);
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.docker-page-shell :deep(.docker-main-tabs .neo-tab-btn.active) {
  color: #245bdb;
  font-weight: 600;
  background: rgba(36, 91, 219, 0.12);
  box-shadow: inset 0 0 0 1px rgba(36, 91, 219, 0.12), 0 8px 16px rgba(36, 91, 219, 0.08);
}

.docker-page-shell :deep(.docker-main-tabs .neo-tab-btn:hover) {
  background: rgba(36, 91, 219, 0.06);
}

.docker-top-stats {
  gap: 8px;
}

.docker-summary-card {
  min-height: 82px;
  padding: 10px 12px;
}

.docker-summary-card.tone-slate {
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
}

.docker-summary-card.tone-emerald {
  background: linear-gradient(180deg, #f5fffb 0%, #ecfdf5 100%);
}

.docker-summary-card.tone-amber {
  background: linear-gradient(180deg, #fffdf7 0%, #fffbeb 100%);
}

.docker-summary-card.tone-blue {
  background: linear-gradient(180deg, #f8fbff 0%, #eef5ff 100%);
}

.docker-context-strip,
.docker-nav-panel {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.docker-context-copy,
.docker-nav-head {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.docker-context-title,
.docker-nav-title {
  color: #0f172a;
  font-size: 12px;
  font-weight: 700;
}

.docker-context-desc,
.docker-nav-desc {
  color: #64748b;
  font-size: 11px;
  line-height: 1.5;
}

.docker-context-items {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.docker-page-shell .workbench-card {
  min-width: 0;
}

.docker-host-card,
.docker-resource-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 12px;
}

.docker-page-shell .workbench-toolbar--history {
  margin-top: 0;
}

.docker-page-shell :deep(.section-toolbar) {
  padding-bottom: 2px;
}

.docker-page-shell :deep(.toolbar-title) {
  color: #0f172a;
}

.docker-page-shell :deep(.toolbar-desc) {
  color: #64748b;
}

.filter-bar--context {
  align-items: center;
}

.docker-context-toolbar-right {
  justify-content: flex-end;
  flex-wrap: nowrap;
  gap: 10px;
}

.docker-image-toolbar-right {
  flex-wrap: wrap;
}

.filter-inline-context {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex-wrap: nowrap;
  white-space: nowrap;
}

.filter-inline-label {
  flex: 0 0 auto;
  font-size: 12px;
  font-weight: 700;
  color: #64748b;
  line-height: 1;
  white-space: nowrap;
}

.filter-inline-select {
  width: 220px;
  min-width: 220px;
  flex: 0 0 220px;
}

.context-option-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  width: 100%;
  box-sizing: border-box;
}

.context-option-main {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  gap: 2px;
}

.context-option-head {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.context-option-main--host {
  flex-direction: row;
  align-items: center;
  gap: 8px;
}

.context-option-title {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}

.context-option-subtitle {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  color: #64748b;
}

.context-status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  min-width: 40px;
  height: 20px;
  padding: 0 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
  white-space: nowrap;
  border: 1px solid transparent;
  box-sizing: border-box;
}

.context-status-pill--success {
  color: #65a30d;
  background: #f0fdf4;
  border-color: #d9f99d;
}

.context-status-pill--info {
  color: #64748b;
  background: #f8fafc;
  border-color: #cbd5e1;
}

:deep(.docker-context-popper.el-select-dropdown),
:deep(.docker-context-popper.el-popper) {
  box-sizing: border-box;
  background: #ffffff !important;
  border-radius: 16px;
  border: 1px solid rgba(203, 213, 225, 0.72) !important;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.12) !important;
  overflow: hidden;
  backdrop-filter: blur(12px);
}

:deep(.docker-context-popper .el-popper__arrow::before) {
  border-color: rgba(203, 213, 225, 0.72) !important;
  background: #fff !important;
}

:deep(.docker-context-popper .el-scrollbar__view) {
  padding: 4px;
  background: #ffffff;
}

:deep(.docker-context-popper .el-select-dropdown__item) {
  min-height: 52px;
  height: auto;
  padding: 8px 10px;
  border-radius: 12px;
  color: #0f172a !important;
  font-family: inherit !important;
  white-space: normal !important;
  margin-bottom: 2px;
  background: transparent !important;
  transition: background-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
  box-sizing: border-box;
}

:deep(.docker-context-popper .el-select-dropdown__item.hover),
:deep(.docker-context-popper .el-select-dropdown__item:hover) {
  background: rgba(241, 245, 249, 0.92) !important;
  transform: translateY(-1px);
}

:deep(.docker-context-popper .el-select-dropdown__item.selected),
:deep(.docker-context-popper .el-select-dropdown__item.is-selected) {
  background: rgba(219, 234, 254, 0.92) !important;
  color: #1d4ed8 !important;
  box-shadow: inset 0 0 0 1px rgba(96, 165, 250, 0.3);
}

.docker-page-shell :deep(.el-table) {
  --el-table-border-color: rgba(15, 23, 42, 0.08);
  --el-table-header-bg-color: #f8fafc;
  --el-table-row-hover-bg-color: #f8fbff;
  border-radius: 14px;
  overflow: hidden;
}

.docker-page-shell :deep(.el-table th.el-table__cell) {
  height: 42px;
  padding: 0;
}

.docker-page-shell :deep(.el-table th.el-table__cell > .cell) {
  font-size: 12px;
  font-weight: 700;
  color: #64748b;
}

.docker-page-shell :deep(.el-table .el-table__cell) {
  padding: 10px 0;
}

.docker-resource-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.docker-resource-title {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.docker-resource-title span:last-child {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #0f172a;
  font-size: 12px;
  font-weight: 700;
}

.docker-resource-sub {
  color: #64748b;
  font-size: 11px;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.docker-resource-meta {
  color: #94a3b8;
  font-size: 11px;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.docker-inline-tag {
  border-radius: 999px;
  font-weight: 600;
}

.docker-row-action {
  margin-left: 0;
}

.docker-mono-id {
  font-family: 'Cascadia Code', 'Consolas', monospace;
  font-size: 12px;
  color: #64748b;
}

.docker-dialog-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.docker-dialog-header strong {
  color: #0f172a;
  font-size: 16px;
  line-height: 1.25;
}

.docker-dialog-header span:last-child {
  color: #64748b;
  font-size: 11px;
  line-height: 1.5;
}

.docker-dialog-header--compact strong {
  font-size: 15px;
}

.docker-dialog-eyebrow {
  color: #2563eb;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.docker-dialog-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.docker-console-log-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 0 10px;
}

.docker-console-log {
  margin: 0;
  padding: 12px 12px;
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.98) 0%, rgba(15, 23, 42, 0.94) 100%);
  color: #e2e8f0;
  font-family: 'Cascadia Code', 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.55;
  max-height: 64vh;
  overflow: auto;
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.1);
}

.docker-host-form :deep(.el-form-item) {
  margin-bottom: 10px;
}

.docker-host-form :deep(.el-form-item__label) {
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
}

.docker-page-shell :deep(.docker-console-dialog .el-dialog) {
  border-radius: 20px;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.14);
  box-shadow: 0 24px 72px rgba(15, 23, 42, 0.16);
}

.docker-page-shell :deep(.docker-console-dialog .el-dialog__header) {
  margin-right: 0;
  padding: 16px 18px 10px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 0.96) 100%);
}

.docker-page-shell :deep(.docker-console-dialog .el-dialog__body) {
  padding: 14px 16px 16px;
  background: #f8fafc;
}

.docker-page-shell :deep(.docker-console-dialog .el-dialog__footer) {
  padding: 10px 16px 16px;
  border-top: 1px solid rgba(148, 163, 184, 0.1);
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.94) 0%, rgba(255, 255, 255, 0.98) 100%);
}

.docker-host-table :deep(.el-table__header-wrapper th) {
  background: #f8fafc;
}

@media (max-width: 1200px) {
  .docker-context-toolbar-right {
    flex-wrap: wrap;
  }
}

@media (max-width: 900px) {
  .docker-hero,
  .docker-context-strip,
  .docker-nav-panel {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-inline-context {
    width: 100%;
    justify-content: space-between;
  }

  .filter-inline-select {
    flex: 1 1 auto;
    width: auto;
    min-width: 0;
  }

  .docker-main-tabs {
    grid-template-columns: 1fr;
  }
}
</style>
