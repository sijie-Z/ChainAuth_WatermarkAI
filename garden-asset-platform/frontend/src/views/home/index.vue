<template>
  <div class="home-page">
    <!-- 顶部导航 -->
    <header class="navbar" :class="{ 'navbar-scrolled': isScrolled }">
      <div class="navbar-container">
        <router-link to="/home" class="navbar-brand">
          <span class="brand-mark" aria-hidden="true">园</span>
          <span class="brand-text">
            <span class="brand-name">苏州园林数字资产</span>
            <span class="brand-sub">链上确权与溯源</span>
          </span>
        </router-link>

        <nav class="navbar-menu" aria-label="主导航">
          <router-link to="/home" class="nav-link">首页</router-link>
          <router-link to="/assets" class="nav-link">资产档案</router-link>
          <router-link to="/trace" class="nav-link">溯源查询</router-link>
          <template v-if="isLoggedIn">
            <router-link to="/license/my" class="nav-link">我的授权</router-link>
            <router-link v-if="isAdmin" to="/admin" class="nav-link">管理后台</router-link>
          </template>
        </nav>

        <div class="navbar-actions">
          <button
            class="mobile-nav-toggle"
            type="button"
            :aria-expanded="mobileNavOpen"
            aria-label="打开导航菜单"
            @click="mobileNavOpen = !mobileNavOpen"
          >
            <el-icon><Menu /></el-icon>
          </button>
          <template v-if="isLoggedIn">
            <el-dropdown trigger="click" @command="handleCommand">
              <button class="user-menu" type="button">
                <span class="user-initial">{{ username?.charAt(0)?.toUpperCase() }}</span>
                <span class="user-name">{{ username }}</span>
                <el-icon class="dropdown-arrow"><ArrowDown /></el-icon>
              </button>
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
            <router-link to="/register" class="btn-register">注册</router-link>
          </template>
        </div>
      </div>
    </header>

    <nav v-if="mobileNavOpen" class="mobile-nav" aria-label="移动端导航">
      <router-link to="/home" @click="mobileNavOpen = false">首页</router-link>
      <router-link to="/assets" @click="mobileNavOpen = false">资产档案</router-link>
      <router-link to="/trace" @click="mobileNavOpen = false">溯源查询</router-link>
      <router-link v-if="isLoggedIn" to="/license/my" @click="mobileNavOpen = false">我的授权</router-link>
      <router-link v-if="isAdmin" to="/admin" @click="mobileNavOpen = false">管理后台</router-link>
    </nav>

    <!-- Hero：月洞门与资产台账 -->
    <section class="hero-section lattice-light">
      <div class="hero-inner">
        <div class="hero-copy">
          <p class="hero-label">
            <span class="seal">苏州园林 · 数字资产档案</span>
          </p>

          <h1 class="hero-title">
            让每一件园林资产，<br />
            都有出处。
          </h1>

          <p class="hero-subtitle">
            数字水印嵌入，区块链存证，AI 侵权检测与全链路溯源——
            为苏州园林的影像、图纸与三维资产建立可验证的权属档案。
          </p>

          <div class="hero-actions">
            <button class="btn-primary" type="button" @click="goToAssets">
              进入资产档案
              <el-icon><ArrowRight /></el-icon>
            </button>
            <button class="btn-secondary" type="button" @click="goToTrace">
              <el-icon><Search /></el-icon>
              溯源查询
            </button>
          </div>
        </div>

        <div class="hero-visual" aria-hidden="true">
          <svg class="moon-gate" viewBox="0 0 560 560" fill="none">
            <defs>
              <clipPath id="gateClip">
                <circle cx="280" cy="280" r="196" />
              </clipPath>
              <linearGradient id="gateSky" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stop-color="#2c6657" />
                <stop offset="1" stop-color="#113f36" />
              </linearGradient>
            </defs>

            <circle cx="280" cy="280" r="236" stroke="rgba(252,253,251,.14)" />
            <circle cx="280" cy="280" r="218" stroke="rgba(252,253,251,.28)" stroke-width="2" />
            <circle cx="280" cy="280" r="196" fill="url(#gateSky)" stroke="rgba(252,253,251,.42)" stroke-width="2" />

            <g clip-path="url(#gateClip)">
              <circle cx="382" cy="186" r="46" fill="rgba(252,253,251,.16)" stroke="rgba(252,253,251,.32)" />
              <path d="M52 344c62-44 116-44 176-12 52 28 96 26 148-6 48-29 86-26 140 6v240H52z" fill="#1b4a40" />
              <path d="M22 396c74-34 136-22 198 10 62 32 112 22 164-10 52-32 94-22 146 10v154H22z" fill="#123a32" />
              <path d="M74 424h412M104 452h352M132 480h296M160 508h240" stroke="rgba(252,253,251,.16)" />
              <!-- 亭与廊 -->
              <path d="M160 344l62-48 62 48v10H160z" fill="#092722" />
              <path d="M182 354h80v74h-80z" fill="#092722" />
              <path d="M198 378h18v50h-18zM228 378h18v50h-18z" fill="rgba(252,253,251,.07)" />
              <path d="M356 372l40-30 40 30v8h-80z" fill="#092722" />
              <path d="M370 380h52v48h-52z" fill="#092722" />
            </g>

            <!-- 窗棂环 -->
            <g stroke="rgba(252,253,251,.14)">
              <circle cx="280" cy="280" r="252" />
              <circle cx="280" cy="280" r="260" stroke-dasharray="2 7" />
            </g>
            <g stroke="rgba(252,253,251,.10)">
              <path d="M280 20v28M280 512v28M20 280h28M512 280h28" />
            </g>

            <!-- 朱砂印章 -->
            <g transform="rotate(-6 456 132)">
              <rect x="432" y="108" width="48" height="48" rx="3" fill="#a6402f" />
              <text
                x="456"
                y="141"
                text-anchor="middle"
                fill="#fcfdfb"
                font-family="'Noto Serif SC','Songti SC','STSong','SimSun',serif"
                font-size="24"
              >园</text>
            </g>
          </svg>
          <p class="gate-caption">拙政园 · 见山楼 · 数字档案</p>
        </div>
      </div>

      <div class="hero-ledger">
        <div class="ledger-item">
          <span class="ledger-value">{{ statsLoaded ? animatedStats.assets : '—' }}</span>
          <span class="ledger-label">数字资产</span>
        </div>
        <div class="ledger-item">
          <span class="ledger-value">{{ statsLoaded ? animatedStats.watermarked : '—' }}</span>
          <span class="ledger-label">水印确权</span>
        </div>
        <div class="ledger-item">
          <span class="ledger-value">{{ statsLoaded ? animatedStats.chained : '—' }}</span>
          <span class="ledger-label">链上存证</span>
        </div>
        <div class="ledger-item">
          <span class="ledger-value">{{ statsLoaded ? animatedStats.licenses : '—' }}</span>
          <span class="ledger-label">授权记录</span>
        </div>
      </div>
    </section>

    <!-- 四道工序 -->
    <section class="workflow-section">
      <div class="section-container">
        <header class="section-header">
          <h2 class="section-title">一件资产的四道工序</h2>
          <p class="section-subtitle">从上传到授权，每一步都留下可核验的记录。</p>
        </header>

        <ol class="workflow-list">
          <li class="workflow-step" v-for="(step, index) in workflowSteps" :key="step.title">
            <span class="step-index">{{ String(index + 1).padStart(2, '0') }}</span>
            <div class="step-body">
              <h3 class="step-title">{{ step.title }}</h3>
              <p class="step-desc">{{ step.description }}</p>
            </div>
          </li>
        </ol>
      </div>
    </section>

    <!-- 能力 -->
    <section class="features-section">
      <div class="section-container">
        <header class="section-header">
          <h2 class="section-title">四类保护能力</h2>
          <p class="section-subtitle">水印、存证、检测、溯源，构成完整的证据链。</p>
        </header>

        <div class="features-grid">
          <article class="feature-item" v-for="feature in features" :key="feature.title">
            <div class="feature-head">
              <el-icon class="feature-icon"><component :is="feature.icon" /></el-icon>
              <h3 class="feature-title">{{ feature.title }}</h3>
            </div>
            <p class="feature-desc">{{ feature.description }}</p>
            <ul class="feature-tags">
              <li v-for="tag in feature.tags" :key="tag">{{ tag }}</li>
            </ul>
          </article>
        </div>
      </div>
    </section>

    <!-- 园林档案 -->
    <section class="gardens-section">
      <div class="section-container">
        <header class="section-header section-header-row">
          <div>
            <h2 class="section-title">园林档案</h2>
            <p class="section-subtitle">世界文化遗产的数字化切片，按园收录。</p>
          </div>
          <router-link to="/assets" class="section-link">
            查看全部资产
            <el-icon><ArrowRight /></el-icon>
          </router-link>
        </header>

        <div class="gardens-grid" v-if="gardens.length">
          <article
            class="garden-card"
            v-for="(garden, index) in gardens"
            :key="garden.id"
            :class="{ featured: index === 0 }"
            @click="goToGarden(garden.id)"
          >
            <div class="garden-visual">
              <img
                v-if="garden.cover_image"
                :src="garden.cover_image"
                :alt="garden.name"
                class="garden-image"
              />
              <div v-else class="garden-placeholder lattice">
                <span class="garden-glyph">{{ garden.name?.charAt(0) }}</span>
                <span class="garden-code">{{ garden.code }}</span>
              </div>
              <span class="garden-count">{{ garden.asset_count || 0 }} 件资产</span>
            </div>
            <div class="garden-body">
              <h3 class="garden-name">{{ garden.name }}</h3>
              <p class="garden-desc">{{ garden.description }}</p>
              <span class="garden-location">
                <el-icon><Location /></el-icon>
                {{ garden.location || '苏州' }}
              </span>
            </div>
          </article>
        </div>

        <div v-else class="garden-empty">
          <p>暂无园林数据。启动后端并执行 <code>flask seed</code> 后即可看到档案。</p>
        </div>
      </div>
    </section>

    <!-- 技术台账 -->
    <section class="tech-section">
      <div class="section-container">
        <header class="section-header">
          <h2 class="section-title">技术台账</h2>
          <p class="section-subtitle">所有组件均可本地部署，数据不出内网。</p>
        </header>

        <dl class="tech-ledger">
          <div class="tech-row" v-for="tech in techStack" :key="tech.name">
            <dt class="tech-name">{{ tech.name }}</dt>
            <dd class="tech-desc">{{ tech.description }}</dd>
            <span class="tech-role">{{ tech.role }}</span>
          </div>
        </dl>
      </div>
    </section>

    <footer class="footer">
      <div class="footer-content">
        <div class="footer-brand">
          <span class="brand-mark">园</span>
          <div>
            <p class="footer-name">苏州园林数字资产平台</p>
            <p class="footer-note">数字水印 · 区块链存证 · AI 溯源</p>
          </div>
        </div>
        <nav class="footer-links" aria-label="页脚导航">
          <router-link to="/home">首页</router-link>
          <router-link to="/assets">资产档案</router-link>
          <router-link to="/trace">溯源查询</router-link>
          <router-link to="/login">登录</router-link>
        </nav>
        <p class="footer-copyright">
          © 2026 苏州园林数字资产平台团队 · 苏州大学计算机科学与技术学院
        </p>
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
  Location, Stamp, Link, Aim, Guide, Menu
} from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()

const gardens = ref([])
const isScrolled = ref(false)
const mobileNavOpen = ref(false)
const statsLoaded = ref(false)
const animatedStats = ref({
  assets: 0,
  watermarked: 0,
  chained: 0,
  licenses: 0
})

const features = [
  {
    icon: Stamp,
    title: '水印确权',
    description: '自研鲁棒水印算法，将资产唯一标识隐式嵌入影像与矢量数据，抗压缩、抗裁剪。',
    tags: ['DCT 频域', '矢量坐标扰动', 'NC 完整性校验']
  },
  {
    icon: Link,
    title: '区块链存证',
    description: '资产与授权信息写入 FISCO BCOS 联盟链，形成不可篡改的存证记录与电子证书。',
    tags: ['联盟链', '存证证书', '哈希校验']
  },
  {
    icon: Aim,
    title: 'AI 侵权检测',
    description: '基于 CLIP 特征与向量检索，在海量图像中定位相似资产，辅助人工判定侵权。',
    tags: ['CLIP 特征', 'Milvus 检索', '相似度评分']
  },
  {
    icon: Guide,
    title: '全链路溯源',
    description: '从上传、嵌入、存证到授权分发，每一次流转都记录在案，可回溯完整证据链。',
    tags: ['流转记录', '授权合同', '溯源报告']
  }
]

const workflowSteps = [
  { title: '上传资产', description: '影像、三维模型或矢量图纸进入档案库，生成唯一资产编码。' },
  { title: '嵌入水印', description: '按资产类型选择 DCT 或坐标扰动算法，写入可提取的水印标识。' },
  { title: '链上存证', description: '文件哈希与水印信息写入联盟链，签发可验证的存证证书。' },
  { title: '授权分发', description: '双重审批通过后发放授权，下载与使用记录持续回流台账。' }
]

const techStack = [
  { name: 'Vue 3 + Vite', description: '响应式前端与按需构建', role: '展示层' },
  { name: 'Flask + SQLAlchemy', description: 'REST API 与业务服务', role: '服务层' },
  { name: 'PostgreSQL / Redis', description: '主数据与缓存限流', role: '数据层' },
  { name: 'FISCO BCOS', description: '国产联盟链存证与合约', role: '信任层' },
  { name: 'GLM-4V / CLIP / Milvus', description: '视觉理解与向量检索', role: '智能层' },
  { name: 'Docker Compose', description: '一键部署与健康检查', role: '运行层' }
]

const isLoggedIn = computed(() => userStore.isLoggedIn)
const isAdmin = computed(() => ['admin', 'adm1', 'adm2', 'adm3'].includes(userStore.userRole))
const username = computed(() => userStore.username)

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
      if (d.gardens?.length) {
        gardens.value = d.gardens.slice(0, 4)
      }
      statsLoaded.value = true
    }
  } catch {
    // 后端未启动时保持 0，不伪造数据
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
    if (gardens.value.length === 0) {
      gardens.value = [
        { id: 1, name: '拙政园', code: 'ZZY', description: '中国四大名园之首，以水景与远借塔影著称。', asset_count: 0, location: '姑苏区' },
        { id: 2, name: '留园', code: 'LY', description: '以建筑空间与太湖石闻名，廊院层次丰富。', asset_count: 0, location: '姑苏区' },
        { id: 3, name: '狮子林', code: 'SZL', description: '假山迷宫与湖石景观的代表。', asset_count: 0, location: '姑苏区' },
        { id: 4, name: '沧浪亭', code: 'CLT', description: '苏州现存最古老的园林，以复廊借景见长。', asset_count: 0, location: '姑苏区' }
      ]
    }
  }
}

function animateNumbers() {
  const targets = statsTargets.value
  const duration = 1200
  const steps = 40
  const interval = duration / steps

  Object.keys(targets).forEach(key => {
    const target = targets[key]
    if (!target) {
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

function handleScroll() {
  isScrolled.value = window.scrollY > 16
}

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
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.home-page {
  min-height: 100vh;
  background: $bg-primary;
  overflow-x: hidden;
}

// ========== 导航栏 ==========
.navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: $z-fixed;
  height: $header-height;
  padding: 0 40px;
  background: transparent;
  border-bottom: 1px solid transparent;
  transition: background $transition-base, border-color $transition-base;

  &-container {
    max-width: 1320px;
    margin: 0 auto;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 24px;
  }

  &.navbar-scrolled {
    background: rgba(252, 253, 251, 0.94);
    backdrop-filter: $glass-blur;
    border-bottom-color: $border-light;

    .brand-mark {
      border-color: $border-color;
      background: $bg-secondary;
      color: $primary-dark;
    }
    .brand-name { color: $text-primary; }
    .brand-sub { color: $text-secondary; }
    .nav-link { color: $text-secondary; }
    .nav-link:hover,
    .nav-link.router-link-active { color: $primary-dark; }
    .btn-login { color: $text-primary; }
    .btn-register {
      background: $primary-color;
      border-color: $primary-dark;
      color: #fcfdfb;
    }
    .user-name { color: $text-primary; }
    .user-menu { border-color: $border-color; }
    .user-initial { color: #fcfdfb; }
    .mobile-nav-toggle {
      border-color: $border-color;
      color: $text-primary;
    }
  }
}

.navbar-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;

  .brand-mark {
    width: 38px;
    height: 38px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: 1px solid rgba(252, 253, 251, 0.5);
    border-radius: $radius-xs;
    color: #fcfdfb;
    font-family: $font-display;
    font-size: 20px;
    line-height: 1;
    background: rgba(252, 253, 251, 0.08);
  }

  .brand-text {
    display: flex;
    flex-direction: column;
    line-height: 1.25;
  }

  .brand-name {
    font-family: $font-display;
    font-size: 17px;
    font-weight: 600;
    color: #fcfdfb;
    letter-spacing: 0.04em;
    white-space: nowrap;
  }

  .brand-sub {
    font-size: 11px;
    color: rgba(252, 253, 251, 0.65);
    letter-spacing: 0.16em;
  }
}

.navbar-menu {
  display: flex;
  align-items: center;
  gap: 4px;

  .nav-link {
    padding: 8px 14px;
    font-size: 14px;
    color: rgba(252, 253, 251, 0.82);
    border-radius: $radius-sm;
    transition: color $transition-fast, background $transition-fast;

    &:hover {
      color: #fcfdfb;
      background: rgba(252, 253, 251, 0.08);
    }

    &.router-link-active {
      color: #fcfdfb;
    }
  }
}

.navbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.mobile-nav-toggle {
  display: none;
  width: 38px;
  height: 38px;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid rgba(252, 253, 251, 0.28);
  border-radius: $radius-sm;
  color: #fcfdfb;
  font-size: 18px;
  cursor: pointer;
}

.mobile-nav {
  position: fixed;
  top: $header-height;
  left: 0;
  right: 0;
  z-index: 999;
  display: flex;
  flex-direction: column;
  background: $bg-card;
  border-bottom: 1px solid $border-color;
  box-shadow: $shadow-lg;

  a {
    padding: 14px 20px;
    font-size: 15px;
    color: $text-primary;
    border-bottom: 1px solid $border-light;

    &:last-child { border-bottom: none; }
    &:hover { background: $bg-hover; }
  }
}

.btn-login {
  padding: 8px 14px;
  font-size: 14px;
  color: rgba(252, 253, 251, 0.9);

  &:hover { color: #fcfdfb; }
}

.btn-register {
  padding: 8px 18px;
  font-size: 14px;
  color: $primary-dark;
  background: #fcfdfb;
  border: 1px solid #fcfdfb;
  border-radius: $radius-sm;

  &:hover {
    background: $bg-secondary;
    color: $primary-dark;
  }
}

.user-menu {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 10px 5px 5px;
  background: transparent;
  border: 1px solid rgba(252, 253, 251, 0.28);
  border-radius: $radius-full;
  cursor: pointer;

  .user-initial {
    width: 28px;
    height: 28px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    background: $accent-color;
    color: #fcfdfb;
    font-family: $font-display;
    font-size: 14px;
  }

  .user-name {
    font-size: 13px;
    color: #fcfdfb;
  }

  .dropdown-arrow {
    font-size: 12px;
    color: rgba(252, 253, 251, 0.7);
  }
}

// ========== Hero ==========
.hero-section {
  position: relative;
  background: $primary-dark;
  color: #fcfdfb;
  padding: 128px 40px 0;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    background: radial-gradient(circle at 68% 42%, rgba(91, 146, 127, 0.22) 0%, transparent 58%);
    pointer-events: none;
  }
}

.hero-inner {
  position: relative;
  max-width: 1320px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr);
  align-items: center;
  gap: 64px;
  padding-bottom: 96px;
}

.hero-copy {
  max-width: 620px;
}

.hero-label {
  margin-bottom: 28px;
}

.hero-label .seal {
  border-color: rgba(252, 253, 251, 0.34);
  color: rgba(252, 253, 251, 0.86);
}

.hero-title {
  font-family: $font-display;
  font-size: clamp(36px, 4.2vw, 56px);
  font-weight: 600;
  line-height: 1.28;
  letter-spacing: 0.02em;
  color: #fcfdfb;
  margin-bottom: 24px;
  animation: inkReveal 1.1s cubic-bezier(0.22, 1, 0.36, 1) both;
}

.hero-subtitle {
  font-size: 16px;
  line-height: 1.9;
  color: rgba(252, 253, 251, 0.72);
  max-width: 34em;
  margin-bottom: 36px;
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 13px 26px;
  font-size: 15px;
  font-weight: 500;
  color: $primary-dark;
  background: #fcfdfb;
  border: 1px solid #fcfdfb;
  border-radius: $radius-sm;
  cursor: pointer;
  transition: background $transition-fast;

  &:hover {
    background: $bg-secondary;
  }
}

.btn-secondary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 13px 24px;
  font-size: 15px;
  color: #fcfdfb;
  background: transparent;
  border: 1px solid rgba(252, 253, 251, 0.3);
  border-radius: $radius-sm;
  cursor: pointer;

  &:hover {
    border-color: rgba(252, 253, 251, 0.6);
    background: rgba(252, 253, 251, 0.06);
  }
}

.hero-visual {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;

  .moon-gate {
    width: min(100%, 520px);
    height: auto;
    animation: fadeIn 1.4s ease both;
  }

  .gate-caption {
    margin-top: 12px;
    font-size: 12px;
    letter-spacing: 0.18em;
    color: rgba(252, 253, 251, 0.5);
  }
}

.hero-ledger {
  position: relative;
  max-width: 1320px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  border-top: 1px solid rgba(252, 253, 251, 0.16);

  .ledger-item {
    padding: 24px 8px 28px;
    display: flex;
    flex-direction: column;
    gap: 6px;

    & + .ledger-item {
      border-left: 1px solid rgba(252, 253, 251, 0.12);
      padding-left: 32px;
    }
  }

  .ledger-value {
    font-family: $font-display;
    font-size: 34px;
    font-weight: 600;
    line-height: 1;
    font-variant-numeric: tabular-nums;
    color: #fcfdfb;
  }

  .ledger-label {
    font-size: 12px;
    letter-spacing: 0.14em;
    color: rgba(252, 253, 251, 0.55);
  }
}

// ========== 通用区块 ==========
.section-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 40px;
}

.section-header {
  margin-bottom: 48px;

  &-row {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 24px;
  }
}

.section-title {
  font-size: clamp(26px, 3vw, 36px);
  font-weight: 600;
  color: $text-primary;
  margin-bottom: 12px;
}

.section-subtitle {
  font-size: 15px;
  color: $text-secondary;
  max-width: 36em;
}

.section-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: $primary-color;
  white-space: nowrap;

  &:hover { color: $primary-dark; }
}

// ========== 四道工序 ==========
.workflow-section {
  padding: 96px 0;
  background: $bg-card;
  border-bottom: 1px solid $border-light;
}

.workflow-list {
  list-style: none;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  border-top: 1px solid $border-color;
}

.workflow-step {
  padding: 28px 24px 8px 0;
  border-right: 1px solid $border-light;

  &:last-child {
    border-right: none;
    padding-right: 0;
  }

  & + .workflow-step {
    padding-left: 24px;
  }

  .step-index {
    display: block;
    font-family: $font-mono;
    font-size: 13px;
    color: $accent-color;
    letter-spacing: 0.08em;
    margin-bottom: 18px;
  }

  .step-title {
    font-size: 19px;
    font-weight: 600;
    margin-bottom: 8px;
  }

  .step-desc {
    font-size: 14px;
    line-height: 1.8;
    color: $text-secondary;
  }
}

// ========== 能力 ==========
.features-section {
  padding: 96px 0;
  background: $bg-primary;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0;
  border-top: 1px solid $border-color;
  border-left: 1px solid $border-color;
}

.feature-item {
  padding: 32px;
  border-right: 1px solid $border-color;
  border-bottom: 1px solid $border-color;
  background: $bg-card;

  .feature-head {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 14px;
  }

  .feature-icon {
    width: 36px;
    height: 36px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: 1px solid $border-color;
    border-radius: $radius-xs;
    color: $primary-color;
    font-size: 18px;
    background: $bg-secondary;
  }

  .feature-title {
    font-size: 20px;
    font-weight: 600;
  }

  .feature-desc {
    font-size: 14px;
    line-height: 1.85;
    color: $text-secondary;
    margin-bottom: 20px;
    max-width: 38em;
  }

  .feature-tags {
    list-style: none;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;

    li {
      font-family: $font-mono;
      font-size: 11px;
      letter-spacing: 0.04em;
      color: $text-secondary;
      padding: 3px 8px;
      border: 1px solid $border-light;
      border-radius: $radius-xs;
      background: $bg-primary;
    }
  }
}

// ========== 园林档案 ==========
.gardens-section {
  padding: 96px 0;
  background: $bg-card;
  border-top: 1px solid $border-light;
  border-bottom: 1px solid $border-light;
}

.gardens-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  grid-auto-rows: minmax(180px, auto);
  gap: 16px;
}

.garden-card {
  grid-column: span 1;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  overflow: hidden;
  background: $bg-primary;
  cursor: pointer;
  transition: border-color $transition-fast, box-shadow $transition-fast;

  &.featured {
    grid-column: span 2;
    grid-row: span 2;
  }

  &:hover {
    border-color: $border-dark;
    box-shadow: $shadow-md;

    .garden-image,
    .garden-placeholder {
      transform: scale(1.02);
    }
  }

  .garden-visual {
    position: relative;
    height: 180px;
    overflow: hidden;
    background: $primary-dark;

    .garden-image,
    .garden-placeholder {
      width: 100%;
      height: 100%;
      transition: transform $transition-slow;
    }

    .garden-image { object-fit: cover; }

    .garden-placeholder {
      display: flex;
      align-items: center;
      justify-content: center;
      background-color: $primary-dark;
      color: rgba(252, 253, 251, 0.9);
    }

    .garden-glyph {
      font-family: $font-display;
      font-size: 72px;
      line-height: 1;
      opacity: 0.9;
    }

    .garden-code {
      position: absolute;
      right: 14px;
      bottom: 10px;
      font-family: $font-mono;
      font-size: 11px;
      letter-spacing: 0.18em;
      color: rgba(252, 253, 251, 0.55);
    }

    .garden-count {
      position: absolute;
      top: 12px;
      left: 12px;
      padding: 3px 8px;
      font-size: 11px;
      color: #fcfdfb;
      background: rgba(14, 59, 51, 0.72);
      border: 1px solid rgba(252, 253, 251, 0.2);
      border-radius: $radius-xs;
      backdrop-filter: blur(6px);
    }
  }

  .garden-body {
    padding: 16px 18px 18px;
  }

  .garden-name {
    font-size: 19px;
    font-weight: 600;
    margin-bottom: 6px;
  }

  .garden-desc {
    font-size: 13px;
    line-height: 1.7;
    color: $text-secondary;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    margin-bottom: 10px;
  }

  .garden-location {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    color: $text-placeholder;
  }

  &.featured {
    position: relative;

    .garden-visual {
      height: 100%;
      min-height: 360px;
    }

    .garden-glyph { font-size: 120px; }

    .garden-body {
      position: absolute;
      left: 0;
      right: 0;
      bottom: 0;
      padding: 20px;
      background: linear-gradient(180deg, transparent 0%, rgba(14, 59, 51, 0.86) 55%);
      color: #fcfdfb;

      .garden-name { color: #fcfdfb; font-size: 26px; }
      .garden-desc { color: rgba(252, 253, 251, 0.75); }
      .garden-location { color: rgba(252, 253, 251, 0.6); }
    }
  }
}

.garden-empty {
  padding: 32px;
  border: 1px dashed $border-color;
  border-radius: $radius-md;
  color: $text-secondary;
  font-size: 14px;

  code {
    font-family: $font-mono;
    font-size: 12px;
    padding: 2px 6px;
    background: $bg-secondary;
    border-radius: $radius-xs;
  }
}

// ========== 技术台账 ==========
.tech-section {
  padding: 96px 0;
  background: $bg-primary;
}

.tech-ledger {
  border-top: 1px solid $border-color;
}

.tech-row {
  display: grid;
  grid-template-columns: minmax(180px, 1.1fr) minmax(0, 2fr) minmax(80px, 0.4fr);
  align-items: baseline;
  gap: 24px;
  padding: 18px 4px;
  border-bottom: 1px solid $border-light;

  .tech-name {
    font-family: $font-display;
    font-size: 17px;
    font-weight: 600;
    color: $text-primary;
  }

  .tech-desc {
    font-size: 14px;
    color: $text-secondary;
  }

  .tech-role {
    justify-self: end;
    font-size: 11px;
    letter-spacing: 0.14em;
    color: $text-placeholder;
  }
}

// ========== 页脚 ==========
.footer {
  background: $primary-dark;
  color: rgba(252, 253, 251, 0.72);
  padding: 48px 40px 32px;

  .footer-content {
    max-width: 1200px;
    margin: 0 auto;
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 32px;
    align-items: start;
  }

  .footer-brand {
    display: flex;
    align-items: center;
    gap: 12px;

    .brand-mark {
      width: 40px;
      height: 40px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border: 1px solid rgba(252, 253, 251, 0.35);
      border-radius: $radius-xs;
      font-family: $font-display;
      font-size: 20px;
      color: #fcfdfb;
    }
  }

  .footer-name {
    font-family: $font-display;
    font-size: 16px;
    color: #fcfdfb;
    margin-bottom: 4px;
  }

  .footer-note {
    font-size: 12px;
    letter-spacing: 0.12em;
    color: rgba(252, 253, 251, 0.5);
  }

  .footer-links {
    display: flex;
    gap: 24px;

    a {
      font-size: 13px;
      color: rgba(252, 253, 251, 0.68);

      &:hover { color: #fcfdfb; }
    }
  }

  .footer-copyright {
    grid-column: 1 / -1;
    padding-top: 20px;
    border-top: 1px solid rgba(252, 253, 251, 0.12);
    font-size: 12px;
    color: rgba(252, 253, 251, 0.42);
  }
}

// ========== 响应式 ==========
@media (max-width: 1100px) {
  .hero-inner {
    grid-template-columns: 1fr;
    gap: 40px;
  }

  .hero-visual {
    order: -1;
    .moon-gate { width: min(70vw, 380px); }
  }

  .workflow-list {
    grid-template-columns: repeat(2, 1fr);
  }

  .workflow-step {
    border-right: none;
    border-bottom: 1px solid $border-light;
    padding: 24px 24px 20px 0;

    & + .workflow-step { padding-left: 0; }
  }

  .gardens-grid {
    grid-template-columns: repeat(2, 1fr);

    .garden-card.featured {
      grid-column: span 2;
      grid-row: span 1;
      .garden-visual { min-height: 260px; }
    }
  }
}

@media (max-width: 768px) {
  .navbar { padding: 0 20px; }
  .navbar-menu { display: none; }
  .brand-sub { display: none; }
  .mobile-nav-toggle { display: inline-flex; }

  .hero-section { padding: 88px 20px 0; }
  .hero-title { font-size: 32px; }
  .hero-ledger {
    grid-template-columns: repeat(2, 1fr);

    .ledger-item:nth-child(3) { border-left: none; }
    .ledger-item:nth-child(3),
    .ledger-item:nth-child(4) { border-top: 1px solid rgba(252, 253, 251, 0.12); }
  }

  .section-container { padding: 0 20px; }
  .workflow-section,
  .features-section,
  .gardens-section,
  .tech-section { padding: 64px 0; }

  .workflow-list { grid-template-columns: 1fr; }
  .features-grid { grid-template-columns: 1fr; }
  .gardens-grid { grid-template-columns: 1fr; }
  .garden-card.featured { grid-column: span 1; }

  .tech-row {
    grid-template-columns: 1fr;
    gap: 4px;
    .tech-role { justify-self: start; }
  }

  .footer { padding: 40px 20px 24px; }
  .footer-content { grid-template-columns: 1fr; }
}

@media (prefers-reduced-motion: reduce) {
  .hero-title { animation: none; }
  .moon-gate { animation: none; }
}
</style>
