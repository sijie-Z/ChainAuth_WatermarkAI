<template>
  <div class="stat-card">
    <div class="stat-head">
      <span class="stat-icon">
        <el-icon><component :is="icon" /></el-icon>
      </span>
      <span class="stat-label">{{ label }}</span>
    </div>
    <div class="stat-value">{{ value }}</div>
  </div>
</template>

<script setup>
defineProps({
  icon: { type: Object, required: true },
  value: { type: [Number, String], default: 0 },
  label: { type: String, default: '' },
  color: { type: String, default: '' }
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.stat-card {
  padding: 20px;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
  box-shadow: $shadow-sm;
  transition: border-color $transition-fast;

  &:hover {
    border-color: $border-dark;
  }
}

.stat-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}

.stat-icon {
  width: 30px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid $border-color;
  border-radius: $radius-xs;
  background: $bg-secondary;
  color: $primary-dark;
  font-size: 16px;
}

.stat-label {
  font-size: 13px;
  color: $text-secondary;
}

.stat-value {
  font-family: $font-display;
  font-size: 30px;
  font-weight: 600;
  line-height: 1.1;
  color: $text-primary;
  font-variant-numeric: tabular-nums;
}
</style>
