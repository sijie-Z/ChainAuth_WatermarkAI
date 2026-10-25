<template>
  <div class="auth-page">
    <div class="auth-card">
      <router-link to="/home" class="auth-brand">
        <span class="brand-mark">园</span>
        <span>苏州园林数字资产</span>
      </router-link>
      <h1 class="auth-title">设置新密码</h1>
      <p class="auth-desc">重置链接仅可使用一次；新密码至少 6 位。</p>

      <el-alert
        v-if="!token"
        type="warning"
        :closable="false"
        show-icon
        class="auth-alert"
      >
        缺少重置凭证，请重新
        <router-link to="/forgot-password">申请重置链接</router-link>。
      </el-alert>

      <el-form v-else label-position="top" @submit.prevent="submit">
        <el-form-item label="新密码">
          <el-input
            v-model="password"
            type="password"
            placeholder="至少 6 位"
            size="large"
            show-password
            autocomplete="new-password"
          />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input
            v-model="confirm"
            type="password"
            placeholder="再次输入新密码"
            size="large"
            show-password
            autocomplete="new-password"
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-button
          type="primary"
          size="large"
          class="auth-submit"
          :loading="loading"
          @click="submit"
        >{{ loading ? '提交中…' : '重置密码' }}</el-button>
      </el-form>

      <p class="auth-links">
        <router-link to="/login">返回登录</router-link>
        <router-link to="/forgot-password">重新申请链接</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authApi } from '@/api/modules'

const route = useRoute()
const router = useRouter()
const token = computed(() => String(route.query.token || ''))
const password = ref('')
const confirm = ref('')
const loading = ref(false)

async function submit() {
  if (!token.value) return
  if (password.value.length < 6) {
    ElMessage.warning('新密码至少 6 位')
    return
  }
  if (password.value !== confirm.value) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }
  loading.value = true
  try {
    const response = await authApi.resetPassword({
      token: token.value,
      new_password: password.value
    })
    if (response.data?.code === 200) {
      ElMessage.success('密码已重置，请使用新密码登录')
      router.push('/login')
    } else {
      ElMessage.error(response.data?.message || '重置失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '重置链接已过期或无效')
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
  margin-bottom: $spacing-lg;
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
