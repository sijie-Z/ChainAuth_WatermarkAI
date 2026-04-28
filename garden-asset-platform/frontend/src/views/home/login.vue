<template>
  <div class="login-page">
    <!-- THREE.js 粒子背景 -->
    <div ref="particlesContainer" class="particles-background"></div>

    <!-- 左侧品牌区域 -->
    <div class="login-aside">
      <div class="aside-content">
        <!-- 中央能量核心 -->
        <div class="energy-core">
          <div class="core-ring core-ring-1"></div>
          <div class="core-ring core-ring-2"></div>
          <div class="core-ring core-ring-3"></div>
          <div class="core-center">
            <svg viewBox="0 0 80 80" fill="none">
              <circle cx="40" cy="40" r="35" stroke="url(#coreGrad)" stroke-width="2" opacity="0.6"/>
              <circle cx="40" cy="40" r="25" stroke="url(#coreGrad)" stroke-width="1.5" opacity="0.4"/>
              <path d="M40 15L55 30V50L40 65L25 50V30L40 15Z" fill="url(#coreGrad)" opacity="0.3"/>
              <path d="M40 25L48 32V48L40 55L32 48V32L40 25Z" fill="white" opacity="0.2"/>
              <defs>
                <linearGradient id="coreGrad" x1="15" y1="15" x2="65" y2="65">
                  <stop stop-color="#34d399"/>
                  <stop offset="1" stop-color="#10b981"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
        </div>

        <h1 class="brand-title">苏州园林数字资产平台</h1>
        <p class="brand-subtitle">基于数字水印和AI推理的数字资产安全分发与溯源系统</p>

        <!-- 特性列表 -->
        <div class="features-list">
          <div class="feature-item" v-for="(feature, idx) in features" :key="idx">
            <div class="feature-icon">{{ feature.icon }}</div>
            <span class="feature-text">{{ feature.text }}</span>
          </div>
        </div>

        <!-- 数据统计 -->
        <div class="stats-row">
          <div class="stat-item">
            <span class="stat-value">156+</span>
            <span class="stat-label">数字资产</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <span class="stat-value">142+</span>
            <span class="stat-label">水印确权</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <span class="stat-value">128+</span>
            <span class="stat-label">链上存证</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧登录区域 -->
    <div class="login-main">
      <div class="login-wrapper">
        <!-- 顶部导航 -->
        <div class="login-nav">
          <router-link to="/home" class="nav-link">
            <el-icon><HomeFilled /></el-icon>
            返回首页
          </router-link>
        </div>

        <!-- 登录卡片 - Glassmorphism -->
        <div class="login-card">
          <!-- 顶部渐变条 -->
          <div class="card-gradient-bar"></div>

          <div class="card-header">
            <h2 class="login-title">欢迎回来</h2>
            <p class="login-desc">请登录您的账号以继续使用</p>
          </div>

          <el-form
            ref="formRef"
            :model="form"
            :rules="rules"
            label-position="top"
            class="login-form"
            @submit.prevent="handleLogin"
          >
            <el-form-item prop="username" class="form-item">
              <template #label>
                <span class="input-label">用户名</span>
              </template>
              <el-input
                v-model="form.username"
                placeholder="请输入用户名"
                size="large"
                class="custom-input"
              >
                <template #prefix>
                  <el-icon class="input-icon"><User /></el-icon>
                </template>
              </el-input>
            </el-form-item>

            <el-form-item prop="password" class="form-item">
              <template #label>
                <div class="label-row">
                  <span class="input-label">密码</span>
                  <a href="#" class="forgot-link">忘记密码？</a>
                </div>
              </template>
              <el-input
                v-model="form.password"
                type="password"
                placeholder="请输入密码"
                size="large"
                show-password
                class="custom-input"
                @keyup.enter="handleLogin"
              >
                <template #prefix>
                  <el-icon class="input-icon"><Lock /></el-icon>
                </template>
              </el-input>
            </el-form-item>

            <el-form-item class="form-item">
              <div class="remember-row">
                <el-checkbox v-model="rememberMe">
                  <span class="remember-text">记住登录状态</span>
                </el-checkbox>
              </div>
            </el-form-item>

            <el-form-item class="form-item">
              <el-button
                type="primary"
                size="large"
                :loading="loading"
                class="login-btn"
                @click="handleLogin"
              >
                <span v-if="!loading">登录</span>
                <span v-else>登录中...</span>
                <el-icon v-if="!loading" class="btn-arrow"><ArrowRight /></el-icon>
              </el-button>
            </el-form-item>

            <!-- 分隔线 -->
            <div class="divider-section">
              <span class="divider-text">或使用其他方式登录</span>
            </div>

            <!-- 第三方登录 -->
            <div class="social-login">
              <button type="button" class="social-btn wechat">
                <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                  <path d="M8.691 2.188C3.891 2.188 0 5.476 0 9.53c0 2.212 1.17 4.203 3.002 5.55a.59.59 0 0 1 .213.665l-.39 1.48c-.019.074-.024.152-.024.232 0 .304.246.55.55.55a.57.57 0 0 0 .263-.065l1.77-.974a1.09 1.09 0 0 1 .722-.092c.956.207 1.958.322 2.987.322.3 0 .596-.012.888-.033-.192-.598-.297-1.233-.297-1.889 0-3.65 3.468-6.608 7.744-6.608.331 0 .658.021.978.058-1.075-3.692-5.037-6.408-9.809-6.408z"/>
                </svg>
              </button>
              <button type="button" class="social-btn alipay">
                <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 17h-2v-2h2v2zm2-7.5c0 1.38-1.12 2.5-2.5 2.5H11v2H9v-4h3.5c.28 0 .5-.22.5-.5v-3c0-.28-.22-.5-.5-.5H9V6h3.5c1.38 0 2.5 1.12 2.5 2.5v3z"/>
                </svg>
              </button>
            </div>

            <!-- 注册链接 -->
            <div class="register-section">
              <span class="register-text">还没有账号？</span>
              <router-link to="/register" class="register-link">立即注册</router-link>
            </div>
          </el-form>
        </div>

        <!-- 演示账号 -->
        <div class="demo-accounts">
          <div class="demo-title">快速登录</div>
          <div class="demo-list">
            <div class="demo-item" @click="fillDemo('admin', 'admin123')">
              <span class="demo-role">管理员</span>
              <span class="demo-account">admin / admin123</span>
            </div>
            <div class="demo-item" @click="fillDemo('adm1', 'adm123')">
              <span class="demo-role">资产管理</span>
              <span class="demo-account">adm1 / adm123</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import { User, Lock, ArrowRight, HomeFilled } from '@element-plus/icons-vue'
import * as THREE from 'three'

const router = useRouter()
const userStore = useUserStore()

const formRef = ref()
const loading = ref(false)
const rememberMe = ref(false)

const form = ref({
  username: '',
  password: ''
})

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

// 特性列表
const features = ref([
  { icon: '🔐', text: '鲁棒水印确权' },
  { icon: '⛓️', text: '区块链存证' },
  { icon: '🤖', text: 'AI侵权检测' }
])

// THREE.js 相关
const particlesContainer = ref(null)
let scene, camera, renderer, particles

const initParticles = () => {
  if (!particlesContainer.value) return

  scene = new THREE.Scene()
  camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000)
  renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true })

  renderer.setSize(window.innerWidth, window.innerHeight)
  renderer.setClearColor(0x000000, 0)
  particlesContainer.value.appendChild(renderer.domElement)

  // 创建粒子几何体
  const particlesGeometry = new THREE.BufferGeometry()
  const particlesCount = 500
  const posArray = new Float32Array(particlesCount * 3)

  for (let i = 0; i < particlesCount * 3; i++) {
    posArray[i] = (Math.random() - 0.5) * 100
  }

  particlesGeometry.setAttribute('position', new THREE.BufferAttribute(posArray, 3))

  // 创建粒子材质
  const particlesMaterial = new THREE.PointsMaterial({
    size: 0.5,
    color: 0x10b981,
    transparent: true,
    opacity: 0.6,
    sizeAttenuation: true
  })

  particles = new THREE.Points(particlesGeometry, particlesMaterial)
  scene.add(particles)

  camera.position.z = 30

  const animate = () => {
    requestAnimationFrame(animate)
    particles.rotation.x += 0.0005
    particles.rotation.y += 0.001
    renderer.render(scene, camera)
  }

  animate()
}

const handleResize = () => {
  if (camera && renderer) {
    camera.aspect = window.innerWidth / window.innerHeight
    camera.updateProjectionMatrix()
    renderer.setSize(window.innerWidth, window.innerHeight)
  }
}

async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true

  try {
    const result = await userStore.login(form.value)
    if (result.success) {
      ElMessage({
        message: '登录成功，欢迎回来！',
        type: 'success',
        duration: 2000
      })

      const role = userStore.userRole
      setTimeout(() => {
        if (['admin', 'adm1', 'adm2', 'adm3'].includes(role)) {
          router.push('/admin')
        } else {
          router.push('/assets')
        }
      }, 500)
    } else {
      ElMessage.error(result.message || '登录失败，请重试')
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
  initParticles()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (renderer && particlesContainer.value) {
    particlesContainer.value.removeChild(renderer.domElement)
  }
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.login-page {
  display: flex;
  min-height: 100vh;
  background: $bg-primary;
  position: relative;
}

// THREE.js 粒子背景
.particles-background {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  pointer-events: none;
}

// ========== 左侧品牌区域 ==========
.login-aside {
  width: 50%;
  background: radial-gradient(circle at 30% 50%, #065f46 0%, #022c22 50%, #011a13 100%);
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 48px;
  z-index: 1;
}

.aside-content {
  position: relative;
  z-index: 1;
  text-align: center;
}

// 能量核心动画
.energy-core {
  position: relative;
  width: 200px;
  height: 200px;
  margin: 0 auto 40px;

  .core-ring {
    position: absolute;
    border-radius: 50%;
    border: 1px solid rgba(16, 185, 129, 0.3);

    &.core-ring-1 {
      inset: 0;
      animation: corePulse 4s ease-in-out infinite;
    }

    &.core-ring-2 {
      inset: 20px;
      animation: corePulse 4s ease-in-out infinite 0.5s;
    }

    &.core-ring-3 {
      inset: 40px;
      animation: corePulse 4s ease-in-out infinite 1s;
    }
  }

  .core-center {
    position: absolute;
    inset: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    animation: coreGlow 3s ease-in-out infinite;

    svg {
      width: 100%;
      height: 100%;
    }
  }
}

@keyframes corePulse {
  0%, 100% {
    transform: scale(1);
    opacity: 0.3;
  }
  50% {
    transform: scale(1.1);
    opacity: 0.6;
  }
}

@keyframes coreGlow {
  0%, 100% {
    filter: drop-shadow(0 0 20px rgba(16, 185, 129, 0.5));
  }
  50% {
    filter: drop-shadow(0 0 40px rgba(16, 185, 129, 0.8));
  }
}

.brand-title {
  font-size: 36px;
  font-weight: $font-weight-bold;
  color: white;
  margin-bottom: 16px;
  text-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.brand-subtitle {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.7);
  line-height: 1.6;
  max-width: 320px;
  margin: 0 auto 48px;
}

// 特性列表
.features-list {
  display: flex;
  justify-content: center;
  gap: 24px;
  margin-bottom: 48px;

  .feature-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 20px;
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(10px);
    border-radius: $radius-full;
    border: 1px solid rgba(255, 255, 255, 0.1);
    transition: all $transition-base;

    &:hover {
      background: rgba(255, 255, 255, 0.1);
      transform: translateY(-2px);
    }

    .feature-icon {
      font-size: 18px;
    }

    .feature-text {
      font-size: 14px;
      font-weight: $font-weight-medium;
      color: white;
    }
  }
}

// 数据统计
.stats-row {
  display: flex;
  align-items: center;
  gap: 32px;

  .stat-item {
    text-align: center;

    .stat-value {
      display: block;
      font-size: 28px;
      font-weight: $font-weight-bold;
      color: white;
      margin-bottom: 4px;
    }

    .stat-label {
      font-size: 13px;
      color: rgba(255, 255, 255, 0.6);
    }
  }

  .stat-divider {
    width: 1px;
    height: 40px;
    background: rgba(255, 255, 255, 0.2);
  }
}

// ========== 右侧登录区域 ==========
.login-main {
  width: 50%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 48px;
  position: relative;
  z-index: 1;
}

.login-wrapper {
  width: 100%;
  max-width: 420px;
}

.login-nav {
  margin-bottom: 32px;

  .nav-link {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    font-weight: $font-weight-medium;
    color: $text-secondary;
    transition: color $transition-fast;

    &:hover {
      color: $primary-color;
    }
  }
}

// Glassmorphism 登录卡片
.login-card {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-radius: $radius-2xl;
  padding: 48px 40px;
  box-shadow:
    0 25px 50px -12px rgba(0, 0, 0, 0.15),
    0 0 0 1px rgba(255, 255, 255, 0.1);
  position: relative;
  overflow: hidden;

  // 顶部渐变条
  .card-gradient-bar {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: linear-gradient(90deg, #10b981, #34d399, #10b981);
    background-size: 200% 100%;
    animation: gradientSlide 3s linear infinite;
  }
}

@keyframes gradientSlide {
  0% { background-position: 0% 0%; }
  100% { background-position: 200% 0%; }
}

.card-header {
  text-align: center;
  margin-bottom: 32px;

  .login-title {
    font-size: 28px;
    font-weight: $font-weight-bold;
    color: $text-primary;
    margin-bottom: 8px;
  }

  .login-desc {
    font-size: 15px;
    color: $text-secondary;
  }
}

// 表单样式
.login-form {
  .form-item {
    margin-bottom: 24px;
  }

  .input-label {
    font-size: 14px;
    font-weight: $font-weight-medium;
    color: $text-primary;
  }

  .label-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .forgot-link {
    font-size: 13px;
    color: $primary-color;
    cursor: pointer;

    &:hover {
      text-decoration: underline;
    }
  }

  .custom-input {
    :deep(.el-input__wrapper) {
      background: $bg-primary;
      border-radius: $radius-lg;
      border: 1px solid $border-color;
      box-shadow: none;
      padding: 4px 16px;
      height: 48px;
      transition: all $transition-fast;

      &:hover, &.is-focus {
        border-color: $primary-color;
        box-shadow: 0 0 0 3px rgba($primary-color, 0.1);
      }
    }

    :deep(.el-input__inner) {
      font-size: 15px;
      color: $text-primary;

      &::placeholder {
        color: $text-placeholder;
      }
    }

    .input-icon {
      font-size: 18px;
      color: $text-placeholder;
    }
  }

  .remember-row {
    display: flex;
    align-items: center;

    .remember-text {
      font-size: 14px;
      color: $text-secondary;
    }
  }

  .login-btn {
    width: 100%;
    height: 48px;
    font-size: 16px;
    font-weight: $font-weight-semibold;
    border-radius: $radius-lg;
    background: $primary-gradient;
    border: none;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    transition: all $transition-base;

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 20px rgba($primary-color, 0.3);
    }

    &:active {
      transform: translateY(0);
    }

    .btn-arrow {
      font-size: 18px;
      transition: transform $transition-fast;
    }

    &:hover .btn-arrow {
      transform: translateX(4px);
    }
  }
}

// 分隔线
.divider-section {
  display: flex;
  align-items: center;
  margin: 24px 0;

  &::before,
  &::after {
    content: '';
    flex: 1;
    height: 1px;
    background: $border-color;
  }

  .divider-text {
    padding: 0 16px;
    font-size: 13px;
    color: $text-placeholder;
  }
}

// 第三方登录
.social-login {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-bottom: 24px;

  .social-btn {
    width: 48px;
    height: 48px;
    border-radius: $radius-lg;
    border: 1px solid $border-color;
    background: white;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all $transition-fast;

    &:hover {
      border-color: $primary-color;
      transform: translateY(-2px);
      box-shadow: $shadow-md;
    }

    &.wechat {
      color: #07c160;
    }

    &.alipay {
      color: #1677ff;
    }
  }
}

// 注册链接
.register-section {
  text-align: center;

  .register-text {
    font-size: 14px;
    color: $text-secondary;
  }

  .register-link {
    font-size: 14px;
    font-weight: $font-weight-semibold;
    color: $primary-color;
    margin-left: 8px;
    cursor: pointer;

    &:hover {
      text-decoration: underline;
    }
  }
}

// 演示账号
.demo-accounts {
  margin-top: 32px;

  .demo-title {
    font-size: 12px;
    font-weight: $font-weight-medium;
    color: $text-placeholder;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 12px;
  }

  .demo-list {
    display: flex;
    gap: 12px;
  }

  .demo-item {
    flex: 1;
    padding: 12px 16px;
    background: rgba(255, 255, 255, 0.9);
    backdrop-filter: blur(10px);
    border: 1px solid $border-color;
    border-radius: $radius-lg;
    cursor: pointer;
    transition: all $transition-fast;

    &:hover {
      border-color: $primary-color;
      transform: translateY(-2px);
      box-shadow: $shadow-sm;
    }

    .demo-role {
      display: block;
      font-size: 12px;
      font-weight: $font-weight-medium;
      color: $text-secondary;
      margin-bottom: 4px;
    }

    .demo-account {
      font-size: 11px;
      font-family: $font-mono;
      color: $text-placeholder;
    }
  }
}

// ========== 响应式 ==========
@media (max-width: 992px) {
  .login-page {
    flex-direction: column;
  }

  .login-aside {
    width: 100%;
    min-height: auto;
    padding: 48px 32px;

    .energy-core {
      width: 150px;
      height: 150px;
      margin-bottom: 24px;

      .core-center {
        inset: 45px;
      }
    }

    .brand-title {
      font-size: 28px;
    }

    .features-list {
      flex-wrap: wrap;
      gap: 12px;
    }

    .stats-row {
      gap: 20px;

      .stat-value {
        font-size: 22px;
      }
    }
  }

  .login-main {
    width: 100%;
    padding: 32px 24px;
  }

  .login-card {
    padding: 32px 24px;
  }

  .demo-accounts {
    .demo-list {
      flex-direction: column;
    }
  }
}
</style>
