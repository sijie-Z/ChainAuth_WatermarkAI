<template>
  <Teleport to="body">
    <transition name="palette-fade">
      <div v-if="visible" class="palette-backdrop" role="presentation" @mousedown.self="close">
        <section class="palette" role="dialog" aria-modal="true" aria-label="全局搜索与快捷导航" @keydown.tab="handleTab">
          <header class="palette-search">
            <el-icon class="search-icon"><Search /></el-icon>
            <input
              ref="inputRef"
              v-model="query"
              type="text"
              class="palette-input"
              placeholder="搜索资产、园林，或跳转到页面…"
              aria-label="搜索资产、园林或页面"
              autocomplete="off"
              @keydown.down.prevent="move(1)"
              @keydown.up.prevent="move(-1)"
              @keydown.enter.prevent="selectActive"
              @keydown.esc.prevent="close"
            />
            <kbd class="palette-kbd">Esc</kbd>
          </header>

          <div class="palette-body" role="listbox" aria-label="搜索结果">
            <p v-if="loading" class="palette-status">正在搜索…</p>

            <template v-for="group in groups" :key="group.label">
              <div v-if="group.items.length" class="palette-group">
                <p class="palette-group-label">{{ group.label }}</p>
                <button
                  v-for="item in group.items"
                  :key="item.id"
                  type="button"
                  class="palette-item"
                  :class="{ active: item._index === activeIndex }"
                  role="option"
                  :aria-selected="item._index === activeIndex"
                  @mouseenter="activeIndex = item._index"
                  @click="run(item)"
                >
                  <span class="item-icon" :class="item.tone">
                    <el-icon><component :is="item.icon" /></el-icon>
                  </span>
                  <span class="item-text">
                    <span class="item-title">{{ item.title }}</span>
                    <span v-if="item.subtitle" class="item-subtitle">{{ item.subtitle }}</span>
                  </span>
                  <span v-if="item.hint" class="item-hint">{{ item.hint }}</span>
                </button>
              </div>
            </template>

            <div v-if="!loading && flatItems.length === 0" class="palette-empty">
              <el-icon><Search /></el-icon>
              <span>没有找到匹配的页面、资产或园林</span>
            </div>
          </div>

          <footer class="palette-footer">
            <span><kbd>↑</kbd><kbd>↓</kbd> 选择</span>
            <span><kbd>Enter</kbd> 打开</span>
            <span><kbd>Esc</kbd> 关闭</span>
            <span class="footer-brand">苏州园林数字资产</span>
          </footer>
        </section>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  Collection,
  Cpu,
  DataLine,
  Document,
  Download,
  HomeFilled,
  Picture,
  Place,
  Search,
  Setting,
  Star,
  Upload
} from '@element-plus/icons-vue'
import { assetApi, gardenApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const visible = ref(false)
const query = ref('')
const activeIndex = ref(0)
const inputRef = ref(null)
const loading = ref(false)
const assetResults = ref([])
const gardens = ref([])
const gardensLoaded = ref(false)
const previousFocus = ref(null)

const ADMIN_ROLES = ['admin', 'asset_admin', 'license_admin', 'adm1', 'adm2']
const isLoggedIn = computed(() => userStore.isLoggedIn)
const isAdmin = computed(() => ADMIN_ROLES.includes(userStore.userRole))

const pageActions = computed(() => {
  const actions = [
    {
      id: 'page-home',
      title: '首页',
      subtitle: '平台概览与园林导览',
      path: '/home',
      icon: HomeFilled,
      tone: 'primary',
      keywords: 'home 首页'
    },
    {
      id: 'page-assets',
      title: '资产档案',
      subtitle: '浏览、搜索已发布资产',
      path: '/assets',
      icon: Picture,
      tone: 'primary',
      keywords: 'assets 资产 档案',
      auth: true
    },
    {
      id: 'page-trace',
      title: '溯源查询',
      subtitle: '上传图片或输入水印编号',
      path: '/trace',
      icon: Search,
      tone: 'secondary',
      keywords: 'trace 溯源 核验'
    },
    {
      id: 'page-watermark-lab',
      title: '水印实验室',
      subtitle: '真实执行压缩、噪声与缩放攻击',
      path: '/watermark-lab',
      icon: Cpu,
      tone: 'accent',
      auth: true,
      keywords: 'watermark lab 水印 鲁棒性 实验 PSNR NC'
    },
    {
      id: 'page-verify-package',
      title: '证据包核验',
      subtitle: '上传 ZIP 核对完整性与平台登记',
      path: '/verify-package',
      icon: Document,
      tone: 'secondary',
      keywords: 'evidence verify 证据包 核验 ZIP SHA256'
    },
    {
      id: 'page-guide',
      title: '使用指南',
      subtitle: '三分钟了解完整流程',
      path: '/guide',
      icon: Document,
      tone: 'neutral',
      keywords: 'guide 文档 帮助'
    },
    {
      id: 'page-my-assets',
      title: '我的资产',
      subtitle: '草稿、待审、已发布',
      path: '/my-assets',
      icon: Collection,
      tone: 'primary',
      auth: true,
      keywords: 'my assets 我的 上传'
    },
    {
      id: 'page-favorites',
      title: '我的收藏',
      subtitle: '收藏的园林资产',
      path: '/favorites',
      icon: Star,
      tone: 'accent',
      auth: true,
      keywords: 'favorites 收藏'
    },
    {
      id: 'page-collections',
      title: '我的合集',
      subtitle: '按主题组织的资产合集',
      path: '/collections',
      icon: Collection,
      tone: 'secondary',
      auth: true,
      keywords: 'collections 合集 策展'
    },
    {
      id: 'page-downloads',
      title: '下载记录',
      subtitle: '授权下载与使用台账',
      path: '/downloads',
      icon: Download,
      tone: 'secondary',
      auth: true,
      keywords: 'downloads 下载 记录'
    },
    {
      id: 'page-licenses',
      title: '我的授权',
      subtitle: '授权记录与申请进度',
      path: '/license/my',
      icon: Document,
      tone: 'secondary',
      auth: true,
      keywords: 'license 授权 申请'
    },
    {
      id: 'page-upload',
      title: '上传资产',
      subtitle: '上传影像、图纸或三维模型',
      path: '/assets/upload',
      icon: Upload,
      tone: 'accent',
      auth: true,
      keywords: 'upload 上传'
    },
    {
      id: 'page-settings',
      title: '账号设置',
      subtitle: '个人资料与密码',
      path: '/settings',
      icon: Setting,
      tone: 'neutral',
      auth: true,
      keywords: 'settings 设置'
    },
    {
      id: 'page-admin',
      title: '管理后台',
      subtitle: '仪表盘与审批工作台',
      path: '/admin',
      icon: DataLine,
      tone: 'primary',
      admin: true,
      keywords: 'admin 后台 管理'
    },
    {
      id: 'page-admin-assets',
      title: '资产审核',
      subtitle: '发布审核与批量水印/上链',
      path: '/admin/assets',
      icon: Picture,
      tone: 'primary',
      admin: true,
      keywords: 'admin assets 审核'
    },
    {
      id: 'page-admin-license',
      title: '授权待审批',
      subtitle: '一级审批与二级复核',
      path: '/admin/license/pending',
      icon: Document,
      tone: 'accent',
      admin: true,
      keywords: 'admin license 审批'
    },
    {
      id: 'page-admin-gardens',
      title: '园林档案维护',
      subtitle: '新建、编辑园林基础资料',
      path: '/admin/gardens',
      icon: Place,
      tone: 'secondary',
      admin: true,
      roles: ['admin', 'asset_admin'],
      keywords: 'admin gardens 园林'
    },
    {
      id: 'page-admin-downloads',
      title: '下载台账',
      subtitle: '全平台下载明细',
      path: '/admin/downloads',
      icon: Download,
      tone: 'secondary',
      admin: true,
      keywords: 'admin downloads 台账'
    }
  ]

  return actions.filter(action => {
    if (action.auth && !isLoggedIn.value) return false
    if (action.admin && !isAdmin.value) return false
    if (action.roles && !action.roles.includes(userStore.userRole)) return false
    return true
  })
})

function matches(text, keyword) {
  return String(text || '')
    .toLowerCase()
    .includes(keyword)
}

const groups = computed(() => {
  const keyword = query.value.trim().toLowerCase()

  const actions = pageActions.value
    .filter(
      action =>
        !keyword ||
        matches(action.title, keyword) ||
        matches(action.subtitle, keyword) ||
        matches(action.keywords, keyword)
    )
    .slice(0, keyword ? 8 : 7)
    .map(action => ({
      ...action,
      type: 'page',
      subtitle: action.subtitle,
      hint: '页面'
    }))

  const gardenItems = gardens.value
    .filter(garden => !keyword || matches(garden.name, keyword) || matches(garden.name_en, keyword))
    .slice(0, 6)
    .map(garden => ({
      id: `garden-${garden.id}`,
      type: 'garden',
      title: garden.name,
      subtitle: garden.name_en || garden.location || '园林档案',
      hint: `${garden.asset_count ?? 0} 件资产`,
      icon: Place,
      tone: 'secondary',
      garden
    }))

  const assetItems = assetResults.value.map(asset => ({
    id: `asset-${asset.id}`,
    type: 'asset',
    title: asset.title,
    subtitle: `${asset.asset_code}${asset.garden_name ? ` · ${asset.garden_name}` : ''}`,
    hint: '资产',
    icon: Picture,
    tone: 'primary',
    asset
  }))

  const groups = []
  if (assetItems.length) groups.push({ label: '资产', items: assetItems })
  if (gardenItems.length) groups.push({ label: '园林', items: gardenItems })
  if (actions.length) {
    groups.push({ label: keyword ? '相关页面' : '快捷导航', items: actions })
  }

  let index = 0
  groups.forEach(group => {
    group.items.forEach(item => {
      item._index = index++
    })
  })
  return groups
})

const flatItems = computed(() => groups.value.flatMap(group => group.items))

watch(query, value => {
  activeIndex.value = 0
  scheduleAssetSearch(value)
})

let searchTimer = null
let searchSeq = 0
function scheduleAssetSearch(value) {
  if (searchTimer) clearTimeout(searchTimer)
  const requestId = ++searchSeq
  const keyword = String(value || '').trim()
  if (!keyword || !isLoggedIn.value) {
    assetResults.value = []
    loading.value = false
    return
  }
  loading.value = true
  searchTimer = setTimeout(async () => {
    try {
      const response = await assetApi.getList({ keyword, per_page: 6, page: 1 })
      if (requestId !== searchSeq || keyword !== String(query.value || '').trim()) return
      if (response.data?.code === 200) {
        assetResults.value = response.data.data?.items || []
      }
    } catch {
      if (requestId === searchSeq) assetResults.value = []
    } finally {
      if (requestId === searchSeq) loading.value = false
    }
  }, 260)
}

async function loadGardens() {
  if (gardensLoaded.value) return
  try {
    const response = await gardenApi.getList()
    if (response.data?.code === 200) {
      gardens.value = response.data.data || []
      gardensLoaded.value = true
    }
  } catch {
    gardens.value = []
  }
}

function open() {
  visible.value = true
  previousFocus.value = document.activeElement
  document.body.style.overflow = 'hidden'
  loadGardens()
  nextTick(() => inputRef.value?.focus())
}

function close() {
  visible.value = false
  document.body.style.overflow = ''
  searchSeq += 1
  query.value = ''
  assetResults.value = []
  activeIndex.value = 0
  nextTick(() => previousFocus.value?.focus?.())
}

function handleTab(event) {
  const focusables = [...event.currentTarget.querySelectorAll('input, button:not([disabled])')]
    .filter(element => element.offsetParent !== null)
  if (!focusables.length) return
  const first = focusables[0]
  const last = focusables[focusables.length - 1]
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}

function move(step) {
  if (!flatItems.value.length) return
  const next = activeIndex.value + step
  if (next < 0) activeIndex.value = flatItems.value.length - 1
  else if (next >= flatItems.value.length) activeIndex.value = 0
  else activeIndex.value = next
}

function selectActive() {
  const item = flatItems.value[activeIndex.value]
  if (item) run(item)
}

function run(item) {
  close()
  if (item.type === 'page') {
    router.push(item.path)
  } else if (item.type === 'garden') {
    router.push({ path: '/assets', query: { garden_id: item.garden.id } })
  } else if (item.type === 'asset') {
    router.push(`/assets/${item.asset.id}`)
  }
}

function handleKeydown(event) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    if (visible.value) close()
    else open()
  } else if (event.key === 'Escape' && visible.value) {
    event.preventDefault()
    close()
  }
}

function handleExternalOpen() {
  open()
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
  window.addEventListener('open-command-palette', handleExternalOpen)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('open-command-palette', handleExternalOpen)
  if (searchTimer) clearTimeout(searchTimer)
  document.body.style.overflow = ''
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.palette-backdrop {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 12vh 20px 20px;
  background: rgba(18, 28, 23, 0.38);
  backdrop-filter: blur(2px);
}

.palette {
  width: min(640px, 100%);
  max-height: 72vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid $border-color;
  border-radius: $radius-xl;
  background: $bg-card;
  box-shadow: 0 24px 64px rgba(18, 28, 23, 0.22);
}

.palette-search {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 18px;
  border-bottom: 1px solid $border-light;

  .search-icon {
    color: $text-placeholder;
    font-size: 18px;
  }
}

.palette-input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  font-size: 15px;
  color: $text-primary;

  &::placeholder {
    color: $text-placeholder;
  }
}

.palette-kbd,
.palette-footer kbd {
  padding: 1px 6px;
  border: 1px solid $border-color;
  border-radius: $radius-xs;
  background: $bg-secondary;
  font-family: $font-mono;
  font-size: 10px;
  color: $text-placeholder;
}

.palette-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.palette-status {
  padding: 8px 12px;
  font-size: 12px;
  color: $text-placeholder;
}

.palette-group + .palette-group {
  margin-top: 6px;
}

.palette-group-label {
  padding: 8px 12px 4px;
  font-size: 11px;
  letter-spacing: 0.08em;
  color: $text-placeholder;
}

.palette-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 9px 12px;
  border: none;
  border-radius: $radius-md;
  background: transparent;
  text-align: left;
  cursor: pointer;

  &.active {
    background: $bg-active;
  }
}

.item-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  flex: 0 0 32px;
  border-radius: $radius-sm;
  background: $bg-secondary;
  color: $text-secondary;
  font-size: 16px;

  &.primary {
    background: rgba(47, 107, 90, 0.1);
    color: $primary-color;
  }
  &.secondary {
    background: rgba(76, 110, 138, 0.1);
    color: $secondary-color;
  }
  &.accent {
    background: rgba(166, 64, 47, 0.08);
    color: $accent-color;
  }
}

.item-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.item-title {
  font-size: 13px;
  font-weight: 500;
  color: $text-primary;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-subtitle {
  font-size: 11px;
  color: $text-placeholder;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-hint {
  flex: 0 0 auto;
  font-size: 10px;
  color: $text-placeholder;
  padding: 2px 6px;
  border: 1px solid $border-light;
  border-radius: $radius-full;
}

.palette-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 40px 20px;
  color: $text-placeholder;
  font-size: 13px;

  .el-icon {
    font-size: 24px;
  }
}

.palette-footer {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 18px;
  border-top: 1px solid $border-light;
  background: $bg-secondary;
  font-size: 11px;
  color: $text-placeholder;

  span {
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }

  .footer-brand {
    margin-left: auto;
    letter-spacing: 0.08em;
  }
}

.palette-fade-enter-active,
.palette-fade-leave-active {
  transition: opacity 0.18s ease;

  .palette {
    transition: transform 0.18s ease;
  }
}

.palette-fade-enter-from,
.palette-fade-leave-to {
  opacity: 0;

  .palette {
    transform: translateY(-8px) scale(0.99);
  }
}

@media (max-width: 560px) {
  .palette-backdrop {
    padding: 6vh 10px 10px;
  }

  .palette {
    max-height: 82vh;
  }

  .palette-footer {
    gap: 10px;

    .footer-brand {
      display: none;
    }
  }
}
</style>
