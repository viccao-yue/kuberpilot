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
