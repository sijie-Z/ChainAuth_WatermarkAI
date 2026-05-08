<template>
  <div class="stat-card" :style="{ borderColor: color }">
    <div class="stat-icon" :style="{ background: color }">
      <el-icon :size="24"><component :is="icon" /></el-icon>
    </div>
    <div class="stat-content">
      <div class="stat-value">{{ value }}</div>
      <div class="stat-label">{{ label }}</div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  icon: { type: Object, required: true },
  value: { type: [Number, String], default: 0 },
  label: { type: String, default: '' },
  color: { type: String, default: '#409eff' }
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.stat-card {
  display: flex;
  align-items: center;
  padding: 20px;
  background: #fff;
  border-radius: $radius-lg;
  border-left: 4px solid;
  box-shadow: $shadow-card;
  transition: $transition-base;

  &:hover {
    box-shadow: $shadow-lg;
    transform: translateY(-2px);
  }
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: $radius-lg;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  margin-right: $spacing-md;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: $font-size-3xl;
  font-weight: $font-weight-bold;
  color: $text-primary;
}

.stat-label {
  font-size: $font-size-sm;
  color: $text-secondary;
  margin-top: $spacing-xs;
}
</style>
