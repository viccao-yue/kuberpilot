<template>
  <div class="forbidden-page workbench-page-shell">
    <section class="hero panel forbidden-hero">
      <div class="forbidden-hero-copy">
        <div class="forbidden-title-row">
          <span class="forbidden-icon">403</span>
          <h2>无权访问</h2>
          <p class="forbidden-subtitle">当前账号没有访问该页面的权限，请联系管理员分配对应角色、用户组或模块访问范围。</p>
        </div>
      </div>
      <div class="hero-actions">
        <el-button @click="$router.back()">返回上一页</el-button>
        <el-button type="primary" @click="$router.push('/dashboard')">回到首页</el-button>
      </div>
    </section>

    <div class="stats-grid forbidden-stats">
      <div class="stat-card release-stat-card">
        <div class="stat-value">权限不足</div>
        <div class="stat-label">当前状态</div>
        <div class="release-stat-desc">账号暂未获得此页面或模块的访问权限</div>
      </div>
      <div class="stat-card release-stat-card">
        <div class="stat-value">角色 / 用户组</div>
        <div class="stat-label">建议排查</div>
        <div class="release-stat-desc">优先检查角色绑定、用户组授权与菜单模块设置</div>
      </div>
      <div class="stat-card release-stat-card">
        <div class="stat-value">返回控制台</div>
        <div class="stat-label">快速处理</div>
        <div class="release-stat-desc">可先回到首页或上一页继续处理其它可访问模块</div>
      </div>
    </div>

    <section class="workbench-inline-tip--panel forbidden-tip">
      <div class="tip-panel-head">
        <strong>权限处理建议</strong>
        <span>如果你原本预期能访问这里，优先确认账号角色、用户组授权和模块显示配置是否一致，再由管理员补齐对应权限。</span>
      </div>
      <div class="tip-panel-list">
        <div class="tip-panel-item">检查是否已分配目标模块对应的 RBAC 权限。</div>
        <div class="tip-panel-item">检查模块是否被导航配置隐藏，导致入口和权限状态不一致。</div>
        <div class="tip-panel-item">如为新接入账号，建议刷新权限后重新进入对应页面。</div>
        <div class="tip-panel-item">如仍无权限，请联系管理员补齐角色或用户组授权。</div>
      </div>
    </section>

    <div class="workbench-card forbidden-card">
      <div class="forbidden-card-head">
        <strong>为什么会看到这个页面</strong>
        <span>系统检测到当前会话未满足页面访问要求，因此阻止继续进入，避免在无权限场景下暴露敏感操作入口。</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.forbidden-page {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.forbidden-card {
  min-height: 112px;
}

.forbidden-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.forbidden-title-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.forbidden-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(249, 115, 22, 0.12);
  color: #c2410c;
  font-size: 14px;
  font-weight: 800;
}

.forbidden-page h2 {
  margin: 0;
  color: #0f172a;
  font-size: 23px;
}

.forbidden-subtitle,
.forbidden-card-head span {
  margin: 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.6;
}

.hero-actions {
  display: flex;
  gap: 12px;
}

.forbidden-stats {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.forbidden-tip {
  margin-top: -2px;
}

.forbidden-card-head {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

@media (max-width: 760px) {
  .forbidden-hero {
    align-items: flex-start;
    flex-direction: column;
  }

  .forbidden-stats {
    grid-template-columns: 1fr;
  }
}
</style>
