import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import zhCn from 'element-plus/es/locale/lang/zh-cn'

import App from './App.vue'
import router from './router'
import './assets/main.css'
import './assets/coreui-theme.css'
import './assets/cloud-theme.css'
import './assets/tdesign-theme.css'
import { pinia } from './stores'
import { useAuthStore } from './stores/auth'

function migrateLegacyStorage(storage) {
  const pairs = [
    ['sxdevops_token', 'kuberPilot_token'],
    ['sxdevops_user', 'kuberPilot_user'],
    ['sxdevops_workorder_flow_types', 'kuberPilot_workorder_flow_types'],
    ['sxdevops_preview_mode', 'kuberPilot_preview_mode'],
    ['sxdevops_preview_knowledge_envs_v1', 'kuberPilot_preview_knowledge_envs_v1'],
    ['sxdevops.task-center.prefill-draft', 'kuberPilot.task-center.prefill-draft'],
    ['sxdevops_aiops_current_session', 'kuberPilot_aiops_current_session'],
    ['sxdevops_aiops_visible', 'kuberPilot_aiops_visible'],
    ['sxdevops_aiops_analysis_only', 'kuberPilot_aiops_analysis_only'],
  ]
  pairs.forEach(([oldKey, newKey]) => {
    const legacy = storage.getItem(oldKey)
    if (legacy != null && storage.getItem(newKey) == null) storage.setItem(newKey, legacy)
  })
  const legacyDrafts = []
  for (let index = 0; index < storage.length; index += 1) {
    const key = storage.key(index)
    if (key && key.startsWith('sxdevops_aiops_draft_')) legacyDrafts.push(key)
  }
  legacyDrafts.forEach((key) => {
    const newKey = `kuberPilot_aiops_draft_${key.slice('sxdevops_aiops_draft_'.length)}`
    const legacy = storage.getItem(key)
    if (legacy != null && storage.getItem(newKey) == null) storage.setItem(newKey, legacy)
  })
}

migrateLegacyStorage(window.localStorage)
migrateLegacyStorage(window.sessionStorage)

const savedTheme = window.localStorage.getItem('kp-theme')
document.documentElement.dataset.theme = savedTheme || 'tdesign'

const app = createApp(App)

app.use(pinia)
app.use(router)
app.use(ElementPlus, { locale: zhCn })

// 注册所有图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component)
}

const authStore = useAuthStore(pinia)

router.afterEach((to) => {
    const title = typeof to.meta?.title === 'string' && to.meta.title.trim()
        ? `${to.meta.title} - KuberPilot`
        : 'KuberPilot 运维智能体平台'
    document.title = title
})

authStore.bootstrap().finally(() => {
    app.mount('#app')
})
