<template>
  <div class="error-page">
    <main class="error-content">
      <p class="error-code" aria-hidden="true">403</p>
      <h1 class="error-title">权限不足</h1>
      <p class="error-desc">抱歉，您没有访问该页面的权限。如需访问，请联系管理员，或返回首页继续浏览。</p>
      <div class="error-actions">
        <el-button type="primary" @click="goHome">返回首页</el-button>
        <router-link to="/assets" class="error-link">浏览资产档案</router-link>
      </div>
    </main>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

function goHome() {
  router.push('/home')
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.error-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  background: $bg-card;
  text-align: center;
}

.error-content {
  max-width: 460px;
}

.error-code {
  margin: 0 0 20px;
  font-family: $font-display;
  font-size: clamp(72px, 16vw, 112px);
  font-weight: 600;
  line-height: 1;
  letter-spacing: 0.08em;
  color: $primary-dark;
}

.error-title {
  margin: 0 0 12px;
  font-family: $font-display;
  font-size: 24px;
  font-weight: 600;
  color: $text-primary;
}

.error-desc {
  margin: 0 auto 32px;
  max-width: 34em;
  font-size: 14px;
  line-height: 1.8;
  color: $text-secondary;
}

.error-actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
}

.error-link {
  padding-bottom: 1px;
  border-bottom: 1px solid transparent;
  font-size: 13px;
  color: $text-secondary;
  transition: color 0.15s ease, border-color 0.15s ease;

  &:hover {
    color: $primary-dark;
    border-bottom-color: $border-color;
  }
}

@media (max-width: 480px) {
  .error-page {
    padding: 32px 20px;
  }

  .error-title {
    font-size: 20px;
  }
}
</style>
