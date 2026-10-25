<template>
  <div class="auth-page">
    <div class="auth-card">
      <router-link to="/home" class="auth-brand">
        <span class="brand-mark">园</span>
        <span>苏州园林数字资产</span>
      </router-link>
      <h1 class="auth-title">找回密码</h1>
      <p class="auth-desc">输入注册邮箱，我们会发送一条 30 分钟内有效的重置链接。</p>

      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="邮箱">
          <el-input
            v-model="email"
            placeholder="name@example.com"
            size="large"
            autocomplete="email"
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-button
          type="primary"
          size="large"
          class="auth-submit"
          :loading="loading"
          @click="submit"
        >{{ loading ? '发送中…' : '发送重置链接' }}</el-button>
      </el-form>

      <el-alert
        v-if="devToken"
        type="info"
        :closable="false"
        show-icon
        class="auth-alert"
      >
        开发环境未配置 SMTP，可直接
        <router-link :to="{ path: '/reset-password', query: { token: devToken } }">打开重置页</router-link>
      </el-alert>

      <p class="auth-links">
        <router-link to="/login">返回登录</router-link>
        <router-link to="/register">注册账号</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { authApi } from '@/api/modules'

const email = ref('')
const loading = ref(false)
const devToken = ref('')

async function submit() {
  if (!email.value.trim()) {
    ElMessage.warning('请输入邮箱')
    return
  }
  loading.value = true
  devToken.value = ''
  try {
    const response = await authApi.forgotPassword({ email: email.value.trim() })
    const data = response.data?.data || {}
    ElMessage.success(
      data.sent
        ? '重置链接已发送，请查收邮箱'
        : '如果该邮箱已注册，重置链接已发送'
    )
    if (data.dev_reset_url) {
      try {
        devToken.value = new URL(data.dev_reset_url).searchParams.get('token') || ''
      } catch {
        devToken.value = ''
      }
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '发送失败，请稍后重试')
  } finally {
    loading.value = false
  }
}
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

.auth-title {
  font-family: $font-display;
  font-size: 26px;
  color: $text-primary;
  margin-bottom: 8px;
}

.auth-desc {
  font-size: 13px;
  line-height: 1.8;
  color: $text-secondary;
  margin-bottom: $spacing-xl;
}

.auth-submit {
  width: 100%;
}

.auth-alert {
  margin-top: $spacing-lg;
}

.auth-links {
  display: flex;
  justify-content: space-between;
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
