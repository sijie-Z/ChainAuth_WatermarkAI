<template>
  <div class="not-found-page">
    <div class="not-found-content">
      <div class="error-code">
        <span class="digit">4</span>
        <div class="icon-wrapper">
          <svg viewBox="0 0 80 80" fill="none" class="error-icon">
            <circle cx="40" cy="40" r="36" stroke="currentColor" stroke-width="3" fill="none" opacity="0.2"/>
            <path d="M28 28L52 52M52 28L28 52" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
          </svg>
        </div>
        <span class="digit">4</span>
      </div>

      <h1 class="error-title">页面未找到</h1>
      <p class="error-desc">您访问的页面不存在或已被移除，请检查链接是否正确</p>

      <div class="action-buttons">
        <el-button type="primary" size="large" @click="$router.push('/home')">
          <el-icon><HomeFilled /></el-icon>
          返回首页
        </el-button>
        <el-button size="large" @click="$router.back()">
          <el-icon><ArrowLeft /></el-icon>
          返回上页
        </el-button>
      </div>
    </div>

    <!-- 背景装饰 -->
    <div class="bg-decoration">
      <div class="circle c1"></div>
      <div class="circle c2"></div>
      <div class="circle c3"></div>
    </div>
  </div>
</template>

<script setup>
import { HomeFilled, ArrowLeft } from '@element-plus/icons-vue'
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.not-found-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: $bg-primary;
  position: relative;
  overflow: hidden;
}

.not-found-content {
  text-align: center;
  z-index: 1;
  padding: 40px;
}

.error-code {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 24px;

  .digit {
    font-size: 120px;
    font-weight: $font-weight-bold;
    background: $primary-gradient;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1;
  }

  .icon-wrapper {
    width: 100px;
    height: 100px;
    color: $primary-color;
  }

  .error-icon {
    width: 100%;
    height: 100%;
    animation: pulse 2s ease-in-out infinite;
  }
}

.error-title {
  font-size: $font-size-3xl;
  font-weight: $font-weight-semibold;
  color: $text-primary;
  margin: 0 0 12px;
}

.error-desc {
  font-size: $font-size-base;
  color: $text-secondary;
  margin: 0 0 32px;
  max-width: 400px;
  margin-left: auto;
  margin-right: auto;
}

.action-buttons {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.bg-decoration {
  position: absolute;
  inset: 0;
  pointer-events: none;

  .circle {
    position: absolute;
    border-radius: 50%;
    opacity: 0.08;

    &.c1 {
      width: 500px;
      height: 500px;
      background: $primary-color;
      top: -150px;
      right: -100px;
      animation: float 8s ease-in-out infinite;
    }

    &.c2 {
      width: 300px;
      height: 300px;
      background: $secondary-color;
      bottom: -50px;
      left: -50px;
      animation: float 6s ease-in-out infinite reverse;
    }

    &.c3 {
      width: 200px;
      height: 200px;
      background: $accent-color;
      top: 50%;
      left: 10%;
      animation: float 10s ease-in-out infinite;
    }
  }
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.05); opacity: 0.8; }
}

@keyframes float {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  50% { transform: translateY(30px) rotate(5deg); }
}

@media (max-width: $breakpoint-sm) {
  .error-code .digit {
    font-size: 80px;
  }

  .error-code .icon-wrapper {
    width: 70px;
    height: 70px;
  }

  .error-title {
    font-size: $font-size-xl;
  }
}
</style>
