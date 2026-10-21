<template>
  <div class="login-page">
    <!-- 左侧：园林档案封面 -->
    <aside class="login-aside lattice-light">
      <router-link to="/home" class="aside-brand">
        <span class="brand-mark">园</span>
        <span class="brand-name">苏州园林数字资产</span>
      </router-link>

      <div class="aside-body">
        <p class="aside-label">数字资产档案 · 链上确权</p>
        <h1 class="aside-title">一园一水，<br />皆有出处。</h1>
        <p class="aside-note">
          水印嵌入、区块链存证与 AI 溯源，
          让每一次下载、授权与流转都可核验。
        </p>
      </div>

      <div v-if="coverImage" class="aside-photo">
        <img :src="coverImage" alt="苏州园林实景" />
      </div>
      <svg v-else class="aside-gate" viewBox="0 0 360 360" fill="none" aria-hidden="true">
        <defs>
          <clipPath id="loginGateClip">
            <circle cx="180" cy="180" r="126" />
          </clipPath>
        </defs>
        <circle cx="180" cy="180" r="152" stroke="rgba(252,253,251,.16)" />
        <circle cx="180" cy="180" r="140" stroke="rgba(252,253,251,.28)" stroke-width="1.5" />
        <circle cx="180" cy="180" r="126" fill="rgba(9,39,34,.75)" stroke="rgba(252,253,251,.4)" stroke-width="1.5" />
        <g clip-path="url(#loginGateClip)">
          <circle cx="240" cy="126" r="24" fill="rgba(252,253,251,.1)" />
          <path d="M36 218c44-30 82-30 124-8 36 19 66 18 102-4 34-20 60-18 96 4v160H36z" fill="#123a32" />
          <path d="M18 252c50-22 94-14 138 6 42 20 76 14 112-6 36-20 66-14 102 6v90H18z" fill="#0a2b25" />
          <path d="M104 206l40-30 40 30v6h-80z" fill="#08231f" />
          <path d="M118 214h52v46h-52z" fill="#08231f" />
          <path d="M132 230h12v30h-12zM152 230h12v30h-12z" fill="rgba(252,253,251,.08)" />
        </g>
        <circle cx="180" cy="180" r="158" stroke="rgba(252,253,251,.1)" stroke-dasharray="2 8" />
      </svg>

      <p class="aside-foot">苏州大学 · 数字资产档案</p>
    </aside>

    <!-- 右侧：登录表单 -->
    <main class="login-main">
      <div class="login-wrapper">
        <div class="login-top">
          <router-link to="/home" class="back-link">
            <el-icon><ArrowLeft /></el-icon>
            返回首页
          </router-link>
        </div>

        <header class="login-header">
          <h2 class="login-title">登录档案系统</h2>
          <p class="login-desc">使用平台账号继续访问资产与授权记录。</p>
        </header>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
          class="login-form"
          @submit.prevent="handleLogin"
        >
          <el-form-item prop="username" label="用户名">
            <el-input
              v-model="form.username"
              placeholder="请输入用户名"
              size="large"
              autocomplete="username"
            />
          </el-form-item>

          <el-form-item prop="password" label="密码">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入密码"
              size="large"
              show-password
              autocomplete="current-password"
              @keyup.enter="handleLogin"
            />
          </el-form-item>

          <div class="form-row">
            <el-checkbox v-model="rememberMe">记住用户名</el-checkbox>
            <span class="form-hint">忘记密码请联系管理员</span>
          </div>

          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="login-btn"
            @click="handleLogin"
          >
            {{ loading ? '登录中…' : '登录' }}
          </el-button>
        </el-form>

        <p class="register-row">
          还没有账号？
          <router-link to="/register">申请注册</router-link>
        </p>

        <p class="guide-hint">
          <router-link to="/guide">第一次使用？查看 3 分钟使用指南 →</router-link>
        </p>

        <div v-if="showDemoAccounts" class="demo-block">
          <p class="demo-title">演示账号</p>
          <button
            v-for="account in demoAccounts"
            :key="account.username"
            type="button"
            class="demo-row"
            @click="fillDemo(account.username, account.password)"
          >
            <span class="demo-role">{{ account.role }}</span>
            <span class="demo-credential">{{ account.username }} / {{ account.password }}</span>
            <span class="demo-fill">填入</span>
          </button>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { publicApi } from '@/api/modules'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'

// 管理员角色集合，与后端角色枚举保持一致
const ADMIN_ROLES = ['admin', 'asset_admin', 'license_admin', 'adm1', 'adm2']
const REMEMBERED_USERNAME_KEY = 'rememberedUsername'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const showDemoAccounts = import.meta.env.DEV

const formRef = ref()
const loading = ref(false)
const rememberMe = ref(false)
const coverImage = ref('')

const form = ref({
  username: '',
  password: ''
})

const demoAccounts = [
  { role: '管理员', username: 'admin', password: 'admin123' },
  { role: '一级审批员', username: 'adm1', password: '123456' }
]

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度 3-20 位', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 32, message: '密码长度 6-32 位', trigger: 'blur' }
  ]
}

async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true

  try {
    const result = await userStore.login(form.value)
    if (result.success) {
      ElMessage({
        message: '登录成功',
        type: 'success',
        duration: 1800
      })

      const role = userStore.userRole
      if (rememberMe.value) {
        localStorage.setItem(REMEMBERED_USERNAME_KEY, form.value.username)
      } else {
        localStorage.removeItem(REMEMBERED_USERNAME_KEY)
      }

      // 登录后直接进入目标页，仅在站点内部路径时回跳，避免开放重定向
      const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : ''
      const isSafeRedirect = redirect.startsWith('/') && !redirect.startsWith('//')
      const fallback = ADMIN_ROLES.includes(role) ? '/admin' : '/assets'
      await router.push(isSafeRedirect ? redirect : fallback)
    } else {
      ElMessage.error(result.message || '登录失败，请检查用户名与密码')
    }
  } finally {
    loading.value = false
  }
}

function fillDemo(username, password) {
  form.value.username = username
  form.value.password = password
}

onMounted(() => {
  const remembered = localStorage.getItem(REMEMBERED_USERNAME_KEY)
  if (remembered) {
    form.value.username = remembered
    rememberMe.value = true
  }
  loadCover()
})

async function loadCover() {
  try {
    const response = await publicApi.getStats()
    const gardens = response.data?.data?.gardens || []
    const garden = gardens.find(g => g.code === 'ZZY' && g.cover_image) || gardens.find(g => g.cover_image)
    if (garden) coverImage.value = garden.cover_image
  } catch {
    // 封面加载失败时保留线稿月洞门，不影响登录
  }
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.login-page {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
  min-height: 100vh;
  background: $bg-primary;
}

// ========== 左侧封面 ==========
.login-aside {
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

.aside-body {
  position: relative;
  z-index: 1;
}

.aside-note {
  font-size: 14px;
  line-height: 1.9;
  color: rgba(252, 253, 251, 0.66);
  max-width: 26em;
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

.aside-photo {
  position: absolute;
  right: -140px;
  bottom: -130px;
  width: 380px;
  height: 380px;
  border-radius: 50%;
  overflow: hidden;
  opacity: 0.62;
  border: 1px solid rgba(252, 253, 251, 0.22);
  pointer-events: none;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.aside-foot {
  position: relative;
  z-index: 1;
  font-size: 11px;
  letter-spacing: 0.16em;
  color: rgba(252, 253, 251, 0.4);
}

// ========== 右侧表单 ==========
.login-main {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
  background: $bg-primary;
}

.login-wrapper {
  width: 100%;
  max-width: 400px;
}

.login-top {
  margin-bottom: 40px;

  .back-link {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    color: $text-secondary;

    &:hover { color: $primary-dark; }
  }
}

.login-header {
  margin-bottom: 28px;

  .login-title {
    font-family: $font-display;
    font-size: 30px;
    font-weight: 600;
    color: $text-primary;
    margin-bottom: 8px;
  }

  .login-desc {
    font-size: 14px;
    color: $text-secondary;
  }
}

.login-form {
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

  :deep(.el-input__inner) {
    font-size: 14px;
  }
}

.form-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 4px 0 22px;

  .form-hint {
    font-size: 12px;
    color: $text-placeholder;
  }
}

.login-btn {
  width: 100%;
  height: 46px;
  font-size: 15px;
  letter-spacing: 0.12em;
}

.register-row {
  margin-top: 24px;
  font-size: 13px;
  color: $text-secondary;
  text-align: center;

  a {
    color: $primary-color;
    margin-left: 4px;

    &:hover { text-decoration: underline; }
  }
}

// ========== 演示账号 ==========
.guide-hint {
  margin-top: 10px;
  text-align: center;
  font-size: 12px;

  a {
    color: $text-placeholder;

    &:hover {
      color: $primary-color;
    }
  }
}

.demo-block {
  margin-top: 36px;
  padding-top: 20px;
  border-top: 1px solid $border-light;

  .demo-title {
    font-size: 11px;
    letter-spacing: 0.16em;
    color: $text-placeholder;
    margin-bottom: 10px;
  }
}

.demo-row {
  display: grid;
  grid-template-columns: 84px 1fr auto;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 10px 12px;
  margin-bottom: 6px;
  background: $bg-card;
  border: 1px solid $border-light;
  border-radius: $radius-sm;
  cursor: pointer;
  text-align: left;
  transition: border-color $transition-fast;

  &:hover {
    border-color: $primary-color;
  }

  .demo-role {
    font-size: 12px;
    color: $text-secondary;
  }

  .demo-credential {
    font-family: $font-mono;
    font-size: 12px;
    color: $text-primary;
  }

  .demo-fill {
    font-size: 12px;
    color: $primary-color;
  }
}

// ========== 响应式 ==========
@media (max-width: 992px) {
  .login-page {
    grid-template-columns: 1fr;
  }

  .login-aside {
    padding: 28px 24px;
    min-height: 260px;
  }

  .aside-body {
    margin: 32px 0 8px;
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

  .aside-photo {
    width: 220px;
    height: 220px;
    right: -50px;
    bottom: -70px;
    opacity: 0.5;
  }

  .aside-foot { display: none; }

  .login-main { padding: 32px 20px 48px; }
}
</style>
