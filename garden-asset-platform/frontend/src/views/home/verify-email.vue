<template>
  <div class="auth-page">
    <div class="auth-card">
      <router-link to="/home" class="auth-brand">
        <span class="brand-mark">园</span>
        <span>苏州园林数字资产</span>
      </router-link>

      <div class="verify-status">
        <el-icon v-if="loading" class="is-loading" :size="42"><Loading /></el-icon>
        <el-icon v-else-if="success" class="ok" :size="42"><CircleCheck /></el-icon>
        <el-icon v-else class="fail" :size="42"><Warning /></el-icon>
        <h1 class="auth-title">{{ title }}</h1>
        <p class="auth-desc">{{ message }}</p>
      </div>

      <p class="auth-links">
        <router-link v-if="userStore.isLoggedIn" to="/settings">前往账号设置</router-link>
        <router-link to="/login">返回登录</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { CircleCheck, Loading, Warning } from '@element-plus/icons-vue'
import { authApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const userStore = useUserStore()
const loading = ref(true)
const success = ref(false)
const message = ref('正在验证邮箱…')

const title = computed(() => {
  if (loading.value) return '正在验证邮箱'
  return success.value ? '邮箱验证成功' : '验证链接无效'
})

onMounted(async () => {
  const token = String(route.query.token || '')
  if (!token) {
    loading.value = false
    message.value = '缺少验证凭证，请回到账号设置重新发送验证邮件。'
    return
  }
  try {
    const response = await authApi.verifyEmail({ token })
    if (response.data?.code === 200) {
      success.value = true
      message.value = '邮箱已与当前账号绑定，可以接收授权、任务与审批通知。'
      if (userStore.user) {
        userStore.setUser({ ...userStore.user, email_verified: true })
      }
    } else {
      message.value = response.data?.message || '验证失败，请重新发送验证邮件。'
    }
  } catch (error) {
    message.value = error.response?.data?.message || '验证链接已过期或无效。'
  } finally {
    loading.value = false
  }
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: $spacing-xl;
  background:
    radial-gradient(circle at 20% 10%, rgba(47, 107, 90, 0.12), transparent 42%),
    $bg-primary;
}

.auth-card {
  width: min(440px, 100%);
  padding: $spacing-3xl;
  border: 1px solid $border-color;
  border-radius: $radius-xl;
  background: $bg-card;
  box-shadow: $shadow-md;
}

.auth-brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: $text-primary;
  font-family: $font-display;
  font-size: 15px;
  margin-bottom: $spacing-xl;
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid $primary-color;
  border-radius: $radius-sm;
  color: $primary-color;
  font-weight: 600;
}

.verify-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 10px;
  padding: $spacing-lg 0;

  .ok {
    color: $success-color;
  }

  .fail {
    color: $error-color;
  }
}

.auth-title {
  font-family: $font-display;
  font-size: 24px;
  color: $text-primary;
}

.auth-desc {
  font-size: 13px;
  line-height: 1.8;
  color: $text-secondary;
}

.auth-links {
  display: flex;
  justify-content: center;
  gap: $spacing-xl;
  margin-top: $spacing-lg;
  font-size: 13px;

  a {
    color: $primary-dark;

    &:hover {
      text-decoration: underline;
    }
  }
}
</style>
