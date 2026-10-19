<template>
  <div class="asset-detail-container">
    <!-- 加载骨架屏 -->
    <el-skeleton :loading="loading" animated>
      <template #template>
        <el-row :gutter="20">
          <el-col :span="16">
            <el-card>
              <template #header>
                <div style="display: flex; justify-content: space-between; align-items: center">
                  <el-skeleton-item variant="text" style="width: 200px; height: 24px" />
                  <el-skeleton-item variant="text" style="width: 60px; height: 24px" />
                </div>
              </template>
              <el-skeleton-item variant="image" style="width: 100%; height: 400px" />
              <div style="margin-top: 20px">
                <el-skeleton :rows="4" animated />
              </div>
            </el-card>
          </el-col>
          <el-col :span="8">
            <el-card v-for="i in 3" :key="i" style="margin-bottom: 20px">
              <template #header>
                <el-skeleton-item variant="text" style="width: 100px" />
              </template>
              <el-skeleton :rows="2" animated />
            </el-card>
          </el-col>
        </el-row>
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
        <template v-else>
          <el-row :gutter="20">
            <!-- 左侧：资产预览 -->
            <el-col :xs="24" :sm="24" :md="16">
              <el-card>
                <template #header>
                  <div class="card-header">
                    <span>{{ asset.title }}</span>
                    <StatusTag :status="asset.status" />
                  </div>
                </template>

                <!-- 预览区域 -->
                <div class="preview-area">
                  <img v-if="asset.asset_type === 'image'" :src="getAssetUrl(asset)" alt="资产预览" />
                  <div v-else class="preview-placeholder">
                    <el-icon :size="64"><Document /></el-icon>
                    <span>{{ asset.file_format }}</span>
                  </div>
                </div>

                <!-- 基本信息 -->
                <el-descriptions title="基本信息" :column="2" border>
                  <el-descriptions-item label="资产编码">{{ asset.asset_code }}</el-descriptions-item>
                  <el-descriptions-item label="文件格式">{{ asset.file_format }}</el-descriptions-item>
                  <el-descriptions-item label="文件大小">{{ formatSize(asset.file_size) }}</el-descriptions-item>
                  <el-descriptions-item label="创建时间">{{ formatDate(asset.created_at) }}</el-descriptions-item>
                  <el-descriptions-item label="描述" :span="2">{{ asset.description || '暂无描述' }}</el-descriptions-item>
                </el-descriptions>
              </el-card>
            </el-col>

            <!-- 右侧：状态与操作 -->
            <el-col :xs="24" :sm="24" :md="8">
              <!-- 水印状态 -->
              <el-card class="status-card">
                <template #header>
                  <div class="card-header">
                    <span>水印状态</span>
                    <StatusTag :status="asset.watermark_status || 'pending'" />
                  </div>
                </template>
                <div v-if="asset.watermark_id" class="status-item">
                  <span class="label">水印ID：</span>
                  <span class="value mono">{{ asset.watermark_id }}</span>
                </div>
                <div v-if="asset.vr_value !== undefined" class="status-item">
                  <span class="label">鲁棒性值：</span>
                  <span class="value">{{ asset.vr_value?.toFixed(4) || '-' }}</span>
                </div>
                <el-button
                  v-if="asset.watermark_status !== 'embedded'"
                  type="primary"
                  style="width: 100%; margin-top: 12px"
                  :loading="watermarking"
                  @click="embedWatermark"
                >
                  嵌入水印
                </el-button>
                <el-button
                  v-else
                  type="success"
                  style="width: 100%; margin-top: 12px"
                  :loading="extracting"
                  @click="extractWatermark"
                >
                  提取水印
                </el-button>
              </el-card>

              <!-- 区块链存证 -->
              <el-card class="status-card">
                <template #header>
                  <div class="card-header">
                    <span>区块链存证</span>
                    <StatusTag :status="asset.chain_status || 'pending'" />
                  </div>
                </template>
                <div v-if="asset.chain_tx_hash" class="status-item">
                  <span class="label">交易哈希：</span>
                  <span class="value mono">{{ asset.chain_tx_hash }}</span>
                </div>
                <div v-if="asset.certificate_id" class="status-item">
                  <span class="label">证书ID：</span>
                  <span class="value mono">{{ asset.certificate_id }}</span>
                </div>
                <el-button
                  v-if="asset.chain_status !== 'confirmed'"
                  type="primary"
                  style="width: 100%; margin-top: 12px"
                  :disabled="asset.watermark_status !== 'embedded'"
                  :loading="chaining"
                  @click="registerChain"
                >
                  上链存证
                </el-button>
                <el-button
                  v-else
                  type="success"
                  style="width: 100%; margin-top: 12px"
                  @click="viewCertificate"
                >
                  查看证书
                </el-button>
              </el-card>

              <!-- 操作按钮 -->
              <el-card class="status-card">
                <template #header>操作</template>
                <el-button type="primary" style="width: 100%; margin-bottom: 10px" @click="applyLicense">
                  申请授权
                </el-button>
                <el-button style="width: 100%" @click="goBack">返回列表</el-button>
              </el-card>
            </el-col>
          </el-row>
        </template>
      </template>
    </el-skeleton>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Document } from '@element-plus/icons-vue'
import { assetApi, watermarkApi, blockchainApi } from '@/api/modules'

const route = useRoute()
const router = useRouter()

const asset = ref({})
const loading = ref(true)
const loadError = ref(false)
const watermarking = ref(false)
const extracting = ref(false)
const chaining = ref(false)

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

function getAssetUrl(asset) {
  if (asset.thumbnail_path) return asset.thumbnail_path
  const colors = { image: '#2f6b5a', vector: '#4c6e8a', model: '#6d5b7a', document: '#b07a2a', video: '#a6402f' }
  const color = (colors[asset.asset_type] || '#5b675f').replace('#', '')
  const label = (asset.asset_type || 'FILE').substring(0, 3).toUpperCase()
  return `data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="800" height="600"%3E%3Crect fill="%23${color}" width="800" height="600" rx="12"/%3E%3Ctext x="400" y="310" text-anchor="middle" fill="white" font-size="48"%3E${label}%3C/text%3E%3C/svg%3E`
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
  padding: $spacing-lg;
  min-height: 100vh;
  background: $bg-primary;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preview-area {
  min-height: 400px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  background: $bg-secondary;
  margin-bottom: $spacing-lg;
  border-radius: $radius-md;
  gap: $spacing-md;

  img {
    max-width: 100%;
    max-height: 400px;
    object-fit: contain;
  }
}

.preview-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: $spacing-sm;
  color: $text-placeholder;
  font-size: $font-size-lg;
}

.status-card {
  margin-bottom: $spacing-lg;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-sm;

  .label {
    color: $text-secondary;
    font-size: $font-size-sm;
  }

  .value {
    font-size: $font-size-sm;
    color: $text-primary;
    max-width: 180px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mono {
    font-family: 'Courier New', monospace;
    font-size: $font-size-xs;
  }
}

.error-card {
  min-height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
}

@media (max-width: $breakpoint-sm) {
  .asset-detail-container {
    padding: $spacing-md;
  }

  .preview-area {
    min-height: 250px;
  }

  .status-item .value {
    max-width: 120px;
  }
}
</style>
