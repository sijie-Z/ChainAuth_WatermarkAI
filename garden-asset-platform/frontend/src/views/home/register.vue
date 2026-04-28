<template>
  <div class="register-page">
    <!-- THREE.js 粒子背景 -->
    <div ref="particlesContainer" class="particles-background"></div>

    <!-- 左侧品牌区域 -->
    <div class="register-aside">
      <div class="aside-content">
        <!-- 中央能量核心 -->
        <div class="energy-core">
          <div class="core-ring core-ring-1"></div>
          <div class="core-ring core-ring-2"></div>
          <div class="core-center">
            <svg viewBox="0 0 80 80" fill="none">
              <circle cx="40" cy="40" r="35" stroke="url(#coreGradR)" stroke-width="2" opacity="0.6"/>
              <circle cx="40" cy="40" r="25" stroke="url(#coreGradR)" stroke-width="1.5" opacity="0.4"/>
              <path d="M40 15L55 30V50L40 65L25 50V30L40 15Z" fill="url(#coreGradR)" opacity="0.3"/>
              <defs>
                <linearGradient id="coreGradR" x1="15" y1="15" x2="65" y2="65">
                  <stop stop-color="#34d399"/>
                  <stop offset="1" stop-color="#10b981"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
        </div>

        <h1 class="brand-title">苏州园林数字资产平台</h1>
        <p class="brand-subtitle">创建账户，开启您的数字资产保护之旅</p>

        <!-- 特性列表 -->
        <div class="features-list">
          <div class="feature-item" v-for="(feature, idx) in features" :key="idx">
            <div class="feature-icon">{{ feature.icon }}</div>
            <span class="feature-text">{{ feature.text }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧注册区域 -->
    <div class="register-main">
      <div class="register-wrapper">
        <!-- 顶部导航 -->
        <div class="register-nav">
          <router-link to="/home" class="nav-link">
            <el-icon><HomeFilled /></el-icon>
            返回首页
          </router-link>
        </div>

        <!-- 注册卡片 -->
        <div class="register-card">
          <!-- 顶部渐变条 -->
          <div class="card-gradient-bar"></div>

          <div class="card-header">
            <h2 class="register-title">创建账户</h2>
            <p class="register-desc">加入我们，保护您的数字资产</p>
          </div>

          <el-form ref="formRef" :model="form" :rules="rules" label-position="top" class="register-form" @submit.prevent="handleRegister">
            <el-form-item prop="username" class="form-item">
              <template #label>
                <span class="input-label">用户名</span>
              </template>
              <el-input v-model="form.username" placeholder="请输入用户名" size="large" class="custom-input">
                <template #prefix>
                  <el-icon class="input-icon"><User /></el-icon>
                </template>
              </el-input>
            </el-form-item>

            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item prop="email" class="form-item">
                  <template #label>
                    <span class="input-label">邮箱</span>
                  </template>
                  <el-input v-model="form.email" placeholder="请输入邮箱" size="large" class="custom-input">
                    <template #prefix>
                      <el-icon class="input-icon"><Message /></el-icon>
                    </template>
                  </el-input>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item prop="phone" class="form-item">
                  <template #label>
                    <span class="input-label">手机号</span>
                  </template>
                  <el-input v-model="form.phone" placeholder="请输入手机号" size="large" class="custom-input">
                    <template #prefix>
                      <el-icon class="input-icon"><Phone /></el-icon>
                    </template>
                  </el-input>
                </el-form-item>
              </el-col>
            </el-row>

            <el-form-item prop="password" class="form-item">
              <template #label>
                <span class="input-label">密码</span>
              </template>
              <el-input v-model="form.password" type="password" placeholder="请输入密码" size="large" show-password class="custom-input">
                <template #prefix>
                  <el-icon class="input-icon"><Lock /></el-icon>
                </template>
              </el-input>
            </el-form-item>

            <el-form-item prop="confirmPassword" class="form-item">
              <template #label>
                <span class="input-label">确认密码</span>
              </template>
              <el-input v-model="form.confirmPassword" type="password" placeholder="请再次输入密码" size="large" show-password class="custom-input">
                <template #prefix>
                  <el-icon class="input-icon"><Lock /></el-icon>
                </template>
              </el-input>
            </el-form-item>

            <!-- 角色选择 -->
            <el-form-item prop="role" class="form-item">
              <template #label>
                <span class="input-label">账户类型</span>
              </template>
              <div class="role-capsule">
                <div class="capsule-option" :class="{ active: form.role === 'user' }" @click="form.role = 'user'">
                  <el-icon><User /></el-icon>
                  <span>普通用户</span>
                </div>
                <div class="capsule-option" :class="{ active: form.role === 'admin' }" @click="form.role = 'admin'">
                  <el-icon><UserFilled /></el-icon>
                  <span>管理员</span>
                </div>
                <div class="capsule-slider" :class="{ right: form.role === 'admin' }"></div>
              </div>
            </el-form-item>

            <!-- 管理员编号 -->
            <el-form-item v-if="form.role === 'admin'" prop="user_number" class="form-item">
              <template #label>
                <span class="input-label">管理员编号</span>
              </template>
              <el-input v-model="form.user_number" placeholder="如: adm1, adm2, adm3" size="large" class="custom-input">
                <template #prefix>
                  <el-icon class="input-icon"><Key /></el-icon>
                </template>
              </el-input>
            </el-form-item>

            <el-form-item class="form-item">
              <el-button type="primary" size="large" :loading="loading" class="register-btn" @click="handleRegister">
                <span v-if="!loading">创建账户</span>
                <span v-else>创建中...</span>
                <el-icon v-if="!loading" class="btn-arrow"><ArrowRight /></el-icon>
              </el-button>
            </el-form-item>

            <!-- 登录链接 -->
            <div class="login-section">
              <span class="login-text">已有账号？</span>
              <router-link to="/login" class="login-link">立即登录</router-link>
            </div>
          </el-form>
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
import { User, UserFilled, Lock, Message, Phone, Key, ArrowRight, HomeFilled } from '@element-plus/icons-vue'
import * as THREE from 'three'

const router = useRouter()
const userStore = useUserStore()

const formRef = ref()
const loading = ref(false)

const form = ref({
  username: '',
  email: '',
  phone: '',
  password: '',
  confirmPassword: '',
  role: 'user',
  user_number: ''
})

// 特性列表
const features = ref([
  { icon: '🔐', text: '安全可靠的账户保护' },
  { icon: '🎨', text: '专业的数字资产服务' },
  { icon: '🤝', text: '便捷的授权管理' }
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

const validatePass = (rule, value, callback) => {
  if (value !== form.value.password) {
    callback(new Error('两次输入密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  confirmPassword: [{ required: true, validator: validatePass, trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }]
}

async function handleRegister() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true

  try {
    const data = {
      username: form.value.username,
      email: form.value.email,
      phone: form.value.phone,
      password: form.value.password,
      role: form.value.role,
      user_number: form.value.role === 'admin' ? form.value.user_number : null
    }

    const result = await userStore.register(data)
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

.register-page {
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
.register-aside {
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
      animation: corePulseReg 4s ease-in-out infinite;
    }

    &.core-ring-2 {
      inset: 30px;
      animation: corePulseReg 4s ease-in-out infinite 0.5s;
    }
  }

  .core-center {
    position: absolute;
    inset: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    animation: coreGlowReg 3s ease-in-out infinite;

    svg {
      width: 100%;
      height: 100%;
    }
  }
}

@keyframes corePulseReg {
  0%, 100% {
    transform: scale(1);
    opacity: 0.3;
  }
  50% {
    transform: scale(1.1);
    opacity: 0.6;
  }
}

@keyframes coreGlowReg {
  0%, 100% {
    filter: drop-shadow(0 0 20px rgba(16, 185, 129, 0.5));
  }
  50% {
    filter: drop-shadow(0 0 40px rgba(16, 185, 129, 0.8));
  }
}

.brand-title {
  font-size: 32px;
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
  flex-direction: column;
  gap: 16px;

  .feature-item {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    padding: 12px 20px;
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(10px);
    border-radius: $radius-full;
    border: 1px solid rgba(255, 255, 255, 0.1);
    transition: all $transition-base;

    &:hover {
      background: rgba(255, 255, 255, 0.1);
      transform: translateX(5px);
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

// ========== 右侧注册区域 ==========
.register-main {
  width: 50%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 48px;
  position: relative;
  z-index: 1;
}

.register-wrapper {
  width: 100%;
  max-width: 480px;
}

.register-nav {
  margin-bottom: 24px;

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

// Glassmorphism 注册卡片
.register-card {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-radius: $radius-2xl;
  padding: 40px 36px;
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

.card-header {
  text-align: center;
  margin-bottom: 28px;

  .register-title {
    font-size: 26px;
    font-weight: $font-weight-bold;
    color: $text-primary;
    margin-bottom: 8px;
  }

  .register-desc {
    font-size: 14px;
    color: $text-secondary;
  }
}

// 表单样式
.register-form {
  .form-item {
    margin-bottom: 20px;
  }

  .input-label {
    font-size: 14px;
    font-weight: $font-weight-medium;
    color: $text-primary;
  }

  .custom-input {
    :deep(.el-input__wrapper) {
      background: $bg-primary;
      border-radius: $radius-lg;
      border: 1px solid $border-color;
      box-shadow: none;
      height: 44px;
      transition: all $transition-fast;

      &:hover, &.is-focus {
        border-color: $primary-color;
        box-shadow: 0 0 0 3px rgba($primary-color, 0.1);
      }
    }

    .input-icon {
      font-size: 16px;
      color: $text-placeholder;
    }
  }
}

// 胶囊角色选择器
.role-capsule {
  position: relative;
  display: flex;
  background: $bg-primary;
  border-radius: $radius-full;
  padding: 4px;
  border: 1px solid $border-color;

  .capsule-option {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 10px 16px;
    border-radius: $radius-full;
    cursor: pointer;
    z-index: 1;
    transition: color $transition-fast;
    color: $text-secondary;

    &.active {
      color: white;
    }
  }

  .capsule-slider {
    position: absolute;
    top: 4px;
    left: 4px;
    width: calc(50% - 4px);
    height: calc(100% - 8px);
    background: $primary-gradient;
    border-radius: $radius-full;
    transition: transform $transition-base;
    z-index: 0;

    &.right {
      transform: translateX(100%);
    }
  }
}

.register-btn {
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

  .btn-arrow {
    font-size: 18px;
    transition: transform $transition-fast;
  }

  &:hover .btn-arrow {
    transform: translateX(4px);
  }
}

// 登录链接
.login-section {
  text-align: center;
  margin-top: 20px;

  .login-text {
    font-size: 14px;
    color: $text-secondary;
  }

  .login-link {
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

// ========== 响应式 ==========
@media (max-width: 992px) {
  .register-page {
    flex-direction: column;
  }

  .register-aside {
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
      font-size: 26px;
    }

    .features-list {
      flex-direction: row;
      flex-wrap: wrap;
      justify-content: center;
      gap: 12px;
    }
  }

  .register-main {
    width: 100%;
    padding: 32px 24px;
  }

  .register-card {
    padding: 32px 24px;
  }
}
</style>
