<template>
  <div class="asset-list-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="title-section">
          <h1 class="page-title">资产中心</h1>
          <p class="page-subtitle">浏览和管理苏州园林数字资产</p>
        </div>
        <div class="header-actions">
          <el-button type="primary" class="upload-btn" @click="goToUpload">
            <el-icon><Upload /></el-icon>
            上传资产
          </el-button>
        </div>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-section">
      <el-skeleton :loading="statsLoading" animated :count="4">
        <template #template>
          <div class="stat-card" v-for="i in 4" :key="i">
            <el-skeleton-item variant="circle" style="width: 56px; height: 56px; flex-shrink: 0" />
            <div class="stat-info">
              <el-skeleton-item variant="text" style="width: 60px; height: 28px" />
              <el-skeleton-item variant="text" style="width: 40px; height: 14px; margin-top: 4px" />
            </div>
          </div>
        </template>
        <template #default>
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
      </el-skeleton>
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
              <el-option v-for="g in gardens" :key="g.id" :label="g.name" :value="g.id" />
            </el-select>
          </div>
          <div class="filter-item">
            <el-select v-model="search.status" placeholder="状态" clearable size="large" style="width: 120px">
              <el-option label="全部状态" value="" />
              <el-option label="已发布" value="published" />
              <el-option label="待审核" value="pending" />
              <el-option label="草稿" value="draft" />
            </el-select>
          </div>
          <el-button type="primary" size="large" @click="handleSearch">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
        </div>
      </div>
    </div>

    <!-- 资产网格 -->
    <div class="assets-section">
      <div class="section-header">
        <span class="result-count">共 {{ pagination.total }} 项资产</span>
        <div class="view-switch">
          <el-radio-group v-model="viewMode" size="small">
            <el-radio-button label="grid">
              <el-icon><Grid /></el-icon>
            </el-radio-button>
            <el-radio-button label="list">
              <el-icon><List /></el-icon>
            </el-radio-button>
          </el-radio-group>
        </div>
      </div>

      <!-- 网格视图 -->
      <div v-if="viewMode === 'grid'" class="assets-grid">
        <el-skeleton :loading="loading" animated :count="8">
          <template #template>
            <div class="asset-card" v-for="i in 8" :key="i">
              <el-skeleton-item variant="image" style="height: 180px" />
              <div class="asset-content">
                <el-skeleton-item variant="text" style="width: 70%; height: 18px" />
                <el-skeleton-item variant="text" style="width: 40%; height: 12px; margin: 4px 0 12px" />
                <el-skeleton-item variant="text" style="width: 50%; height: 12px" />
              </div>
            </div>
          </template>
          <template #default>
        <div
          class="asset-card"
          v-for="asset in assets"
          :key="asset.id"
          @click="viewDetail(asset.id)"
        >
          <div class="asset-thumbnail">
            <img :src="getThumbnail(asset)" :alt="asset.title" />
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
        </el-skeleton>
      </div>

      <!-- 列表视图 -->
      <div v-else class="assets-list" v-loading="loading">
        <el-table :data="assets" style="width: 100%" class="modern-table">
          <el-table-column label="资产信息" min-width="300">
            <template #default="{ row }">
              <div class="asset-info-cell">
                <div class="asset-thumb-small">
                  <img :src="getThumbnail(row)" alt="" />
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
          <el-table-column label="操作" width="180" fixed="right">
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
      <div class="pagination-section">
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
      <div v-if="!loading && assets.length === 0" class="empty-state">
        <el-empty description="暂无资产数据">
          <el-button type="primary" @click="goToUpload">上传第一个资产</el-button>
        </el-empty>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { assetApi, gardenApi, publicApi } from '@/api/modules'
import { Upload, Search, Grid, List, Calendar, Picture, Document, VideoCamera, Collection, Link } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()

const loading = ref(false)
const statsLoading = ref(true)
const assets = ref([])
const gardens = ref([])
const viewMode = ref('grid')

const search = reactive({
  keyword: '',
  asset_type: '',
  garden_id: '',
  status: 'published'
})

const pagination = reactive({
  page: 1,
  perPage: 12,
  total: 0
})

// 统计数据
const stats = ref([
  { key: 'total', label: '总资产', value: 0, icon: 'Picture', gradient: 'linear-gradient(135deg, #10b981, #059669)' },
  { key: 'image', label: '影像', value: 0, icon: 'Picture', gradient: 'linear-gradient(135deg, #3b82f6, #1d4ed8)' },
  { key: 'model', label: '模型', value: 0, icon: 'Collection', gradient: 'linear-gradient(135deg, #8b5cf6, #6d28d9)' },
  { key: 'vector', label: '矢量', value: 0, icon: 'Document', gradient: 'linear-gradient(135deg, #f59e0b, #d97706)' }
])

async function loadStats() {
  statsLoading.value = true
  try {
    const response = await publicApi.getStats()
    if (response.data?.code === 200) {
      const d = response.data.data
      stats.value = [
        { key: 'total', label: '总资产', value: d.total_assets || 0, icon: 'Picture', gradient: 'linear-gradient(135deg, #10b981, #059669)' },
        { key: 'image', label: '影像', value: d.by_type?.image || 0, icon: 'Picture', gradient: 'linear-gradient(135deg, #3b82f6, #1d4ed8)' },
        { key: 'model', label: '模型', value: d.by_type?.model || 0, icon: 'Collection', gradient: 'linear-gradient(135deg, #8b5cf6, #6d28d9)' },
        { key: 'vector', label: '矢量', value: d.by_type?.vector || 0, icon: 'Document', gradient: 'linear-gradient(135deg, #f59e0b, #d97706)' }
      ]
    }
  } catch {
    // 保持默认值
  } finally {
    statsLoading.value = false
  }
}

async function loadAssets() {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      per_page: pagination.perPage,
      keyword: search.keyword || undefined,
      asset_type: search.asset_type || undefined,
      garden_id: search.garden_id || undefined,
      status: search.status || 'published'
    }
    const response = await assetApi.getList(params)
    if (response.data?.code === 200) {
      const data = response.data.data
      assets.value = data.items || []
      pagination.total = data.total || 0
    }
  } catch {
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
    }
  } catch (error) {
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
  if (asset.thumbnail_path) return asset.thumbnail_path
  const colors = { image: '#10b981', vector: '#3b82f6', model: '#8b5cf6', document: '#f59e0b', video: '#ef4444' }
  const color = (colors[asset.asset_type] || '#6b7280').replace('#', '')
  const label = (asset.asset_type || 'FILE').substring(0, 3).toUpperCase()
  return `data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="300"%3E%3Crect fill="%23${color}" width="400" height="300" rx="8"/%3E%3Ctext x="200" y="160" text-anchor="middle" fill="white" font-size="28"%3E${label}%3C/text%3E%3C/svg%3E`
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
  const map = { none: '未嵌入', pending: '处理中', embedded: '已嵌入' }
  return map[status] || '未知'
}

function getChainStatus(status) {
  const map = { none: '未存证', pending: '处理中', confirmed: '已存证' }
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
  background: white;
  padding: 32px 48px;
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
      font-size: 28px;
      font-weight: $font-weight-bold;
      color: $text-primary;
      margin-bottom: 8px;
    }

    .page-subtitle {
      font-size: 15px;
      color: $text-secondary;
    }
  }

  .upload-btn {
    background: $primary-gradient;
    border: none;
    padding: 12px 24px;
    font-weight: $font-weight-medium;

    &:hover {
      opacity: 0.9;
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

  .stat-card {
    background: white;
    border-radius: $radius-xl;
    padding: 24px;
    display: flex;
    align-items: center;
    gap: 16px;
    box-shadow: $shadow-card;
    transition: all $transition-base;

    &:hover {
      transform: translateY(-2px);
      box-shadow: $shadow-card-hover;
    }

    .stat-icon {
      width: 56px;
      height: 56px;
      border-radius: $radius-lg;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 24px;
      color: white;
    }

    .stat-info {
      .stat-value {
        font-size: 28px;
        font-weight: $font-weight-bold;
        color: $text-primary;
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
    background: white;
    border-radius: $radius-xl;
    padding: 20px 24px;
    box-shadow: $shadow-card;
  }

  .filter-row {
    display: flex;
    gap: 12px;
    align-items: center;

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
    background: white;
    border-radius: $radius-2xl;
    overflow: hidden;
    box-shadow: $shadow-card;
    cursor: pointer;
    transition: all $transition-base;

    &:hover {
      transform: translateY(-4px);
      box-shadow: $shadow-xl;

      .asset-overlay {
        opacity: 1;
      }

      .asset-thumbnail img {
        transform: scale(1.05);
      }
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

      .asset-overlay {
        position: absolute;
        inset: 0;
        background: rgba($primary-color, 0.85);
        display: flex;
        align-items: center;
        justify-content: center;
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
        background: rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(4px);
        border-radius: $radius-full;

        &.image { background: rgba($primary-color, 0.9); }
        &.model { background: rgba(#8b5cf6, 0.9); }
        &.vector { background: rgba(#3b82f6, 0.9); }
        &.document { background: rgba(#f59e0b, 0.9); }
        &.video { background: rgba(#ef4444, 0.9); }
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

        &.embedded, &.confirmed {
          background: rgba($success-color, 0.1);
          color: $success-color;
        }
      }
    }
  }
}

// 列表视图
.assets-list {
  .asset-info-cell {
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
    &.embedded, &.confirmed { background: $success-color; }
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
    padding: 24px;
    flex-direction: column;
    gap: 16px;
    text-align: center;
  }

  .stats-section,
  .filter-section,
  .assets-section {
    padding: 0 16px;
  }

  .assets-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
  }

  .filter-row {
    flex-wrap: wrap;

    .filter-item {
      width: 100% !important;
    }
  }
}
</style>
