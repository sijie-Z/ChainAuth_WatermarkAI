<template>
  <div class="register-page">
    <!-- 左侧：园林档案封面 -->
    <aside class="register-aside lattice-light">
      <router-link to="/home" class="aside-brand">
        <span class="brand-mark">园</span>
        <span class="brand-name">苏州园林数字资产</span>
      </router-link>

      <div class="aside-body">
        <p class="aside-label">建立你的档案身份</p>
        <h1 class="aside-title">一次注册，<br />全程留痕。</h1>
        <p class="aside-note">
          注册后可申请资产授权、查询溯源记录，
          并在个人中心管理自己的授权合同与下载记录。
        </p>
      </div>

      <svg class="aside-gate" viewBox="0 0 360 360" fill="none" aria-hidden="true">
        <defs>
          <clipPath id="registerGateClip">
            <circle cx="180" cy="180" r="126" />
          </clipPath>
        </defs>
        <circle cx="180" cy="180" r="152" stroke="rgba(252,253,251,.16)" />
        <circle cx="180" cy="180" r="140" stroke="rgba(252,253,251,.28)" stroke-width="1.5" />
        <circle cx="180" cy="180" r="126" fill="rgba(9,39,34,.75)" stroke="rgba(252,253,251,.4)" stroke-width="1.5" />
        <g clip-path="url(#registerGateClip)">
          <circle cx="240" cy="126" r="24" fill="rgba(252,253,251,.1)" />
          <path d="M36 218c44-30 82-30 124-8 36 19 66 18 102-4 34-20 60-18 96 4v160H36z" fill="#123a32" />
          <path d="M18 252c50-22 94-14 138 6 42 20 76 14 112-6 36-20 66-14 102 6v90H18z" fill="#0a2b25" />
          <path d="M104 206l40-30 40 30v6h-80z" fill="#08231f" />
          <path d="M118 214h52v46h-52z" fill="#08231f" />
          <path d="M132 230h12v30h-12zM152 230h12v30h-12z" fill="rgba(252,253,251,.08)" />
        </g>
        <circle cx="180" cy="180" r="158" stroke="rgba(252,253,251,.1)" stroke-dasharray="2 8" />
      </svg>

      <p class="aside-foot">苏州大学 · 挑战杯项目</p>
    </aside>

    <!-- 右侧：注册表单 -->
    <main class="register-main">
      <div class="register-wrapper">
        <div class="register-top">
          <router-link to="/home" class="back-link">
            <el-icon><ArrowLeft /></el-icon>
            返回首页
          </router-link>
        </div>

        <header class="register-header">
          <h2 class="register-title">创建账号</h2>
          <p class="register-desc">用于申请授权与查看资产流转记录。</p>
        </header>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
          class="register-form"
          @submit.prevent="handleRegister"
        >
          <el-form-item prop="username" label="用户名">
            <el-input v-model="form.username" placeholder="3-20 位，用于登录" size="large" autocomplete="username" />
          </el-form-item>

          <div class="form-grid">
            <el-form-item prop="email" label="邮箱">
              <el-input v-model="form.email" placeholder="name@example.com" size="large" autocomplete="email" />
            </el-form-item>
            <el-form-item prop="phone" label="手机号">
              <el-input v-model="form.phone" placeholder="选填" size="large" autocomplete="tel" />
            </el-form-item>
          </div>

          <div class="form-grid">
            <el-form-item prop="password" label="密码">
              <el-input v-model="form.password" type="password" placeholder="至少 6 位" size="large" show-password autocomplete="new-password" />
            </el-form-item>
            <el-form-item prop="confirmPassword" label="确认密码">
              <el-input v-model="form.confirmPassword" type="password" placeholder="再次输入" size="large" show-password autocomplete="new-password" />
            </el-form-item>
          </div>

          <p class="role-note">
            注册账号默认为普通用户。管理员角色由平台在后台分配。
          </p>

          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="register-btn"
            @click="handleRegister"
          >
            {{ loading ? '创建中…' : '创建账号' }}
          </el-button>
        </el-form>

        <p class="login-row">
          已有账号？
          <router-link to="/login">直接登录</router-link>
        </p>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()

const formRef = ref()
const loading = ref(false)

const form = ref({
  username: '',
  email: '',
  phone: '',
  password: '',
  confirmPassword: ''
})

const validatePass = (rule, value, callback) => {
  if (value !== form.value.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度 3-20 位', trigger: 'blur' }
  ],
  email: [
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 32, message: '密码长度 6-32 位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { validator: validatePass, trigger: 'blur' }
  ]
}

async function handleRegister() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true

  try {
    const result = await userStore.register({
      username: form.value.username,
      email: form.value.email || null,
      phone: form.value.phone || null,
      password: form.value.password
    })

    if (result.success) {
      ElMessage.success('注册成功，请登录')
      router.push('/login')
    } else {
      ElMessage.error(result.message)
    }
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.register-page {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
  min-height: 100vh;
  background: $bg-primary;
}

// ========== 左侧封面 ==========
.register-aside {
  position: relative;
  display: flex;
  flex-direction: column;
  padding: 40px 48px;
  background: $primary-dark;
  color: #fcfdfb;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    background: radial-gradient(circle at 30% 20%, rgba(91, 146, 127, 0.25) 0%, transparent 55%);
    pointer-events: none;
  }
}

.aside-brand {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  color: #fcfdfb;

  .brand-mark {
    width: 38px;
    height: 38px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: 1px solid rgba(252, 253, 251, 0.4);
    border-radius: $radius-xs;
    font-family: $font-display;
    font-size: 20px;
  }

  .brand-name {
    font-family: $font-display;
    font-size: 16px;
    letter-spacing: 0.06em;
  }
}

.aside-body {
  position: relative;
  margin-top: auto;
  margin-bottom: auto;
  max-width: 420px;
}

.aside-label {
  font-size: 12px;
  letter-spacing: 0.18em;
  color: rgba(252, 253, 251, 0.55);
  margin-bottom: 20px;
}

.aside-title {
  font-family: $font-display;
  font-size: clamp(36px, 4vw, 54px);
  font-weight: 600;
  line-height: 1.3;
  letter-spacing: 0.03em;
  color: #fcfdfb;
  margin-bottom: 20px;
}

.aside-note {
  font-size: 14px;
  line-height: 1.9;
  color: rgba(252, 253, 251, 0.66);
  max-width: 32em;
}

.aside-gate {
  position: absolute;
  right: -80px;
  bottom: -60px;
  width: 420px;
  height: 420px;
  opacity: 0.9;
  pointer-events: none;
}

.aside-foot {
  position: relative;
  font-size: 11px;
  letter-spacing: 0.16em;
  color: rgba(252, 253, 251, 0.4);
}

// ========== 右侧表单 ==========
.register-main {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
  background: $bg-primary;
}

.register-wrapper {
  width: 100%;
  max-width: 480px;
}

.register-top {
  margin-bottom: 32px;

  .back-link {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    color: $text-secondary;

    &:hover { color: $primary-dark; }
  }
}

.register-header {
  margin-bottom: 24px;

  .register-title {
    font-family: $font-display;
    font-size: 30px;
    font-weight: 600;
    color: $text-primary;
    margin-bottom: 8px;
  }

  .register-desc {
    font-size: 14px;
    color: $text-secondary;
  }
}

.register-form {
  :deep(.el-form-item__label) {
    font-size: 13px;
    color: $text-secondary;
    padding-bottom: 6px;
  }

  :deep(.el-input__wrapper) {
    height: 44px;
    padding: 0 12px;
    background: $bg-card;
  }

  :deep(.el-form-item) {
    margin-bottom: 18px;
  }
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.role-note {
  font-size: 12px;
  line-height: 1.7;
  color: $text-placeholder;
  margin: 4px 0 20px;
  padding-left: 10px;
  border-left: 2px solid $border-color;
}

.register-btn {
  width: 100%;
  height: 46px;
  font-size: 15px;
  letter-spacing: 0.12em;
}

.login-row {
  margin-top: 22px;
  font-size: 13px;
  color: $text-secondary;
  text-align: center;

  a {
    color: $primary-color;
    margin-left: 4px;

    &:hover { text-decoration: underline; }
  }
}

// ========== 响应式 ==========
@media (max-width: 992px) {
  .register-page {
    grid-template-columns: 1fr;
  }

  .register-aside {
    padding: 28px 24px;
    min-height: 240px;
  }

  .aside-body {
    margin: 28px 0 8px;
  }

  .aside-title {
    font-size: 32px;
    br { display: none; }
  }

  .aside-gate {
    width: 240px;
    height: 240px;
    right: -60px;
    bottom: -80px;
  }

  .aside-foot { display: none; }

  .register-main { padding: 32px 20px 48px; }
}

@media (max-width: 560px) {
  .form-grid { grid-template-columns: 1fr; gap: 0; }
}
</style>
