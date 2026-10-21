<template>
  <div class="asset-list-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="title-section">
          <h1 class="page-title">资产中心</h1>
          <p class="page-subtitle">
            浏览和管理苏州园林数字资产
            <router-link to="/guide" class="subtitle-guide">不熟悉流程？看使用指南 →</router-link>
          </p>
        </div>
        <div class="header-actions">
          <el-button type="primary" class="upload-btn" @click="goToUpload">
            <el-icon><Upload /></el-icon>
            上传资产
          </el-button>
        </div>
      </div>
    </div>

    <!-- 首次使用提示 -->
    <div v-if="showGuideTip" class="guide-tip">
      <span>
        第一次使用？建议先看
        <router-link to="/guide">3 分钟使用指南</router-link>
        ，再按“上传 → 水印 → 上链 → 发布 → 申请授权”的顺序操作。
      </span>
      <button type="button" class="guide-tip-close" @click="dismissGuideTip">知道了</button>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-section">
      <div v-if="statsError" class="stats-error">
        <span>统计数据暂不可用</span>
        <el-button text type="primary" @click="loadStats">重试</el-button>
      </div>
      <template v-else-if="statsLoading">
        <div class="stat-card stat-card-skeleton" v-for="i in 4" :key="`stat-skeleton-${i}`" aria-hidden="true">
          <el-skeleton-item variant="circle" style="width: 42px; height: 42px; flex-shrink: 0" />
          <div class="stat-info">
            <el-skeleton-item variant="text" style="width: 64px; height: 24px" />
            <el-skeleton-item variant="text" style="width: 44px; height: 12px; margin-top: 6px" />
          </div>
        </div>
      </template>
      <template v-else>
        <div class="stat-card" v-for="stat in stats" :key="stat.key">
          <div class="stat-icon" :style="{ background: stat.gradient }">
            <el-icon><component :is="stat.icon" /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stat.value }}</div>
            <div class="stat-label">{{ stat.label }}</div>
          </div>
        </div>
      </template>
    </div>

    <!-- 搜索筛选区 -->
    <div class="filter-section">
      <div class="filter-card">
        <div class="filter-row">
          <div class="filter-item search-input">
            <el-input
              v-model="search.keyword"
              placeholder="搜索资产名称或编码..."
              prefix-icon="Search"
              clearable
              size="large"
              @keyup.enter="handleSearch"
            />
          </div>
          <div class="filter-item">
            <el-select v-model="search.asset_type" placeholder="资产类型" clearable size="large" style="width: 140px">
              <el-option label="全部类型" value="" />
              <el-option label="影像" value="image" />
              <el-option label="三维模型" value="model" />
              <el-option label="矢量数据" value="vector" />
              <el-option label="文献" value="document" />
              <el-option label="视频" value="video" />
            </el-select>
          </div>
          <div class="filter-item">
            <el-select v-model="search.garden_id" placeholder="所属园林" clearable size="large" style="width: 160px">
              <el-option label="全部园林" value="" />
              <el-option v-for="g in gardens" :key="g.id" :label="gardensOffline ? `${g.name}（离线示例）` : g.name" :value="g.id" />
            </el-select>
          </div>
          <div class="filter-item">
            <el-select v-model="search.status" placeholder="状态" clearable size="large" style="width: 120px">
              <el-option label="全部状态" value="" />
              <el-option label="已发布" value="published" />
              <el-option label="待审核" value="pending" />
              <el-option label="已拒绝" value="rejected" />
              <el-option label="草稿" value="draft" />
            </el-select>
          </div>
          <el-button type="primary" size="large" @click="handleSearch">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-tag v-if="gardensOffline" type="warning" size="small" effect="plain">
            园林筛选为离线示例数据
          </el-tag>
        </div>
      </div>
    </div>

    <!-- 资产网格 -->
    <div class="assets-section">
      <div class="section-header">
        <span class="result-count">共 {{ pagination.total }} 项资产</span>
        <div class="view-switch">
          <el-radio-group v-model="viewMode" size="small">
            <el-radio-button value="grid" aria-label="网格视图" title="网格视图">
              <el-icon aria-hidden="true"><Grid /></el-icon>
            </el-radio-button>
            <el-radio-button value="list" aria-label="列表视图" title="列表视图">
              <el-icon aria-hidden="true"><List /></el-icon>
            </el-radio-button>
          </el-radio-group>
        </div>
      </div>

      <!-- 网格视图 -->
      <div v-if="loadError" class="assets-error">
        <el-empty description="资产列表加载失败">
          <el-button type="primary" @click="loadAssets">重试</el-button>
        </el-empty>
      </div>
      <div v-else-if="viewMode === 'grid'" class="assets-grid">
        <template v-if="loading">
          <div class="asset-card asset-card-skeleton" v-for="i in 8" :key="`card-skeleton-${i}`" aria-hidden="true">
            <div class="asset-thumbnail skeleton"></div>
            <div class="asset-content">
              <div class="skeleton skeleton-line" style="width: 72%; height: 18px"></div>
              <div class="skeleton skeleton-line" style="width: 46%; height: 12px"></div>
              <div class="skeleton skeleton-line" style="width: 58%; height: 12px"></div>
            </div>
          </div>
        </template>
        <template v-else>
          <div
            class="asset-card"
            v-for="asset in assets"
            :key="asset.id"
            role="button"
            tabindex="0"
            :aria-label="`查看资产 ${asset.title || asset.asset_code || ''}`"
            @click="viewDetail(asset.id)"
            @keydown.enter.prevent="viewDetail(asset.id)"
            @keydown.space.prevent="viewDetail(asset.id)"
          >
            <div class="asset-thumbnail">
              <img
                :src="getThumbnail(asset)"
                :alt="asset.title"
                loading="lazy"
                decoding="async"
                @error="onThumbnailError($event, asset)"
              />
              <div class="asset-overlay">
                <el-button type="primary" size="small" round>查看详情</el-button>
              </div>
              <div class="asset-type-badge" :class="asset.asset_type">
                {{ getTypeName(asset.asset_type) }}
              </div>
            </div>
            <div class="asset-content">
              <h3 class="asset-title">{{ asset.title }}</h3>
              <p class="asset-code">{{ asset.asset_code }}</p>
              <div class="asset-meta">
                <span class="meta-item">
                  <el-icon><Calendar /></el-icon>
                  {{ formatDate(asset.created_at) }}
                </span>
              </div>
              <div class="asset-status">
                <span class="status-tag" :class="asset.watermark_status">
                  {{ getWatermarkStatus(asset.watermark_status) }}
                </span>
                <span class="status-tag" :class="asset.chain_status">
                  {{ getChainStatus(asset.chain_status) }}
                </span>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- 列表视图 -->
      <div v-else class="assets-list" v-loading="loading">
        <el-table :data="assets" style="width: 100%" class="modern-table">
          <el-table-column label="资产信息" min-width="300">
            <template #default="{ row }">
              <div class="asset-info-cell">
                <div class="asset-thumb-small">
                  <img :src="getThumbnail(row)" alt="" loading="lazy" @error="onThumbnailError($event, row)" />
                </div>
                <div class="asset-meta-cell">
                  <div class="asset-title-cell">{{ row.title }}</div>
                  <div class="asset-code-cell">{{ row.asset_code }}</div>
                </div>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="asset_type" label="类型" width="100">
            <template #default="{ row }">
              <el-tag :type="getTypeTag(row.asset_type)" size="small" effect="light">
                {{ getTypeName(row.asset_type) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="水印状态" width="100">
            <template #default="{ row }">
              <span class="status-dot" :class="row.watermark_status"></span>
              {{ getWatermarkStatus(row.watermark_status) }}
            </template>
          </el-table-column>
          <el-table-column label="存证状态" width="100">
            <template #default="{ row }">
              <span class="status-dot" :class="row.chain_status"></span>
              {{ getChainStatus(row.chain_status) }}
            </template>
          </el-table-column>
          <el-table-column prop="view_count" label="浏览" width="80" />
          <el-table-column prop="created_at" label="上传时间" width="140">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180">
            <template #default="{ row }">
              <div class="action-buttons">
                <el-button type="primary" link size="small" @click.stop="viewDetail(row.id)">
                  查看
                </el-button>
                <el-button type="success" link size="small" @click.stop="applyLicense(row.id)">
                  申请授权
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 分页 -->
      <div class="pagination-section" v-if="!loadError">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.perPage"
          :total="pagination.total"
          :page-sizes="[12, 24, 48, 96]"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @size-change="loadAssets"
          @current-change="loadAssets"
        />
      </div>

      <!-- 空状态 -->
      <div v-if="!loading && !loadError && assets.length === 0" class="empty-state">
        <el-empty :description="hasFilters ? '没有匹配的资产' : '暂无资产数据'">
          <el-button v-if="hasFilters" type="primary" @click="clearFilters">清除筛选</el-button>
          <el-button v-else type="primary" @click="goToUpload">上传第一个资产</el-button>
        </el-empty>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch, shallowRef } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { assetApi, gardenApi, publicApi } from '@/api/modules'
import { Upload, Search, Grid, List, Calendar, Picture, Document, Collection } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()

const loading = ref(false)
const statsLoading = ref(true)
const statsError = ref(false)
const loadError = ref(false)
const showGuideTip = ref(localStorage.getItem('hideAssetGuideTip') !== '1')
const assets = ref([])
const gardens = ref([])
const gardensOffline = ref(false)
const viewMode = ref('grid')

const search = reactive({
  keyword: '',
  asset_type: '',
  garden_id: '',
  status: ''
})

const hasFilters = computed(() =>
  Boolean(search.keyword || search.asset_type || search.garden_id || search.status)
)

const pagination = reactive({
  page: 1,
  perPage: 12,
  total: 0
})

// 统计数据
const stats = shallowRef([
  { key: 'total', label: '总资产', value: 0, icon: Picture, gradient: '#eaf0eb' },
  { key: 'image', label: '影像', value: 0, icon: Picture, gradient: '#eaf0eb' },
  { key: 'model', label: '模型', value: 0, icon: Collection, gradient: '#eaf0eb' },
  { key: 'vector', label: '矢量', value: 0, icon: Document, gradient: '#eaf0eb' }
])

async function loadStats() {
  statsLoading.value = true
  statsError.value = false
  try {
    const response = await publicApi.getStats()
    if (response.data?.code === 200) {
      const d = response.data.data
      stats.value = [
        { key: 'total', label: '总资产', value: d.total_assets || 0, icon: Picture, gradient: '#eaf0eb' },
        { key: 'image', label: '影像', value: d.by_type?.image || 0, icon: Picture, gradient: '#eaf0eb' },
        { key: 'model', label: '模型', value: d.by_type?.model || 0, icon: Collection, gradient: '#eaf0eb' },
        { key: 'vector', label: '矢量', value: d.by_type?.vector || 0, icon: Document, gradient: '#eaf0eb' }
      ]
    } else {
      statsError.value = true
    }
  } catch {
    statsError.value = true
  } finally {
    statsLoading.value = false
  }
}

async function loadAssets() {
  loading.value = true
  loadError.value = false
  try {
    const params = {
      page: pagination.page,
      per_page: pagination.perPage,
      keyword: search.keyword || undefined,
      asset_type: search.asset_type || undefined,
      garden_id: search.garden_id || undefined,
      status: search.status || undefined
    }
    const response = await assetApi.getList(params)
    if (response.data?.code === 200) {
      const data = response.data.data
      assets.value = data.items || []
      pagination.total = data.total || 0
    } else {
      loadError.value = true
    }
  } catch {
    loadError.value = true
    assets.value = []
    pagination.total = 0
  } finally {
    loading.value = false
  }
}

async function loadGardens() {
  try {
    const response = await gardenApi.getList()
    if (response.data?.code === 200) {
      gardens.value = response.data.data || []
      gardensOffline.value = false
    }
  } catch (error) {
    // 接口失败时使用兜底数据，并在界面明确标注为离线示例，避免掩盖故障
    console.error('加载园林列表失败，使用离线示例数据:', error)
    gardensOffline.value = true
    gardens.value = [
      { id: 1, name: '拙政园', code: 'ZZY' },
      { id: 2, name: '留园', code: 'LY' },
      { id: 3, name: '狮子林', code: 'SZL' }
    ]
  }
}

function handleSearch() {
  pagination.page = 1
  loadAssets()
}

function clearFilters() {
  search.keyword = ''
  search.asset_type = ''
  search.garden_id = ''
  search.status = ''
  pagination.page = 1
  loadAssets()
}

function dismissGuideTip() {
  showGuideTip.value = false
  localStorage.setItem('hideAssetGuideTip', '1')
}

function goToUpload() {
  router.push('/assets/upload')
}

function viewDetail(id) {
  router.push(`/assets/${id}`)
}

function applyLicense(id) {
  router.push(`/license/apply?asset_id=${id}`)
}

function getThumbnail(asset) {
  // 有资产 ID 时统一走后端缩略图端点；列表使用 640px 卡片图，避免解码大图卡顿
  if (asset.id) return `/api/assets/${asset.id}/thumbnail?size=card&v=2`
  return placeholderThumbnail(asset.asset_type)
}

function placeholderThumbnail(type) {
  const colors = { image: '#2f6b5a', vector: '#4c6e8a', model: '#6d5b7a', document: '#b07a2a', video: '#a6402f' }
  const color = (colors[type] || '#5b675f').replace('#', '')
  const label = (type || 'FILE').substring(0, 3).toUpperCase()
  return `data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="300"%3E%3Crect fill="%23${color}" width="400" height="300" rx="8"/%3E%3Ctext x="200" y="160" text-anchor="middle" fill="white" font-size="28"%3E${label}%3C/text%3E%3C/svg%3E`
}

function onThumbnailError(event, asset) {
  const img = event?.target
  if (!img || img.dataset.fallbackApplied) return
  img.dataset.fallbackApplied = '1'
  img.src = placeholderThumbnail(asset?.asset_type)
}

function getTypeName(type) {
  const map = { image: '影像', model: '模型', vector: '矢量', document: '文献', video: '视频' }
  return map[type] || type
}

function getTypeTag(type) {
  const map = { image: 'success', model: 'warning', vector: 'primary', document: 'info', video: 'danger' }
  return map[type] || ''
}

function getWatermarkStatus(status) {
  const map = { none: '未嵌入', pending: '处理中', embedded: '已嵌入', verified: '已校验', failed: '失败' }
  return map[status] || '未知'
}

function getChainStatus(status) {
  const map = { none: '未存证', pending: '处理中', confirmed: '已存证', failed: '存证失败' }
  return map[status] || '未知'
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

onMounted(() => {
  if (route.query.garden_id) {
    search.garden_id = Number(route.query.garden_id)
  }
  loadStats()
  loadAssets()
  loadGardens()
})

// 首页园林卡会在已打开资产中心时只改 query，需要重新筛选
watch(() => route.query.garden_id, (gardenId) => {
  search.garden_id = gardenId ? Number(gardenId) : ''
  pagination.page = 1
  loadAssets()
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.asset-list-page {
  min-height: 100vh;
  background: $bg-primary;
  padding-bottom: 48px;
}

// 页面头部
.page-header {
  background: $bg-card;
  padding: 28px 40px;
  border-bottom: 1px solid $border-light;

  .header-content {
    max-width: 1400px;
    margin: 0 auto;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .title-section {
    .page-title {
      font-family: $font-display;
      font-size: 26px;
      font-weight: 600;
      color: $text-primary;
      margin-bottom: 6px;
    }

    .page-subtitle {
      font-size: 15px;
      color: $text-secondary;

      .subtitle-guide {
        margin-left: 10px;
        font-size: 13px;
        color: $primary-color;
        white-space: nowrap;

        &:hover {
          color: $primary-dark;
        }
      }
    }
  }

  .upload-btn {
    background: $primary-color;
    border: 1px solid $primary-dark;
    padding: 10px 20px;
    border-radius: $radius-sm;
    font-weight: $font-weight-medium;
  }
}

// 首次使用提示
.guide-tip {
  max-width: 1400px;
  margin: 18px auto 0;
  padding: 10px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: rgba(47, 107, 90, 0.06);
  border: 1px solid rgba(47, 107, 90, 0.18);
  border-radius: $radius-md;
  font-size: 13px;
  line-height: 1.7;
  color: $text-secondary;

  a {
    color: $primary-dark;
    font-weight: 500;
  }

  .guide-tip-close {
    flex-shrink: 0;
    padding: 3px 10px;
    background: transparent;
    border: 1px solid $border-color;
    border-radius: $radius-xs;
    font-size: 12px;
    color: $text-secondary;
    cursor: pointer;

    &:hover {
      border-color: $primary-color;
      color: $primary-dark;
    }
  }
}

// 统计卡片
.stats-section {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px 48px;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  .stats-error {
    grid-column: 1 / -1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 18px;
    background: $bg-card;
    border: 1px dashed $border-color;
    border-radius: $radius-lg;
    color: $text-secondary;
  }

  .stat-card {
    background: $bg-card;
    border: 1px solid $border-color;
    border-radius: $radius-lg;
    padding: 18px;
    display: flex;
    align-items: center;
    gap: 14px;
    box-shadow: $shadow-sm;
    transition: border-color $transition-fast;

    &:hover {
      border-color: $border-dark;
    }

    &.stat-card-skeleton {
      pointer-events: none;
    }

    .stat-icon {
      width: 42px;
      height: 42px;
      border-radius: $radius-md;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      color: $primary-dark;
      border: 1px solid $border-color;
    }

    .stat-info {
      .stat-value {
        font-family: $font-display;
        font-size: 26px;
        font-weight: 600;
        color: $text-primary;
        line-height: 1.2;
      }

      .stat-label {
        font-size: 14px;
        color: $text-secondary;
      }
    }
  }
}

// 筛选区
.filter-section {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 48px 24px;

  .filter-card {
    background: $bg-card;
    border: 1px solid $border-color;
    border-radius: $radius-lg;
    padding: 16px 20px;
    box-shadow: $shadow-sm;
  }

  .filter-row {
    display: flex;
    gap: 12px;
    align-items: center;
    flex-wrap: wrap;

    .filter-item {
      flex-shrink: 0;

      &.search-input {
        flex: 1;
        min-width: 280px;
      }
    }
  }
}

// 资产区域
.assets-section {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 48px;

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;

    .result-count {
      font-size: 14px;
      color: $text-secondary;
    }
  }
}

// 网格视图
.assets-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
  .asset-card {
    background: $bg-card;
    border: 1px solid $border-color;
    border-radius: $radius-md;
    overflow: hidden;
    box-shadow: $shadow-sm;
    cursor: pointer;
    transition: border-color $transition-fast, box-shadow $transition-fast;

    &.asset-card-skeleton {
      pointer-events: none;

      .asset-thumbnail.skeleton {
        height: 180px;
      }

      .skeleton-line {
        border-radius: $radius-xs;
        margin-bottom: 10px;
      }
    }

    &:hover {
      border-color: $border-dark;
      box-shadow: $shadow-md;

      .asset-overlay {
        opacity: 1;
      }

      .asset-thumbnail img {
        transform: scale(1.03);
      }
    }

    &:focus-visible {
      outline: 2px solid $primary-color;
      outline-offset: 2px;
    }

    .asset-thumbnail {
      position: relative;
      height: 180px;
      overflow: hidden;

      img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        transition: transform $transition-slow;
      }

      // 悬停时只压一条底部渐隐，不遮住画面主体
      .asset-overlay {
        position: absolute;
        left: 0;
        right: 0;
        bottom: 0;
        height: 64px;
        padding: 0 12px 12px;
        background: linear-gradient(to top, rgba(14, 59, 51, 0.72), rgba(14, 59, 51, 0));
        display: flex;
        align-items: flex-end;
        justify-content: flex-end;
        opacity: 0;
        transition: opacity $transition-base;
      }

      .asset-type-badge {
        position: absolute;
        top: 12px;
        left: 12px;
        padding: 4px 12px;
        font-size: 12px;
        font-weight: $font-weight-medium;
        color: white;
        background: rgba(0, 0, 0, 0.48);
        border: 1px solid rgba(252, 253, 251, 0.18);
        border-radius: $radius-xs;

        &.image { background: rgba($primary-color, 0.9); }
        &.model { background: rgba(#6d5b7a, 0.9); }
        &.vector { background: rgba(#4c6e8a, 0.9); }
        &.document { background: rgba(#b07a2a, 0.9); }
        &.video { background: rgba(#a6402f, 0.9); }
      }
    }

    .asset-content {
      padding: 16px;

      .asset-title {
        font-size: 15px;
        font-weight: $font-weight-semibold;
        color: $text-primary;
        margin-bottom: 4px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .asset-code {
        font-size: 12px;
        font-family: $font-mono;
        color: $text-placeholder;
        margin-bottom: 12px;
      }

      .asset-meta {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 12px;
        color: $text-secondary;
        margin-bottom: 12px;

        .meta-item {
          display: flex;
          align-items: center;
          gap: 4px;
        }
      }

      .asset-status {
        display: flex;
        gap: 8px;
      }

      .status-tag {
        font-size: 11px;
        padding: 2px 8px;
        border-radius: $radius-full;
        background: $bg-secondary;
        color: $text-secondary;

        &.embedded, &.confirmed, &.verified {
          background: rgba($success-color, 0.1);
          color: $success-color;
        }

        &.failed {
          background: rgba($error-color, 0.1);
          color: $error-color;
        }
      }
    }
  }
}

// 列表视图
.assets-list {  .asset-info-cell {
    display: flex;
    align-items: center;
    gap: 12px;

    .asset-thumb-small {
      width: 48px;
      height: 48px;
      border-radius: $radius-md;
      overflow: hidden;

      img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
    }

    .asset-meta-cell {
      min-width: 0;
    }

    .asset-title-cell {
      font-weight: $font-weight-medium;
      color: $text-primary;
      margin-bottom: 2px;
    }

    .asset-code-cell {
      font-size: 12px;
      font-family: $font-mono;
      color: $text-placeholder;
    }
  }

  .status-dot {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    margin-right: 6px;

    &.none { background: $text-placeholder; }
    &.pending { background: $warning-color; }
    &.embedded, &.confirmed, &.verified { background: $success-color; }
    &.failed { background: $error-color; }
  }

  .action-buttons {
    display: flex;
    gap: 8px;
  }
}

// 分页
.pagination-section {
  display: flex;
  justify-content: center;
  margin-top: 32px;
}

.assets-error {
  padding: 48px 0;
}

// 空状态
.empty-state {
  padding: 80px 0;
}

// 响应式
@media (max-width: 1200px) {
  .assets-grid {
    grid-template-columns: repeat(3, 1fr);
  }

  .stats-section {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .page-header {
    padding: 24px 16px;

    .header-content {
      flex-direction: column;
      gap: 16px;
      text-align: center;
    }
  }

  .stats-section,
  .filter-section,
  .assets-section {
    padding: 0 16px;
  }

  .guide-tip {
    margin: 14px 16px 0;
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
  }

  .filter-row {
    flex-wrap: wrap;

    .filter-item {
      width: 100% !important;

      &.search-input {
        min-width: 0;
      }

      :deep(.el-select) {
        width: 100% !important;
      }
    }

    > .el-button {
      width: 100%;
    }
  }

  .assets-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
  }

  .asset-card .asset-title {
    white-space: normal;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }

  .pagination-section {
    :deep(.el-pagination__sizes),
    :deep(.el-pagination__jump) {
      display: none;
    }
  }
}

@media (max-width: 480px) {
  .assets-grid {
    grid-template-columns: 1fr;
  }

  .stats-section {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;

    .stat-card {
      padding: 14px;
      gap: 10px;

      .stat-icon {
        width: 36px;
        height: 36px;
        font-size: 17px;
      }

      .stat-value {
        font-size: 22px;
      }
    }
  }
}
</style>
