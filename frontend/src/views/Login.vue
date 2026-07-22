<template>
  <div class="auth-page">
    <main class="auth-shell">
      <section class="auth-overview">
        <header class="brand-row">
          <div class="brand-identity">
            <img src="@/assets/brand-mark.svg" alt="KuberPilot" class="brand-mark-image" />
            <div class="brand-copy">
              <strong>KuberPilot · AI Agent</strong>
              <span class="brand-motto">
                <span>思而后行</span>
                <el-icon class="brand-motto-icon"><TrendCharts /></el-icon>
                <span>行必有证</span>
              </span>
            </div>
          </div>
          <router-link class="promo-link" to="/ai-agent-promo">
            查看产品介绍
            <el-icon><ArrowRight /></el-icon>
          </router-link>
        </header>

        <div class="overview-content">
          <h1>统一运维智能体平台，让协作闭环更高效</h1>
          <p class="overview-summary">
            面向产研团队的统一入口，围绕可观测性、事件中心、任务中心和 AIOps 等，沉淀从发现异常到闭环复盘的完整链路。
          </p>

          <div class="capability-list">
            <article
              v-for="item in features"
              :key="item.title"
              class="capability-card"
              :class="item.tone"
            >
              <div class="capability-icon">
                <el-icon><component :is="item.icon" /></el-icon>
              </div>
              <div class="capability-body">
                <div class="capability-title">{{ item.title }}</div>
                <div class="capability-desc">{{ item.desc }}</div>
              </div>
            </article>
          </div>

          <div class="ops-flow" aria-label="协作链路">
            <span class="flow-label">协作链路</span>
            <div class="flow-steps">
              <span v-for="step in flowSteps" :key="step">
                <i></i>
                <strong>{{ step }}</strong>
              </span>
            </div>
          </div>
        </div>
      </section>

      <section class="auth-panel">
        <div class="auth-panel-inner">
          <h2>登录平台</h2>
          <p class="auth-subtitle">使用平台账号进入 KuberPilot</p>

          <el-form class="login-form" :model="form" label-position="top" @submit.prevent="handleLogin">
            <el-form-item label="用户名">
              <el-input
                v-model.trim="form.username"
                :prefix-icon="User"
                autocomplete="username"
                size="large"
                placeholder="请输入用户名"
              />
            </el-form-item>
            <el-form-item label="密码">
              <el-input
                v-model="form.password"
                :prefix-icon="Lock"
                autocomplete="current-password"
                size="large"
                type="password"
                show-password
                placeholder="请输入密码"
                @keyup.enter="handleLogin"
              />
            </el-form-item>
            <el-button
              type="primary"
              native-type="submit"
              size="large"
              class="submit-btn"
              :loading="loading"
            >
              进入工作台
            </el-button>
          </el-form>
          <div class="default-auth-tip">默认账号：admin / Admin@123456</div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowRight,
  Bell,
  Lock,
  Service,
  Tickets,
  TrendCharts,
  User,
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const form = reactive({
  username: 'admin',
  password: 'Admin@123456',
})

const features = [
  {
    title: 'AIOps',
    desc: '串联观测、事件与资源上下文，辅助根因分析、处置建议和审计复盘。',
    icon: Service,
    tone: 'aiops-card',
  },
  {
    title: '可观测性',
    desc: '统计系统SLA，统一查看指标、日志、链路与告警，快速定位异常和性能瓶颈。',
    icon: TrendCharts,
    tone: 'observability-card',
  },
  {
    title: '事件中心',
    desc: '收敛应用发布、运维事务、任务调度等事件，支撑影响分析与跟踪，辅助AI分析。',
    icon: Bell,
    tone: 'event-card',
  },
  {
    title: '任务中心',
    desc: '集中管理任务，生成 AIOps 待执行项，形成可追踪、可审计的执行闭环。',
    icon: Tickets,
    tone: 'task-card',
  },
]

const flowSteps = ['看态势', '找证据', '问系统', '确认动作']

async function handleLogin() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }

  loading.value = true
  try {
    await authStore.login(form)
    ElMessage.success('登录成功')
    try {
      await router.replace('/dashboard')
    } catch (error) {
      ElMessage.error('进入工作台失败，请刷新后重试')
    }
  } catch (error) {
    const status = error?.response?.status
    const detail = error?.response?.data?.detail || error?.response?.data?.message || error?.message
    const suffix = status ? `（HTTP ${status}）` : ''
    ElMessage.error(detail ? `登录失败${suffix}：${detail}` : `登录失败${suffix}，请稍后重试`)
  } finally {
    loading.value = false
  }
}
</script>
<style scoped>
.auth-page {
  --auth-scale: 1;
  height: 100vh;
  height: 100dvh;
  display: grid;
  place-items: center;
  padding: 18px;
  overflow: hidden;
  background:
    radial-gradient(circle at 14% 18%, rgba(37, 99, 235, 0.10), transparent 56%),
    radial-gradient(circle at 84% 24%, rgba(37, 99, 235, 0.06), transparent 52%),
    linear-gradient(90deg, rgba(0, 0, 0, 0.035) 1px, transparent 1px),
    linear-gradient(180deg, rgba(0, 0, 0, 0.03) 1px, transparent 1px),
    var(--content-bg);
  background-size: auto, auto, 44px 44px, 44px 44px, auto;
}

.auth-shell {
  width: min(1160px, 100%);
  height: min(680px, calc(100vh - 36px));
  height: min(680px, calc(100dvh - 36px));
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  overflow: hidden;
  border: 1px solid var(--border-color);
  border-radius: 18px;
  background: var(--card-bg);
  box-shadow: 0 18px 52px rgba(0, 0, 0, 0.10);
  backdrop-filter: blur(10px);
  transform: scale(var(--auth-scale));
  transform-origin: center;
}

.auth-overview {
  position: relative;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  padding: 32px 38px;
  background: rgba(0, 0, 0, 0.01);
}

.auth-overview::after {
  content: '';
  position: absolute;
  top: 30px;
  right: 0;
  bottom: 30px;
  width: 1px;
  background: linear-gradient(180deg, transparent, rgba(0, 0, 0, 0.12), transparent);
}

.brand-row,
.brand-identity,
.promo-link,
.capability-card,
.ops-flow,
.auth-panel {
  display: flex;
  align-items: center;
}

.brand-row {
  justify-content: space-between;
  gap: 18px;
  flex: 0 0 auto;
}

.brand-identity {
  gap: 12px;
  min-width: 0;
}

.brand-mark-image {
  width: 48px;
  height: 48px;
  display: block;
  flex: 0 0 auto;
}

.brand-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.brand-copy strong {
  display: inline-block;
  font-size: 20px;
  font-weight: 600;
  line-height: 1.1;
  color: var(--text-primary);
  white-space: nowrap;
}

.brand-motto {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
  line-height: 1.2;
}

.brand-motto-icon {
  font-size: 11px;
  color: var(--primary, #2563eb);
  opacity: 0.9;
}

.promo-link {
  flex: 0 0 auto;
  justify-content: center;
  gap: 7px;
  min-height: 36px;
  padding: 0 15px;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.02);
  color: var(--primary, #2563eb);
  font-size: 12px;
  font-weight: 600;
  text-decoration: none;
  box-shadow: none;
  transition: border-color 0.18s ease, background 0.18s ease;
}

.promo-link:hover {
  border-color: var(--border-color-strong);
  background: rgba(0, 0, 0, 0.03);
}

.overview-content {
  width: min(610px, 100%);
  margin: auto 0;
  padding: 18px 0 8px;
}

.auth-overview h1 {
  margin: 0;
  color: var(--text-primary);
  font-size: clamp(30px, 3.2vw, 38px);
  font-weight: 650;
  line-height: 1.22;
  letter-spacing: 0;
}

.overview-summary {
  max-width: 560px;
  margin: 14px 0 0;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.8;
}

.capability-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 26px;
}

.capability-card {
  min-height: 88px;
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--border-color, rgba(148, 163, 184, 0.16));
  border-radius: 14px;
  background: var(--card-bg);
  box-shadow: none;
}

.capability-icon {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  flex: 0 0 38px;
  border-radius: 12px;
  background: rgba(37, 99, 235, 0.18);
  color: var(--primary, #2563eb);
  font-size: 18px;
}

.aiops-card .capability-icon {
  background: rgba(37, 99, 235, 0.18);
  color: var(--primary, #2563eb);
}

.observability-card .capability-icon {
  background: rgba(37, 99, 235, 0.18);
  color: var(--primary, #2563eb);
}

.event-card .capability-icon {
  background: rgba(245, 158, 11, 0.13);
  color: rgba(245, 158, 11, 0.92);
}

.task-card .capability-icon {
  background: rgba(47, 181, 158, 0.13);
  color: rgba(16, 185, 129, 0.92);
}

.capability-body {
  min-width: 0;
}

.capability-title {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 600;
  line-height: 1.35;
}

.capability-desc {
  margin-top: 5px;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.55;
}

.ops-flow {
  gap: 12px;
  margin-top: 16px;
  padding: 9px 12px;
  border: 1px solid var(--border-color, rgba(148, 163, 184, 0.16));
  border-radius: 999px;
  background: var(--card-bg);
}

.flow-label {
  flex: 0 0 auto;
  padding-right: 12px;
  border-right: 1px solid var(--border-color);
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 700;
  line-height: 1.2;
  white-space: nowrap;
}

.flow-steps {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
}

.flow-steps span {
  position: relative;
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
  color: var(--text-secondary);
}

.flow-steps span + span::before {
  content: '';
  width: 14px;
  height: 1px;
  margin-right: 1px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.14);
}

.flow-steps i {
  width: 6px;
  height: 6px;
  flex: 0 0 6px;
  border-radius: 50%;
  background: rgba(42, 121, 190, 0.42);
  font-style: normal;
  box-shadow: 0 0 0 3px rgba(42, 121, 190, 0.06);
}

.flow-steps span:nth-child(2) i {
  background: rgba(47, 181, 158, 0.44);
  box-shadow: 0 0 0 3px rgba(47, 181, 158, 0.06);
}

.flow-steps span:nth-child(3) i {
  background: rgba(99, 102, 241, 0.4);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.06);
}

.flow-steps span:nth-child(4) i {
  background: rgba(245, 158, 11, 0.42);
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.06);
}

.flow-steps strong {
  min-width: 0;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.2;
  white-space: nowrap;
}

.auth-panel {
  justify-content: center;
  min-width: 0;
  padding: 42px;
  background: rgba(0, 0, 0, 0.01);
}

.auth-panel-inner {
  width: min(340px, 100%);
}

.auth-panel h2 {
  margin: 0;
  color: var(--text-primary);
  font-size: 34px;
  font-weight: 650;
  line-height: 1.18;
  letter-spacing: 0;
}

.auth-subtitle {
  margin: 10px 0 28px;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.7;
}

.login-form {
  width: 100%;
}

:deep(.el-form-item) {
  margin-bottom: 17px;
}

:deep(.el-form-item__label) {
  display: block;
  padding: 0 0 8px;
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 500;
  line-height: 1.4;
}

:deep(.el-input__wrapper) {
  min-height: 44px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 0 0 1px var(--border-color) inset;
  transition: box-shadow 0.18s ease, background 0.18s ease;
}

:deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--border-color-strong) inset;
}

:deep(.el-input__wrapper.is-focus) {
  background: rgba(255, 255, 255, 0.98);
  box-shadow:
    0 0 0 1px var(--primary, #2563eb) inset,
    0 0 0 4px rgba(37, 99, 235, 0.18);
}

:deep(.el-input__inner) {
  color: var(--text-primary);
  font-size: 14px;
}

:deep(.el-input__prefix) {
  color: var(--text-muted);
}

.submit-btn {
  width: 100%;
  height: 46px;
  margin-top: 4px;
  border: none;
  border-radius: 12px;
  background: var(--primary, #2563eb);
  box-shadow: none;
  font-size: 15px;
  font-weight: 600;
}

.submit-btn:hover,
.submit-btn:focus {
  background: var(--primary-dark, #1d4ed8);
  box-shadow: none;
}

.default-auth-tip {
  margin-top: 14px;
  color: var(--text-muted);
  font-size: 12px;
  text-align: center;
}

@media (min-width: 1440px) and (min-height: 840px) {
  .auth-page {
    --auth-scale: 1.08;
  }
}

@media (min-width: 1680px) and (min-height: 920px) {
  .auth-page {
    --auth-scale: 1.18;
  }
}

@media (min-width: 1920px) and (min-height: 1040px) {
  .auth-page {
    --auth-scale: 1.28;
  }
}

@media (min-width: 2240px) and (min-height: 1200px) {
  .auth-page {
    --auth-scale: 1.42;
  }
}

@media (min-width: 2560px) and (min-height: 1360px) {
  .auth-page {
    --auth-scale: 1.58;
  }
}

@media (min-width: 3200px) and (min-height: 1800px) {
  .auth-page {
    --auth-scale: 2;
  }
}

@media (max-height: 760px) and (min-width: 981px) {
  .auth-shell {
    height: calc(100vh - 28px);
    height: calc(100dvh - 28px);
  }

  .auth-overview {
    padding: 26px 34px;
  }

  .overview-content {
    padding-top: 8px;
  }

  .auth-overview h1 {
    font-size: 30px;
  }

  .overview-summary {
    line-height: 1.65;
  }

  .capability-list {
    gap: 10px;
    margin-top: 18px;
  }

  .capability-card {
    min-height: 78px;
    padding: 12px;
  }

  .ops-flow {
    margin-top: 14px;
  }

  .auth-panel {
    padding: 34px;
  }
}

@media (max-width: 980px) {
  .auth-page {
    height: auto;
    min-height: 100vh;
    min-height: 100dvh;
    overflow: auto;
  }

  .auth-shell {
    height: auto;
    min-height: auto;
    grid-template-columns: 1fr;
  }

  .auth-overview::after {
    display: none;
  }

  .overview-content {
    width: 100%;
    margin: 34px 0 0;
  }

  .auth-panel {
    padding: 34px 38px 40px;
  }
}

@media (max-width: 640px) {
  .auth-page {
    padding: 14px;
  }

  .auth-shell {
    border-radius: 20px;
  }

  .auth-overview,
  .auth-panel {
    padding: 24px;
  }

  .brand-row {
    align-items: flex-start;
    flex-direction: column;
    gap: 14px;
  }

  .auth-overview h1 {
    font-size: 26px;
  }

  .overview-summary {
    font-size: 13px;
    line-height: 1.65;
  }

  .capability-list {
    grid-template-columns: 1fr;
    margin-top: 20px;
  }

  .ops-flow {
    display: none;
  }

  .auth-panel h2 {
    font-size: 30px;
  }
}
</style>
