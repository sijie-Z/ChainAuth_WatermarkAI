<template>
  <div class="asset-detail-container">
    <el-row :gutter="20">
      <!-- 左侧：资产预览 -->
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>{{ asset.title }}</span>
              <el-tag>{{ getTypeName(asset.asset_type) }}</el-tag>
            </div>
          </template>

          <!-- 预览区域 -->
          <div class="preview-area">
            <img v-if="asset.asset_type === 'image'" :src="getAssetUrl(asset)" alt="资产预览" />
            <div v-else class="preview-placeholder">
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
      <el-col :span="8">
        <!-- 水印状态 -->
        <el-card class="status-card">
          <template #header>水印状态</template>
          <div class="status-item">
            <span class="label">状态：</span>
            <el-tag :type="asset.watermark_status === 'embedded' ? 'success' : 'info'">
              {{ asset.watermark_status === 'embedded' ? '已嵌入' : '未嵌入' }}
            </el-tag>
          </div>
          <div v-if="asset.watermark_id" class="status-item">
            <span class="label">水印ID：</span>
            <span class="value">{{ asset.watermark_id }}</span>
          </div>
          <el-button
            v-if="asset.watermark_status !== 'embedded'"
            type="primary"
            style="width: 100%; margin-top: 10px"
            @click="embedWatermark"
          >
            嵌入水印
          </el-button>
          <el-button
            v-else
            type="success"
            style="width: 100%; margin-top: 10px"
            @click="extractWatermark"
          >
            提取水印
          </el-button>
        </el-card>

        <!-- 区块链存证 -->
        <el-card class="status-card">
          <template #header>区块链存证</template>
          <div class="status-item">
            <span class="label">状态：</span>
            <el-tag :type="asset.chain_status === 'confirmed' ? 'success' : 'info'">
              {{ asset.chain_status === 'confirmed' ? '已存证' : '未存证' }}
            </el-tag>
          </div>
          <div v-if="asset.certificate_id" class="status-item">
            <span class="label">证书ID：</span>
            <span class="value">{{ asset.certificate_id }}</span>
          </div>
          <el-button
            v-if="asset.chain_status !== 'confirmed'"
            type="primary"
            style="width: 100%; margin-top: 10px"
            :disabled="asset.watermark_status !== 'embedded'"
            @click="registerChain"
          >
            上链存证
          </el-button>
          <el-button
            v-else
            type="success"
            style="width: 100%; margin-top: 10px"
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { assetApi, watermarkApi, blockchainApi } from '@/api/modules'

const route = useRoute()
const router = useRouter()

const asset = ref({})

async function loadAsset() {
  try {
    const response = await assetApi.getDetail(route.params.id)
    if (response.data.code === 200) {
      asset.value = response.data.data
    }
  } catch (error) {
    ElMessage.error('加载资产失败')
  }
}

async function embedWatermark() {
  try {
    const response = await watermarkApi.embed(asset.value.id)
    if (response.data.code === 200) {
      ElMessage.success('水印嵌入成功')
      loadAsset()
    }
  } catch (error) {
    ElMessage.error('水印嵌入失败')
  }
}

async function extractWatermark() {
  try {
    const response = await watermarkApi.extract(asset.value.id)
    if (response.data.code === 200) {
      ElMessage.success('水印提取成功，NC值: ' + response.data.data.nc_value)
    }
  } catch (error) {
    ElMessage.error('水印提取失败')
  }
}

async function registerChain() {
  try {
    const response = await blockchainApi.register(asset.value.id)
    if (response.data.code === 200) {
      ElMessage.success('存证成功')
      loadAsset()
    }
  } catch (error) {
    ElMessage.error('存证失败')
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
  return `/api/assets/${asset.id}/preview`
}

function getTypeName(type) {
  const map = { image: '影像', model: '模型', vector: '矢量', document: '文献', video: '视频' }
  return map[type] || type
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

<style scoped>
.asset-detail-container {
  padding: 20px;
  min-height: 100vh;
  background: #f5f7fa;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preview-area {
  min-height: 400px;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #f5f5f5;
  margin-bottom: 20px;
  border-radius: 4px;
}

.preview-area img {
  max-width: 100%;
  max-height: 400px;
  object-fit: contain;
}

.preview-placeholder {
  font-size: 48px;
  color: #999;
}

.status-card {
  margin-bottom: 20px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
}

.status-item .label {
  color: #666;
}

.status-item .value {
  font-family: monospace;
  word-break: break-all;
}
</style>