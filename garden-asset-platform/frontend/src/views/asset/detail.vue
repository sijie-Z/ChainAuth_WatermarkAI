<template>
  <div class="asset-detail-container">
    <header class="page-bar">
      <router-link to="/assets" class="page-back">
        <el-icon><ArrowLeft /></el-icon>
        返回资产档案
      </router-link>
      <h1 class="page-title">资产详情</h1>
      <span v-if="asset.asset_code" class="page-meta">{{ asset.asset_code }}</span>
    </header>

    <!-- 加载骨架屏 -->
    <el-skeleton :loading="loading" animated>
      <template #template>
        <div class="detail-grid">
          <div class="skeleton-sheet">
            <el-skeleton-item variant="text" style="width: 40%; height: 26px" />
            <el-skeleton-item variant="image" style="width: 100%; aspect-ratio: 16 / 10; margin-top: 20px" />
            <el-skeleton :rows="4" animated style="margin-top: 20px" />
          </div>
          <div class="skeleton-side">
            <el-skeleton :rows="5" animated />
            <el-skeleton :rows="3" animated style="margin-top: 32px" />
          </div>
        </div>
      </template>

      <template #default>
        <!-- 错误状态 -->
        <el-card v-if="loadError" class="error-card">
          <el-empty description="资产加载失败">
            <el-button type="primary" @click="loadAsset">重试</el-button>
            <el-button @click="goBack">返回列表</el-button>
          </el-empty>
        </el-card>

        <!-- 正常内容 -->
        <div v-else class="detail-grid">
          <!-- 左侧：资产图版与著录信息 -->
          <article class="asset-sheet">
            <header class="sheet-head">
              <div class="sheet-title-group">
                <p class="sheet-kicker">{{ asset.garden_name || '苏州园林' }} · 数字资产</p>
                <h2 class="sheet-title">{{ asset.title }}</h2>
              </div>
              <StatusTag :status="asset.status" />
            </header>

            <figure class="preview-area">
              <el-image
                v-if="asset.asset_type === 'image' || asset.asset_type === 'vector'"
                class="asset-photo"
                :src="getAssetUrl(asset)"
                :preview-src-list="asset.asset_type === 'image' ? [getAssetUrl(asset)] : []"
                :preview-teleported="true"
                hide-on-click-modal
                fit="contain"
              >
                <template #error>
                  <div class="preview-placeholder">
                    <el-icon :size="48"><Picture /></el-icon>
                    <span>{{ typeLabel(asset.asset_type) }}预览暂不可用</span>
                  </div>
                </template>
              </el-image>
              <div v-else class="preview-placeholder">
                <el-icon :size="56"><Document /></el-icon>
                <span>{{ typeLabel(asset.asset_type) }} · {{ asset.file_format || '文件' }}</span>
              </div>
              <figcaption class="preview-caption">
                <span>{{ asset.garden_name || '未归类园林' }}</span>
                <span class="mono">{{ asset.asset_code }}</span>
              </figcaption>
            </figure>

            <dl class="spec-grid">
              <div class="spec-item">
                <dt>资产编码</dt>
                <dd class="mono">{{ asset.asset_code || '—' }}</dd>
              </div>
              <div class="spec-item">
                <dt>所属园林</dt>
                <dd>{{ asset.garden_name || '—' }}</dd>
              </div>
              <div class="spec-item">
                <dt>文件格式</dt>
                <dd>{{ (asset.file_format || '—').toUpperCase() }}</dd>
              </div>
              <div class="spec-item">
                <dt>文件大小</dt>
                <dd>{{ formatSize(asset.file_size) }}</dd>
              </div>
              <div class="spec-item">
                <dt>上传者</dt>
                <dd>{{ asset.uploader_name || asset.creator_name || '—' }}</dd>
              </div>
              <div class="spec-item">
                <dt>创建时间</dt>
                <dd>{{ formatDate(asset.created_at) }}</dd>
              </div>
              <div class="spec-item spec-span">
                <dt>著录说明</dt>
                <dd>{{ asset.description || '暂无描述' }}</dd>
              </div>
            </dl>
          </article>

          <!-- 右侧：状态与操作 -->
          <aside class="side-panel">
            <section class="side-block">
              <header class="side-head">
                <span class="side-kicker">水印状态</span>
                <StatusTag :status="asset.watermark_status || 'none'" kind="watermark" />
              </header>
              <dl class="side-meta">
                <div v-if="asset.watermark_id" class="side-row">
                  <dt>水印 ID</dt>
                  <dd class="mono">{{ asset.watermark_id }}</dd>
                </div>
                <div v-if="asset.vr_value !== undefined" class="side-row">
                  <dt>鲁棒性值</dt>
                  <dd>{{ asset.vr_value?.toFixed(4) || '-' }}</dd>
                </div>
                <div v-if="!asset.watermark_id" class="side-row">
                  <dt>说明</dt>
                  <dd>尚未写入水印标识</dd>
                </div>
              </dl>
              <el-button
                v-if="canManage && !watermarkReady"
                type="primary"
                class="side-action"
                :loading="watermarking"
                @click="embedWatermark"
              >
                嵌入水印
              </el-button>
              <el-button
                v-else-if="canManage"
                class="side-action"
                :loading="extracting"
                @click="extractWatermark"
              >
                提取并校验水印
              </el-button>
              <p v-else class="side-hint">仅上传者或资产管理员可操作水印。</p>
            </section>

            <section class="side-block">
              <header class="side-head">
                <span class="side-kicker">区块链存证</span>
                <StatusTag :status="asset.chain_status || 'none'" kind="chain" />
              </header>
              <dl class="side-meta">
                <div v-if="asset.chain_tx_hash" class="side-row">
                  <dt>交易哈希</dt>
                  <dd class="mono">{{ asset.chain_tx_hash }}</dd>
                </div>
                <div v-if="asset.certificate_id" class="side-row">
                  <dt>证书编号</dt>
                  <dd class="mono">{{ asset.certificate_id }}</dd>
                </div>
                <div v-if="!asset.chain_tx_hash" class="side-row">
                  <dt>说明</dt>
                  <dd>尚未写入联盟链</dd>
                </div>
              </dl>
              <el-button
                v-if="canManage && asset.chain_status !== 'confirmed'"
                type="primary"
                class="side-action"
                :disabled="!watermarkReady"
                :loading="chaining"
                @click="registerChain"
              >
                上链存证
              </el-button>
              <el-button v-else-if="canManage" class="side-action" @click="viewCertificate">
                查看存证证书
              </el-button>
              <p v-if="!canManage" class="side-hint">存证操作由上传者或资产管理员完成。</p>
              <p v-else-if="asset.chain_status !== 'confirmed' && !watermarkReady" class="side-hint">
                上链前需先完成水印嵌入
              </p>
            </section>

            <section class="side-block side-actions">
              <header class="side-head">
                <span class="side-kicker">授权与分发</span>
              </header>
              <p class="side-note">下载与使用需经双重审批，授权记录会写入台账。</p>
              <el-button type="primary" class="side-action" @click="applyLicense">
                申请授权
              </el-button>
              <el-button class="side-action" @click="goBack">返回资产列表</el-button>
            </section>
          </aside>
        </div>
      </template>
    </el-skeleton>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Document, Picture } from '@element-plus/icons-vue'
import { assetApi, watermarkApi, blockchainApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const asset = ref({})
const loading = ref(true)
const loadError = ref(false)
const watermarking = ref(false)
const extracting = ref(false)
const chaining = ref(false)
const watermarkReady = computed(() =>
  ['embedded', 'verified'].includes(asset.value.watermark_status)
)
const canManage = computed(() => {
  const role = userStore.userRole
  const userId = userStore.user?.id
  return ['admin', 'asset_admin'].includes(role)
    || (userId && asset.value.creator_id === userId)
})

async function loadAsset() {
  loading.value = true
  loadError.value = false
  try {
    const response = await assetApi.getDetail(route.params.id)
    if (response.data.code === 200) {
      asset.value = response.data.data
    } else {
      loadError.value = true
    }
  } catch (error) {
    loadError.value = true
  } finally {
    loading.value = false
  }
}

async function embedWatermark() {
  watermarking.value = true
  try {
    const response = await watermarkApi.embed(asset.value.id)
    if (response.data.code === 200) {
      ElMessage.success('水印嵌入成功')
      loadAsset()
    }
  } catch (error) {
    ElMessage.error('水印嵌入失败')
  } finally {
    watermarking.value = false
  }
}

async function extractWatermark() {
  extracting.value = true
  try {
    const response = await watermarkApi.extract(asset.value.id)
    if (response.data.code === 200) {
      ElMessage.success('水印提取成功，NC值: ' + response.data.data.nc_value)
    }
  } catch (error) {
    ElMessage.error('水印提取失败')
  } finally {
    extracting.value = false
  }
}

async function registerChain() {
  chaining.value = true
  try {
    const response = await blockchainApi.register(asset.value.id)
    if (response.data.code === 200) {
      ElMessage.success('存证成功')
      loadAsset()
    }
  } catch (error) {
    ElMessage.error('存证失败')
  } finally {
    chaining.value = false
  }
}

function viewCertificate() {
  router.push(`/certificate/${asset.value.certificate_id}`)
}

function applyLicense() {
  router.push(`/license/apply?asset_id=${asset.value.id}`)
}

function goBack() {
  router.push('/assets')
}

const TYPE_LABELS = { image: '影像', vector: '矢量图', model: '三维模型', document: '文献', video: '视频' }

function typeLabel(type) {
  return TYPE_LABELS[type] || '文件'
}

function getAssetUrl(asset) {
  if (asset.id) return `/api/assets/${asset.id}/thumbnail`
  return placeholderImage(asset.asset_type)
}

function placeholderImage(type) {
  const colors = { image: '#2f6b5a', vector: '#4c6e8a', model: '#6d5b7a', document: '#b07a2a', video: '#a6402f' }
  const color = (colors[type] || '#5b675f').replace('#', '')
  const label = (type || 'FILE').substring(0, 3).toUpperCase()
  return `data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="800" height="500"%3E%3Crect fill="%23${color}" width="800" height="500"/%3E%3Ctext x="400" y="260" text-anchor="middle" fill="white" font-size="42"%3E${label}%3C/text%3E%3C/svg%3E`
}

function formatSize(size) {
  if (!size) return '-'
  if (size < 1024) return size + ' B'
  if (size < 1024 * 1024) return (size / 1024).toFixed(2) + ' KB'
  return (size / 1024 / 1024).toFixed(2) + ' MB'
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

onMounted(() => {
  loadAsset()
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.asset-detail-container {
  max-width: 1280px;
  margin: 0 auto;
  padding: $spacing-2xl $spacing-3xl $spacing-4xl;
  min-height: 100vh;
  background: $bg-primary;
}

// ========== 页眉 ==========
.page-bar {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: $spacing-md;
  padding-bottom: $spacing-md;
  margin-bottom: $spacing-xl;
  border-bottom: 1px solid $border-light;
}

.page-back {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  align-self: center;
  font-size: $font-size-sm;
  color: $text-secondary;
  transition: color $transition-fast;

  &:hover {
    color: $primary-dark;
  }
}

.page-title {
  font-family: $font-display;
  font-size: 23px;
  font-weight: $font-weight-semibold;
  line-height: $line-height-tight;
  letter-spacing: 0.02em;
  color: $text-primary;
}

.page-meta {
  margin-left: auto;
  align-self: center;
  font-family: $font-mono;
  font-size: $font-size-xs;
  letter-spacing: 0.08em;
  color: $text-placeholder;
}

// ========== 版面 ==========
.detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: $spacing-2xl;
  align-items: start;
}

.asset-sheet {
  min-width: 0;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
  padding: $spacing-2xl;
  box-shadow: $shadow-sm;
}

.sheet-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: $spacing-lg;
  margin-bottom: $spacing-lg;
}

.sheet-kicker {
  font-size: $font-size-xs;
  letter-spacing: 0.14em;
  color: $text-secondary;
  margin-bottom: 6px;
}

.sheet-title {
  font-family: $font-display;
  font-size: 24px;
  line-height: 1.35;
  font-weight: $font-weight-semibold;
  color: $text-primary;
}

.preview-area {
  margin: 0 0 $spacing-xl;
}

.asset-photo {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 10;
  background: $bg-secondary;
  border: 1px solid $border-light;
  border-radius: $radius-md;
  overflow: hidden;
  cursor: zoom-in;

  :deep(.el-image__inner) {
    width: 100%;
    height: 100%;
    object-fit: contain;
  }
}

.preview-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: $spacing-sm;
  width: 100%;
  aspect-ratio: 16 / 10;
  background: $bg-secondary;
  border: 1px solid $border-light;
  border-radius: $radius-md;
  color: $text-placeholder;
  font-size: $font-size-base;
}

.preview-caption {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: $spacing-md;
  padding-top: $spacing-sm;
  font-size: $font-size-xs;
  color: $text-placeholder;

  .mono {
    font-family: $font-mono;
    letter-spacing: 0.04em;
    overflow-wrap: anywhere;
    text-align: right;
  }
}

.spec-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  border-top: 1px solid $border-light;

  .spec-item {
    display: grid;
    grid-template-columns: 80px minmax(0, 1fr);
    gap: $spacing-sm;
    padding: $spacing-md 0;
    border-bottom: 1px solid $border-light;
    min-width: 0;

    &:nth-child(odd) {
      padding-right: $spacing-lg;
    }

    &:nth-child(even) {
      padding-left: $spacing-lg;
      border-left: 1px solid $border-light;
    }
  }

  .spec-span {
    grid-column: 1 / -1;

    &:nth-child(even) {
      border-left: none;
      padding-left: 0;
    }
  }

  dt {
    font-size: $font-size-xs;
    letter-spacing: 0.06em;
    color: $text-secondary;
    padding-top: 2px;
  }

  dd {
    font-size: $font-size-sm;
    color: $text-primary;
    line-height: 1.7;
    overflow-wrap: anywhere;
  }

  .mono {
    font-family: $font-mono;
    font-size: $font-size-xs;
  }
}

// ========== 右侧面板 ==========
.side-panel {
  position: sticky;
  top: $spacing-xl;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
  box-shadow: $shadow-sm;
  overflow: hidden;
  min-width: 0;
}

.side-block {
  padding: $spacing-xl;
  border-bottom: 1px solid $border-light;

  &:last-child {
    border-bottom: none;
  }
}

.side-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: $spacing-sm;
  margin-bottom: $spacing-md;
}

.side-kicker {
  font-family: $font-display;
  font-size: $font-size-base;
  font-weight: $font-weight-semibold;
  color: $text-primary;
}

.side-meta {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.side-row {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;

  dt {
    font-size: $font-size-xs;
    color: $text-secondary;
    letter-spacing: 0.04em;
  }

  dd {
    font-size: $font-size-sm;
    color: $text-primary;
    line-height: 1.55;
    overflow-wrap: anywhere;
  }

  .mono {
    font-family: $font-mono;
    font-size: $font-size-xs;
  }
}

.side-action {
  width: 100%;
  margin-top: $spacing-md;
}

.side-hint,
.side-note {
  margin-top: $spacing-sm;
  font-size: $font-size-xs;
  line-height: 1.6;
  color: $text-placeholder;
}

.side-actions {
  .side-action {
    margin-top: 10px;
  }
}

// 骨架
.skeleton-sheet,
.skeleton-side {
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
  padding: $spacing-2xl;
}

.error-card {
  min-height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
}

@media (max-width: $breakpoint-lg) {
  .detail-grid {
    grid-template-columns: minmax(0, 1fr) 300px;
  }
}

@media (max-width: $breakpoint-md) {
  .asset-detail-container {
    padding: $spacing-lg;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }

  .side-panel {
    position: static;
  }

  .asset-sheet {
    padding: $spacing-lg;
  }

  .spec-grid {
    grid-template-columns: 1fr;

    .spec-item {
      &:nth-child(odd) {
        padding-right: 0;
      }

      &:nth-child(even) {
        padding-left: 0;
        border-left: none;
      }
    }
  }

  .page-meta {
    width: 100%;
    margin-left: 0;
    text-align: left;
  }
}
</style>
