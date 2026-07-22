<template>
  <div class="neo-tabs theme-blue log-center-tabs trace-center-tabs event-tabs-shell">
    <button
      v-for="item in tabs"
      :key="item.path"
      type="button"
      class="neo-tab-btn event-tab"
      :class="{ active: route.path === item.path }"
      @click="go(item.path)"
    >
      <el-icon style="margin-right:4px;"><component :is="item.icon" /></el-icon>
      {{ item.title }}
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Aim, CollectionTag, Share } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const tabs = computed(() => [
  { path: '/events/wall', title: '事件中心', icon: Aim, permission: 'eventwall.view' },
  { path: '/events/environments', title: '事件环境', icon: CollectionTag, permission: 'eventwall.environment.view' },
  { path: '/events/sources', title: '事件源', icon: Share, permission: 'eventwall.source.view' },
].filter(item => authStore.hasPermission(item.permission)))

function go(path) {
  if (route.path !== path) {
    router.push({ path, query: { ...route.query } })
  }
}
</script>

<style scoped>
.event-tabs-shell {
  display: flex;
  width: 100%;
  padding: 3px;
  border: 1px solid var(--border-color);
  border-radius: var(--card-radius, 6px);
  background: var(--card-bg);
  box-shadow: none;
}

.event-tab {
  min-height: 36px;
  padding: 0 16px;
  border: 0;
  border-radius: 3px;
  background: transparent;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  line-height: 1.2;
}

.event-tab:hover {
  background: var(--sidebar-hover);
}

.event-tab.active {
  background: var(--sidebar-active);
  color: var(--primary);
  box-shadow: inset 0 0 0 1px rgba(0, 82, 217, 0.16);
}

@media (max-width: 700px) {
  .event-tabs-shell {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .event-tab {
    min-width: 0;
  }
}
</style>
