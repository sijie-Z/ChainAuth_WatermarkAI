<template>
  <div v-if="error" class="error-boundary">
    <div class="error-content">
      <el-icon :size="64" color="#a6402f"><WarningFilled /></el-icon>
      <h2>页面出现错误</h2>
      <p class="error-message">{{ error.message || '未知错误' }}</p>
      <div class="error-actions">
        <el-button type="primary" @click="retry">重试</el-button>
        <el-button @click="goHome">返回首页</el-button>
      </div>
    </div>
  </div>
  <slot v-else />
</template>

<script setup>
import { ref, onErrorCaptured } from 'vue'
import { useRouter } from 'vue-router'
import { WarningFilled } from '@element-plus/icons-vue'

const router = useRouter()
const error = ref(null)

onErrorCaptured((err, vm, info) => {
  error.value = err
  console.error('[ErrorBoundary]', err, info)
  return false // 阻止错误向上传播
})

function retry() {
  error.value = null
}

function goHome() {
  error.value = null
  router.push('/home')
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.error-boundary {
  min-height: 60vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.error-content {
  text-align: center;
  padding: $spacing-3xl;

  h2 {
    margin: $spacing-lg 0 $spacing-sm;
    color: $text-primary;
    font-size: $font-size-2xl;
  }

  .error-message {
    color: $text-secondary;
    margin-bottom: $spacing-xl;
  }
}
</style>
