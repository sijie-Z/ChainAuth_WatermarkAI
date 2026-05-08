<template>
  <div class="error-page">
    <div class="error-content">
      <div class="error-code">403</div>
      <h2>权限不足</h2>
      <p>抱歉，您没有访问该页面的权限。</p>
      <div class="error-actions">
        <el-button type="primary" @click="goHome">返回首页</el-button>
        <el-button @click="goBack">返回上页</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

function goHome() {
  router.push('/home')
}

function goBack() {
  router.back()
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.error-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: $bg-primary;
}

.error-content {
  text-align: center;
  padding: $spacing-3xl;
}

.error-code {
  font-size: 120px;
  font-weight: $font-weight-bold;
  background: $primary-gradient;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  line-height: 1;
  margin-bottom: $spacing-lg;
}

h2 {
  font-size: $font-size-2xl;
  color: $text-primary;
  margin-bottom: $spacing-sm;
}

p {
  color: $text-secondary;
  margin-bottom: $spacing-xl;
}

.error-actions {
  display: flex;
  gap: $spacing-sm;
  justify-content: center;
}
</style>
