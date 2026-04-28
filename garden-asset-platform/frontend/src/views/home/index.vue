<template>
  <div class="home-page">
    <!-- THREE.js 粒子背景 -->
    <div ref="particlesContainer" class="particles-background"></div>

    <!-- 顶部导航 -->
    <header class="navbar" :class="{ 'navbar-scrolled': isScrolled }">
      <div class="navbar-container">
        <div class="navbar-brand">
          <div class="brand-icon">
            <svg viewBox="0 0 32 32" fill="none">
              <path d="M16 2L4 10v12l12 8 12-8V10L16 2z" fill="url(#gradient1)"/>
              <path d="M16 8L8 13v6l8 5 8-5v-6l-8-5z" fill="white" fill-opacity="0.3"/>
              <defs>
                <linearGradient id="gradient1" x1="4" y1="2" x2="28" y2="30">
                  <stop stop-color="#10b981"/>
                  <stop offset="1" stop-color="#059669"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
          <span class="brand-text">园林数字资产平台</span>
        </div>

        <nav class="navbar-menu">
          <router-link to="/home" class="nav-link active">首页</router-link>
          <router-link to="/assets" class="nav-link">资产中心</router-link>
          <router-link to="/trace" class="nav-link">溯源查询</router-link>
          <template v-if="isLoggedIn">
            <router-link to="/license/my" class="nav-link">我的授权</router-link>
            <router-link v-if="isAdmin" to="/admin" class="nav-link">管理后台</router-link>
          </template>
        </nav>

        <div class="navbar-actions">
          <template v-if="isLoggedIn">
            <el-dropdown trigger="click" @command="handleCommand">
              <div class="user-avatar-wrapper">
                <el-avatar :size="36" :src="userAvatar" class="user-avatar">
                  {{ username?.charAt(0)?.toUpperCase() }}
                </el-avatar>
                <span class="user-name">{{ username }}</span>
                <el-icon class="dropdown-arrow"><ArrowDown /></el-icon>
              </div>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="profile">
                    <el-icon><User /></el-icon>
                    个人中心
                  </el-dropdown-item>
                  <el-dropdown-item command="settings">
                    <el-icon><Setting /></el-icon>
                    账号设置
                  </el-dropdown-item>
                  <el-dropdown-item divided command="logout">
                    <el-icon><SwitchButton /></el-icon>
                    退出登录
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
          <template v-else>
            <router-link to="/login" class="btn-login">登录</router-link>
            <router-link to="/register" class="btn-register">立即注册</router-link>
          </template>
        </div>
      </div>
    </header>

    <!-- Hero 区域 -->
    <section class="hero-section">
      <div class="hero-bg">
        <div class="hero-gradient"></div>
        <div class="hero-pattern"></div>
        <div class="hero-glow"></div>
      </div>

      <div class="hero-content">
        <div class="hero-badge animate-fade-in">
          <span class="badge-icon">🏆</span>
          <span class="badge-text">挑战杯项目 - 苏州园林数字资产保护平台</span>
        </div>

        <h1 class="hero-title animate-fade-in" style="animation-delay: 0.1s">
          从<span class="text-gradient">"版权裸奔"</span>到<span class="text-gradient">"链上确权"</span>
        </h1>

        <p class="hero-subtitle animate-fade-in" style="animation-delay: 0.2s">
          基于数字水印和AI推理的苏州园林数字资产安全分发与溯源系统
        </p>

        <div class="hero-actions animate-fade-in" style="animation-delay: 0.3s">
          <button class="btn-primary-lg" @click="goToAssets">
            <span>探索资产</span>
            <el-icon><ArrowRight /></el-icon>
          </button>
          <button class="btn-secondary-lg" @click="goToTrace">
            <el-icon><Search /></el-icon>
            <span>溯源查询</span>
          </button>
        </div>

        <div class="hero-stats animate-fade-in" style="animation-delay: 0.4s">
          <div class="hero-stat-item">
            <div class="stat-value">
              <span class="count-up" data-target="156">{{ animatedStats.assets }}</span>+
            </div>
            <div class="stat-label">数字资产</div>
          </div>
          <div class="hero-stat-divider"></div>
          <div class="hero-stat-item">
            <div class="stat-value">
              <span class="count-up">{{ animatedStats.watermarked }}</span>+
            </div>
            <div class="stat-label">水印确权</div>
          </div>
          <div class="hero-stat-divider"></div>
          <div class="hero-stat-item">
            <div class="stat-value">
              <span class="count-up">{{ animatedStats.chained }}</span>+
            </div>
            <div class="stat-label">链上存证</div>
          </div>
          <div class="hero-stat-divider"></div>
          <div class="hero-stat-item">
            <div class="stat-value">
              <span class="count-up">{{ animatedStats.licenses }}</span>+
            </div>
            <div class="stat-label">授权记录</div>
          </div>
        </div>
      </div>

      <div class="hero-visual">
        <div class="floating-cards">
          <div class="floating-card card-1">
            <div class="card-icon">🔐</div>
            <div class="card-text">水印已嵌入</div>
          </div>
          <div class="floating-card card-2">
            <div class="card-icon"><svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg></div>
            <div class="card-text">区块链验证通过</div>
          </div>
          <div class="floating-card card-3">
            <div class="card-icon">🎨</div>
            <div class="card-text">拙政园全景图</div>
          </div>
        </div>
      </div>

      <div class="scroll-indicator">
        <el-icon class="bounce"><ArrowDown /></el-icon>
      </div>
    </section>

    <!-- 功能特点 -->
    <section class="features-section">
      <div class="section-container">
        <div class="section-header">
          <h2 class="section-title">核心功能</h2>
          <p class="section-subtitle">全方位保护您的数字资产，从确权到溯源的完整解决方案</p>
        </div>

        <div class="features-grid">
          <div class="feature-card" v-for="(feature, index) in features" :key="index"
               :style="{ animationDelay: index * 0.1 + 's' }">
            <div class="feature-icon-wrapper" :style="{ background: feature.gradient }">
              <span class="feature-icon">{{ feature.icon }}</span>
            </div>
            <h3 class="feature-title">{{ feature.title }}</h3>
            <p class="feature-desc">{{ feature.description }}</p>
            <div class="feature-tags">
              <span class="feature-tag" v-for="tag in feature.tags" :key="tag">{{ tag }}</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 园林展示 -->
    <section class="gardens-section">
      <div class="section-container">
        <div class="section-header">
          <h2 class="section-title">苏州园林</h2>
          <p class="section-subtitle">世界文化遗产，中国古典园林的杰出代表</p>
        </div>

        <div class="gardens-grid">
          <div
            class="garden-card"
            v-for="garden in gardens"
            :key="garden.id"
            @click="goToGarden(garden.id)"
          >
            <div class="garden-image-wrapper">
              <img
                :src="garden.cover_image || getDefaultImage(garden.code)"
                :alt="garden.name"
                class="garden-image"
              />
              <div class="garden-overlay">
                <span class="view-btn">查看资产</span>
              </div>
            </div>
            <div class="garden-content">
              <h3 class="garden-name">{{ garden.name }}</h3>
              <p class="garden-desc">{{ garden.description }}</p>
              <div class="garden-meta">
                <span class="meta-item">
                  <el-icon><Picture /></el-icon>
                  {{ garden.asset_count || 0 }} 资产
                </span>
                <span class="meta-item">
                  <el-icon><Location /></el-icon>
                  {{ garden.location || '苏州' }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 工作流程 -->
    <section class="workflow-section">
      <div class="section-container">
        <div class="section-header">
          <h2 class="section-title">工作流程</h2>
          <p class="section-subtitle">四步完成数字资产的全生命周期保护</p>
        </div>

        <div class="workflow-timeline">
          <div class="workflow-line"></div>
          <div
            class="workflow-step"
            v-for="(step, index) in workflowSteps"
            :key="index"
          >
            <div class="step-number">{{ index + 1 }}</div>
            <div class="step-content">
              <div class="step-icon">{{ step.icon }}</div>
              <h4 class="step-title">{{ step.title }}</h4>
              <p class="step-desc">{{ step.description }}</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 技术架构 -->
    <section class="tech-section">
      <div class="section-container">
        <div class="section-header">
          <h2 class="section-title">技术架构</h2>
          <p class="section-subtitle">采用前沿技术，保障资产安全</p>
        </div>

        <div class="tech-grid">
          <div class="tech-card" v-for="tech in techStack" :key="tech.name">
            <div class="tech-icon-wrapper">
              <span class="tech-icon">{{ tech.icon }}</span>
            </div>
            <h4 class="tech-name">{{ tech.name }}</h4>
            <p class="tech-desc">{{ tech.description }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- 页脚 -->
    <footer class="footer">
      <div class="footer-waves">
        <svg viewBox="0 0 1440 120" preserveAspectRatio="none">
          <path d="M0,64L80,69.3C160,75,320,85,480,80C640,75,800,53,960,48C1120,43,1280,53,1360,58.7L1440,64L1440,120L1360,120C1280,120,1120,120,960,120C800,120,640,120,480,120C320,120,160,120,80,120L0,120Z" fill="currentColor"/>
        </svg>
      </div>
      <div class="footer-content">
        <div class="footer-brand">
          <div class="brand-icon">
            <svg viewBox="0 0 32 32" fill="none">
              <path d="M16 2L4 10v12l12 8 12-8V10L16 2z" fill="#10b981"/>
            </svg>
          </div>
          <span>苏州园林数字资产平台</span>
        </div>
        <div class="footer-links">
          <a href="#">关于我们</a>
          <a href="#">使用条款</a>
          <a href="#">隐私政策</a>
          <a href="#">联系我们</a>
        </div>
        <div class="footer-copyright">
          <p>© 2026 挑战杯项目团队 | 苏州大学计算机科学与技术学院</p>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { gardenApi, publicApi } from '@/api/modules'
import {
  ArrowDown, ArrowRight, Search, User, Setting, SwitchButton,
  Picture, Location
} from '@element-plus/icons-vue'
import * as THREE from 'three'

const router = useRouter()
const userStore = useUserStore()

const gardens = ref([])
const isScrolled = ref(false)
const animatedStats = ref({
  assets: 0,
  watermarked: 0,
  chained: 0,
  licenses: 0
})

// THREE.js 粒子背景
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
    opacity: 0.4,
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

const handleResizeParticles = () => {
  if (camera && renderer) {
    camera.aspect = window.innerWidth / window.innerHeight
    camera.updateProjectionMatrix()
    renderer.setSize(window.innerWidth, window.innerHeight)
  }
}

// 功能特点数据
const features = ref([
  {
    icon: '🔐',
    title: '水印确权',
    description: '自研鲁棒水印算法，抗几何攻击能力强，隐式嵌入资产唯一标识，确保版权归属',
    gradient: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
    tags: ['DCT域嵌入', '矢量坐标扰动', '抗攻击']
  },
  {
    icon: '⛓️',
    title: '区块链存证',
    description: '采用FISCO BCOS联盟链技术，实现不可篡改的电子存证，具备司法级证据效力',
    gradient: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
    tags: ['不可篡改', '司法效力', '可信存证']
  },
  {
    icon: '🤖',
    title: 'AI侵权检测',
    description: '基于CLIP特征提取与向量检索技术，智能发现网络侵权行为，保护数字资产权益',
    gradient: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
    tags: ['CLIP特征', '向量检索', '智能识别']
  },
  {
    icon: '📋',
    title: '全链路溯源',
    description: '从资产上传到水印嵌入、链上存证、授权分发，全流程可追溯，形成完整证据链',
    gradient: 'linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%)',
    tags: ['全程追溯', '证据链', '合规审计']
  }
])

// 工作流程步骤
const workflowSteps = ref([
  { icon: '📤', title: '上传资产', description: '上传数字资产图片、模型或矢量数据' },
  { icon: '🔐', title: '嵌入水印', description: '自动嵌入鲁棒数字水印标识' },
  { icon: '⛓️', title: '链上存证', description: '将资产信息上链存证确权' },
  { icon: '📜', title: '授权分发', description: '管理授权与溯源追踪' }
])

// 技术栈
const techStack = ref([
  { icon: '🐍', name: 'Python Flask', description: '高性能后端框架' },
  { icon: '💚', name: 'Vue 3 + Vite', description: '现代化前端技术栈' },
  { icon: '🔗', name: 'FISCO BCOS', description: '国产联盟区块链' },
  { icon: '🤖', name: 'GLM-4-Flash', description: '智能AI分析服务' },
  { icon: '📊', name: 'Milvus', description: '向量相似度检索' },
  { icon: '🐘', name: 'PostgreSQL', description: '可靠数据存储' }
])

const isLoggedIn = computed(() => userStore.isLoggedIn)
const isAdmin = computed(() => ['admin', 'adm1', 'adm2', 'adm3'].includes(userStore.userRole))
const username = computed(() => userStore.username)
const userAvatar = computed(() => userStore.user?.avatar)

const gardenColorMap = { 'ZZY': '#10b981', 'LY': '#3b82f6', 'SZL': '#f59e0b', 'CLT': '#8b5cf6' }

function getDefaultImage(code) {
  const color = gardenColorMap[code] || '#10b981'
  const hex = color.replace('#', '')
  return `data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="300"%3E%3Crect fill="%23${hex}" width="400" height="300"/%3E%3Ctext x="200" y="150" text-anchor="middle" fill="white" font-size="24"%3E${code || '?'}%3C/text%3E%3C/svg%3E`
}

// 统计数据目标值
const statsTargets = ref({ assets: 0, watermarked: 0, chained: 0, licenses: 0 })

async function loadStats() {
  try {
    const response = await publicApi.getStats()
    if (response.data?.code === 200) {
      const d = response.data.data
      statsTargets.value = {
        assets: d.total_assets || 0,
        watermarked: d.watermarked_assets || 0,
        chained: d.chained_assets || 0,
        licenses: d.total_licenses || 0
      }
      // 如果有园林数据，同时更新
      if (d.gardens?.length) {
        gardens.value = d.gardens.slice(0, 4)
      }
    }
  } catch {
    // 保持初始值（0）
  }
  animateNumbers()
}

async function loadGardens() {
  try {
    const response = await gardenApi.getList()
    if (response.data?.code === 200 && response.data.data?.length) {
      gardens.value = response.data.data.slice(0, 4)
    }
  } catch {
    // 如果已有 stats 数据中的 gardens，不覆盖
    if (gardens.value.length === 0) {
      gardens.value = [
        { id: 1, name: '拙政园', code: 'ZZY', description: '中国四大名园之首', asset_count: 0, location: '姑苏区' },
        { id: 2, name: '留园', code: 'LY', description: '以园林建筑艺术著称', asset_count: 0, location: '姑苏区' },
        { id: 3, name: '狮子林', code: 'SZL', description: '以假山迷宫闻名', asset_count: 0, location: '姑苏区' },
        { id: 4, name: '沧浪亭', code: 'CLT', description: '历史最悠久的园林', asset_count: 0, location: '姑苏区' }
      ]
    }
  }
}

function animateNumbers() {
  const targets = statsTargets.value
  const duration = 2000
  const steps = 60
  const interval = duration / steps

  Object.keys(targets).forEach(key => {
    const target = targets[key]
    if (target === 0) {
      animatedStats.value[key] = 0
      return
    }
    const increment = target / steps
    let current = 0

    const timer = setInterval(() => {
      current += increment
      if (current >= target) {
        animatedStats.value[key] = target
        clearInterval(timer)
      } else {
        animatedStats.value[key] = Math.floor(current)
      }
    }, interval)
  })
}

// 滚动监听
function handleScroll() {
  isScrolled.value = window.scrollY > 20
}

// 导航处理
function handleCommand(command) {
  if (command === 'logout') {
    userStore.logout()
    router.push('/home')
  } else if (command === 'profile') {
    router.push('/profile')
  } else if (command === 'settings') {
    router.push('/settings')
  }
}

function goToAssets() {
  router.push('/assets')
}

function goToTrace() {
  router.push('/trace')
}

function goToGarden(id) {
  router.push(`/assets?garden_id=${id}`)
}

onMounted(() => {
  userStore.initStore()
  loadStats()
  loadGardens()
  window.addEventListener('scroll', handleScroll)
  initParticles()
  window.addEventListener('resize', handleResizeParticles)
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
  window.removeEventListener('resize', handleResizeParticles)
  if (renderer && particlesContainer.value) {
    particlesContainer.value.removeChild(renderer.domElement)
  }
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.home-page {
  min-height: 100vh;
  background: $bg-primary;
  overflow-x: hidden;
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

// ========== 导航栏 ==========
.navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  padding: 0 48px;
  height: $header-height;
  transition: all $transition-base;
  background: transparent;

  &-container {
    max-width: 1400px;
    margin: 0 auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 100%;
  }

  &-scrolled {
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: $glass-blur;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);

    .nav-link {
      color: $text-primary;
    }

    .brand-text {
      color: $text-primary;
    }
  }
}

.navbar-brand {
  display: flex;
  align-items: center;
  gap: 12px;

  .brand-icon {
    width: 36px;
    height: 36px;

    svg {
      width: 100%;
      height: 100%;
    }
  }

  .brand-text {
    font-size: 18px;
    font-weight: $font-weight-semibold;
    color: white;
    transition: color $transition-base;
  }
}

.navbar-menu {
  display: flex;
  align-items: center;
  gap: 8px;

  .nav-link {
    padding: 8px 16px;
    font-size: 15px;
    font-weight: $font-weight-medium;
    color: rgba(255, 255, 255, 0.9);
    border-radius: $radius-lg;
    transition: all $transition-fast;

    &:hover {
      background: rgba(255, 255, 255, 0.1);
      color: white;
    }

    &.active,
    &.router-link-active {
      background: rgba(255, 255, 255, 0.15);
      color: white;
    }
  }
}

.navbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-login {
  padding: 8px 20px;
  font-size: 14px;
  font-weight: $font-weight-medium;
  color: white;
  border-radius: $radius-lg;
  transition: all $transition-fast;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
  }
}

.btn-register {
  padding: 8px 20px;
  font-size: 14px;
  font-weight: $font-weight-medium;
  color: white;
  background: rgba(255, 255, 255, 0.2);
  border-radius: $radius-lg;
  transition: all $transition-fast;

  &:hover {
    background: rgba(255, 255, 255, 0.3);
  }
}

.user-avatar-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 12px 6px 6px;
  border-radius: $radius-full;
  cursor: pointer;
  transition: all $transition-fast;
  background: rgba(255, 255, 255, 0.15);

  &:hover {
    background: rgba(255, 255, 255, 0.25);
  }

  .user-name {
    font-size: 14px;
    font-weight: $font-weight-medium;
    color: white;
  }

  .dropdown-arrow {
    font-size: 12px;
    color: white;
    transition: transform $transition-fast;
  }

  .user-avatar {
    background: linear-gradient(135deg, $primary-light, $primary-dark);
    border: 2px solid rgba(255, 255, 255, 0.3);
  }
}

// ========== Hero区域 ==========
.hero-section {
  position: relative;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 120px 48px 80px;
  overflow: hidden;
}

.hero-bg {
  position: absolute;
  inset: 0;
  z-index: -1;

  .hero-gradient {
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, #065f46 0%, #047857 25%, #059669 50%, #10b981 75%, #34d399 100%);
  }

  .hero-pattern {
    position: absolute;
    inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.05'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
  }

  .hero-glow {
    position: absolute;
    top: 20%;
    left: 50%;
    transform: translateX(-50%);
    width: 800px;
    height: 800px;
    background: radial-gradient(circle, rgba(255, 255, 255, 0.15) 0%, transparent 70%);
    pointer-events: none;
  }
}

.hero-content {
  text-align: center;
  max-width: 900px;
  z-index: 1;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 20px;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(10px);
  border-radius: $radius-full;
  margin-bottom: 32px;
  border: 1px solid rgba(255, 255, 255, 0.2);

  .badge-icon {
    font-size: 16px;
  }

  .badge-text {
    font-size: 14px;
    font-weight: $font-weight-medium;
    color: white;
  }
}

.hero-title {
  font-size: 56px;
  font-weight: $font-weight-bold;
  color: white;
  line-height: 1.2;
  margin-bottom: 24px;
  letter-spacing: -0.02em;

  .text-gradient {
    background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 50%, #fcd34d 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
}

.hero-subtitle {
  font-size: 20px;
  color: rgba(255, 255, 255, 0.9);
  line-height: 1.6;
  margin-bottom: 48px;
  font-weight: $font-weight-normal;
}

.hero-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-bottom: 64px;
}

.btn-primary-lg {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 32px;
  font-size: 16px;
  font-weight: $font-weight-semibold;
  color: $primary-dark;
  background: white;
  border: none;
  border-radius: $radius-xl;
  cursor: pointer;
  transition: all $transition-base;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.1);

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
  }

  &:active {
    transform: translateY(0);
  }
}

.btn-secondary-lg {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 32px;
  font-size: 16px;
  font-weight: $font-weight-semibold;
  color: white;
  background: rgba(255, 255, 255, 0.15);
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: $radius-xl;
  cursor: pointer;
  transition: all $transition-base;
  backdrop-filter: blur(10px);

  &:hover {
    background: rgba(255, 255, 255, 0.25);
    border-color: rgba(255, 255, 255, 0.4);
  }
}

.hero-stats {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 32px;

  .hero-stat-item {
    text-align: center;
  }

  .stat-value {
    font-size: 36px;
    font-weight: $font-weight-bold;
    color: white;
    line-height: 1;

    .count-up {
      font-variant-numeric: tabular-nums;
    }
  }

  .stat-label {
    font-size: 14px;
    color: rgba(255, 255, 255, 0.8);
    margin-top: 8px;
  }

  .hero-stat-divider {
    width: 1px;
    height: 48px;
    background: rgba(255, 255, 255, 0.2);
  }
}

.hero-visual {
  position: absolute;
  top: 50%;
  right: 5%;
  transform: translateY(-50%);

  .floating-cards {
    position: relative;
    width: 300px;
    height: 400px;
  }

  .floating-card {
    position: absolute;
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(20px);
    border-radius: $radius-xl;
    padding: 20px;
    box-shadow: $shadow-xl;
    display: flex;
    align-items: center;
    gap: 12px;
    animation: float 4s ease-in-out infinite;

    &.card-1 {
      top: 0;
      left: 0;
      animation-delay: 0s;
    }

    &.card-2 {
      top: 120px;
      left: 80px;
      animation-delay: 0.5s;
    }

    &.card-3 {
      top: 240px;
      left: 20px;
      animation-delay: 1s;
    }

    .card-icon {
      width: 40px;
      height: 40px;
      background: $primary-gradient;
      border-radius: $radius-lg;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
      color: white;
    }

    .card-text {
      font-size: 14px;
      font-weight: $font-weight-medium;
      color: $text-primary;
    }
  }
}

.scroll-indicator {
  position: absolute;
  bottom: 40px;
  left: 50%;
  transform: translateX(-50%);
  color: rgba(255, 255, 255, 0.7);
  font-size: 24px;

  .bounce {
    animation: bounce 2s infinite;
  }
}

@keyframes bounce {
  0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-10px); }
  60% { transform: translateY(-5px); }
}

// ========== 功能特点 ==========
.features-section {
  padding: 120px 48px;
  background: $bg-primary;
}

.section-container {
  max-width: 1280px;
  margin: 0 auto;
}

.section-header {
  text-align: center;
  margin-bottom: 64px;
}

.section-title {
  font-size: 40px;
  font-weight: $font-weight-bold;
  color: $text-primary;
  margin-bottom: 16px;
}

.section-subtitle {
  font-size: 18px;
  color: $text-secondary;
  max-width: 600px;
  margin: 0 auto;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
}

.feature-card {
  background: white;
  border-radius: $radius-2xl;
  padding: 32px;
  border: 1px solid $border-light;
  transition: all $transition-base;
  animation: fadeIn 0.6s ease forwards;
  opacity: 0;

  &:hover {
    transform: translateY(-8px);
    box-shadow: $shadow-xl;
    border-color: transparent;
  }

  .feature-icon-wrapper {
    width: 64px;
    height: 64px;
    border-radius: $radius-xl;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 24px;

    .feature-icon {
      font-size: 32px;
      filter: grayscale(100%) brightness(200%);
    }
  }

  .feature-title {
    font-size: 20px;
    font-weight: $font-weight-semibold;
    color: $text-primary;
    margin-bottom: 12px;
  }

  .feature-desc {
    font-size: 14px;
    color: $text-secondary;
    line-height: 1.7;
    margin-bottom: 20px;
  }

  .feature-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .feature-tag {
    padding: 4px 12px;
    font-size: 12px;
    font-weight: $font-weight-medium;
    color: $primary-color;
    background: rgba($primary-color, 0.1);
    border-radius: $radius-full;
  }
}

// ========== 园林展示 ==========
.gardens-section {
  padding: 120px 48px;
  background: linear-gradient(180deg, $bg-primary 0%, $bg-secondary 100%);
}

.gardens-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
}

.garden-card {
  background: white;
  border-radius: $radius-2xl;
  overflow: hidden;
  border: 1px solid $border-light;
  cursor: pointer;
  transition: all $transition-base;

  &:hover {
    transform: translateY(-8px);
    box-shadow: $shadow-xl;

    .garden-overlay {
      opacity: 1;
    }

    .garden-image {
      transform: scale(1.1);
    }
  }

  .garden-image-wrapper {
    position: relative;
    height: 200px;
    overflow: hidden;

    .garden-image {
      width: 100%;
      height: 100%;
      object-fit: cover;
      transition: transform $transition-slow;
    }

    .garden-overlay {
      position: absolute;
      inset: 0;
      background: rgba($primary-color, 0.8);
      display: flex;
      align-items: center;
      justify-content: center;
      opacity: 0;
      transition: opacity $transition-base;

      .view-btn {
        padding: 12px 24px;
        font-size: 14px;
        font-weight: $font-weight-medium;
        color: white;
        background: rgba(255, 255, 255, 0.2);
        border: 2px solid white;
        border-radius: $radius-full;
        transition: all $transition-base;

        &:hover {
          background: white;
          color: $primary-dark;
        }
      }
    }
  }

  .garden-content {
    padding: 24px;
  }

  .garden-name {
    font-size: 18px;
    font-weight: $font-weight-semibold;
    color: $text-primary;
    margin-bottom: 8px;
  }

  .garden-desc {
    font-size: 14px;
    color: $text-secondary;
    line-height: 1.6;
    margin-bottom: 16px;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .garden-meta {
    display: flex;
    gap: 16px;

    .meta-item {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
      color: $text-secondary;
    }
  }
}

// ========== 工作流程 ==========
.workflow-section {
  padding: 120px 48px;
  background: white;
}

.workflow-timeline {
  position: relative;
  display: flex;
  justify-content: space-between;
  padding-top: 60px;

  .workflow-line {
    position: absolute;
    top: 80px;
    left: 60px;
    right: 60px;
    height: 3px;
    background: linear-gradient(90deg, $primary-light 0%, $primary-dark 100%);
    border-radius: $radius-full;

    &::before {
      content: '';
      position: absolute;
      top: 50%;
      left: 0;
      right: 0;
      height: 3px;
      background: inherit;
      animation: shimmer 2s infinite linear;
      background-size: 200% 100%;
    }
  }

  .workflow-step {
    position: relative;
    z-index: 1;
    text-align: center;

    .step-number {
      position: absolute;
      top: -60px;
      left: 50%;
      transform: translateX(-50%);
      width: 40px;
      height: 40px;
      background: $primary-gradient;
      color: white;
      font-size: 18px;
      font-weight: $font-weight-bold;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 4px 12px rgba($primary-color, 0.3);
    }

    .step-content {
      padding-top: 60px;
    }

    .step-icon {
      font-size: 48px;
      margin-bottom: 16px;
    }

    .step-title {
      font-size: 18px;
      font-weight: $font-weight-semibold;
      color: $text-primary;
      margin-bottom: 8px;
    }

    .step-desc {
      font-size: 14px;
      color: $text-secondary;
      max-width: 200px;
      margin: 0 auto;
    }
  }
}

// ========== 技术架构 ==========
.tech-section {
  padding: 120px 48px;
  background: $bg-secondary;
}

.tech-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 20px;
}

.tech-card {
  text-align: center;
  padding: 32px 16px;
  background: white;
  border-radius: $radius-xl;
  border: 1px solid $border-light;
  transition: all $transition-base;

  &:hover {
    transform: translateY(-4px);
    box-shadow: $shadow-lg;
  }

  .tech-icon-wrapper {
    width: 56px;
    height: 56px;
    margin: 0 auto 16px;
    background: $bg-secondary;
    border-radius: $radius-lg;
    display: flex;
    align-items: center;
    justify-content: center;

    .tech-icon {
      font-size: 28px;
    }
  }

  .tech-name {
    font-size: 15px;
    font-weight: $font-weight-semibold;
    color: $text-primary;
    margin-bottom: 8px;
  }

  .tech-desc {
    font-size: 13px;
    color: $text-secondary;
  }
}

// ========== 页脚 ==========
.footer {
  position: relative;
  background: $primary-dark;
  color: white;

  .footer-waves {
    position: absolute;
    top: -60px;
    left: 0;
    right: 0;
    height: 60px;
    color: $primary-dark;

    svg {
      width: 100%;
      height: 100%;
    }
  }

  .footer-content {
    max-width: 1280px;
    margin: 0 auto;
    padding: 60px 48px 40px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 24px;
  }

  .footer-brand {
    display: flex;
    align-items: center;
    gap: 12px;

    .brand-icon {
      width: 32px;
      height: 32px;
    }

    span {
      font-size: 18px;
      font-weight: $font-weight-semibold;
    }
  }

  .footer-links {
    display: flex;
    gap: 32px;

    a {
      font-size: 14px;
      color: rgba(255, 255, 255, 0.8);
      transition: color $transition-fast;

      &:hover {
        color: white;
      }
    }
  }

  .footer-copyright {
    padding-top: 24px;
    border-top: 1px solid rgba(255, 255, 255, 0.1);

    p {
      font-size: 13px;
      color: rgba(255, 255, 255, 0.6);
    }
  }
}

// ========== 响应式设计 ==========
@media (max-width: 1200px) {
  .features-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .gardens-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .tech-grid {
    grid-template-columns: repeat(3, 1fr);
  }

  .hero-visual {
    display: none;
  }
}

@media (max-width: 768px) {
  .navbar {
    padding: 0 24px;

    &-menu {
      display: none;
    }
  }

  .hero-section {
    padding: 100px 24px 60px;
  }

  .hero-title {
    font-size: 36px;
  }

  .hero-subtitle {
    font-size: 16px;
  }

  .hero-actions {
    flex-direction: column;

    button {
      width: 100%;
      justify-content: center;
    }
  }

  .hero-stats {
    flex-wrap: wrap;
    gap: 24px;

    .hero-stat-divider {
      display: none;
    }
  }

  .features-section,
  .gardens-section,
  .workflow-section,
  .tech-section {
    padding: 80px 24px;
  }

  .features-grid,
  .gardens-grid {
    grid-template-columns: 1fr;
  }

  .tech-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .workflow-timeline {
    flex-direction: column;
    padding-top: 0;

    .workflow-line {
      display: none;
    }

    .workflow-step {
      margin-bottom: 32px;

      .step-number {
        position: relative;
        top: 0;
        margin-bottom: 16px;
      }
    }
  }

  .section-title {
    font-size: 28px;
  }
}

// 动画
.animate-fade-in {
  opacity: 0;
  animation: fadeIn 0.8s ease forwards;
}
</style>
