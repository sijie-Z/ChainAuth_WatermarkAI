<template>
  <router-view v-slot="{ Component, route }">
    <transition name="fade-slide" mode="out-in">
      <component :is="Component" :key="route.path" />
    </transition>
  </router-view>
</template>

<script setup>
import { onMounted } from 'vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

onMounted(() => {
  // 初始化用户状态
  userStore.initStore()
})
</script>

<style lang="scss">
@use '@/assets/styles/variables.scss' as *;

// 全局重置
*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html {
  font-size: 16px;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  scroll-behavior: smooth;
}

body {
  font-family: $font-family;
  font-size: $font-size-base;
  line-height: $line-height-normal;
  color: $text-primary;
  background-color: $bg-primary;
  min-height: 100vh;
}

#app {
  width: 100%;
  min-height: 100vh;
}

// 滚动条美化
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: $border-dark;
  border-radius: $radius-full;

  &:hover {
    background: $text-placeholder;
  }
}

// 选中文本
::selection {
  background-color: rgba($primary-color, 0.2);
  color: $text-primary;
}

// 链接
a {
  color: $primary-color;
  text-decoration: none;
  transition: color $transition-fast;

  &:hover {
    color: $primary-dark;
  }
}

// 图片
img {
  max-width: 100%;
  height: auto;
  vertical-align: middle;
}

// 页面过渡动画
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.3s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

// 工具类
.text-center { text-align: center; }
.text-left { text-align: left; }
.text-right { text-align: right; }

.text-truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.flex { display: flex; }
.flex-1 { flex: 1; }
.items-center { align-items: center; }
.justify-center { justify-content: center; }
.justify-between { justify-content: space-between; }
.gap-1 { gap: 4px; }
.gap-2 { gap: 8px; }
.gap-3 { gap: 12px; }
.gap-4 { gap: 16px; }

.mt-1 { margin-top: 4px; }
.mt-2 { margin-top: 8px; }
.mt-3 { margin-top: 12px; }
.mt-4 { margin-top: 16px; }
.mb-1 { margin-bottom: 4px; }
.mb-2 { margin-bottom: 8px; }
.mb-3 { margin-bottom: 12px; }
.mb-4 { margin-bottom: 16px; }

.p-1 { padding: 4px; }
.p-2 { padding: 8px; }
.p-3 { padding: 12px; }
.p-4 { padding: 16px; }

.w-full { width: 100%; }
.h-full { height: 100%; }

// Element Plus 全局覆盖
.el-button--primary {
  background: $primary-gradient !important;
  border: none !important;

  &:hover {
    opacity: 0.9;
  }
}

.el-card {
  border-radius: $radius-xl !important;
  border: 1px solid $border-light !important;
  box-shadow: $shadow-card !important;
}

.el-input__wrapper {
  border-radius: $radius-lg !important;
  box-shadow: none !important;
  border: 1px solid $border-color !important;

  &:hover, &:focus-within {
    border-color: $primary-color !important;
    box-shadow: 0 0 0 3px rgba($primary-color, 0.1) !important;
  }
}

.el-table {
  border-radius: $radius-xl !important;
  overflow: hidden;

  th.el-table__cell {
    background: $bg-secondary !important;
    font-weight: $font-weight-medium !important;
    color: $text-secondary !important;
  }

  td.el-table__cell {
    border-bottom: 1px solid $border-light !important;
  }

  .el-table__row:hover td {
    background: $bg-hover !important;
  }
}

.el-tag {
  border-radius: $radius-full !important;
  border: none !important;
  padding: 2px 12px !important;
}

.el-dialog {
  border-radius: $radius-2xl !important;
  overflow: hidden;

  .el-dialog__header {
    padding: $spacing-2xl $spacing-3xl;
    border-bottom: 1px solid $border-light;
  }

  .el-dialog__body {
    padding: $spacing-3xl;
  }
}

.el-message-box {
  border-radius: $radius-xl !important;
}

.el-notification {
  border-radius: $radius-lg !important;
  border-left: 4px solid $primary-color !important;
}
</style>
