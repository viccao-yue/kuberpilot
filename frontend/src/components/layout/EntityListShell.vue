<template>
  <div class="entity-shell fade-in workbench-page-shell">
    <section class="hero panel entity-hero">
      <div class="entity-hero-copy">
        <span v-if="eyebrow" class="entity-eyebrow">{{ eyebrow }}</span>
        <div class="entity-hero-title-row">
          <span v-if="$slots.icon" class="entity-hero-icon">
            <slot name="icon" />
          </span>
          <div class="entity-hero-title-block">
            <h2>{{ title }}</h2>
            <p v-if="description" class="entity-hero-desc">{{ description }}</p>
          </div>
        </div>
        <div v-if="$slots.meta" class="entity-hero-meta">
          <slot name="meta" />
        </div>
      </div>
      <div v-if="$slots.actions" class="hero-actions entity-hero-actions">
        <slot name="actions" />
      </div>
    </section>

    <slot name="stats" />
    <slot name="hint" />
    <slot name="tabs" />
    <slot />
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  description: { type: String, default: '' },
  eyebrow: { type: String, default: '' },
})
</script>

<style scoped>
.entity-shell {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.entity-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.entity-hero-copy {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}

.entity-eyebrow {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  min-height: 22px;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid var(--border-color);
  background: rgba(0, 0, 0, 0.02);
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.entity-hero-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.entity-hero-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.entity-hero-title-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.entity-hero-title-block h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 650;
  color: var(--text-primary);
}

.entity-hero-desc {
  margin: 0;
  font-size: 13px;
  line-height: 1.55;
  color: var(--text-secondary);
}

.entity-hero-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.entity-hero-actions {
  align-items: center;
}

@media (max-width: 900px) {
  .entity-hero {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>

