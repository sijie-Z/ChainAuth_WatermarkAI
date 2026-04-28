<template>
  <div class="certificate-page">
    <el-card v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>区块链存证证书</span>
          <el-tag type="success" v-if="certificate.verified">
            <el-icon><CircleCheck /></el-icon>
            验证通过
          </el-tag>
        </div>
      </template>

      <div class="certificate-content" v-if="certificate.certificate_id">
        <!-- 证书头部 -->
        <div class="cert-header">
          <h1>数字资产存证证书</h1>
          <div class="cert-id">证书编号: {{ certificate.certificate_id }}</div>
        </div>

        <!-- 区块链徽章 -->
        <div class="blockchain-badge">
          <div class="badge-icon">
            <el-icon :size="48"><Link /></el-icon>
          </div>
          <div class="badge-text">
            <div>区块链存证</div>
            <div class="chain-name">FISCO BCOS</div>
          </div>
        </div>

        <!-- 资产信息 -->
        <el-descriptions title="资产信息" :column="2" border class="section">
          <el-descriptions-item label="资产编码">{{ certificate.asset_code }}</el-descriptions-item>
          <el-descriptions-item label="资产类型">{{ getTypeName(certificate.asset_type) }}</el-descriptions-item>
          <el-descriptions-item label="资产标题" :span="2">{{ certificate.asset_title }}</el-descriptions-item>
          <el-descriptions-item label="文件哈希" :span="2">
            <span class="hash">{{ certificate.file_hash }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="水印ID">{{ certificate.watermark_id }}</el-descriptions-item>
          <el-descriptions-item label="水印状态">
            <el-tag type="success" size="small">已嵌入</el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <!-- 区块链信息 -->
        <el-descriptions title="区块链信息" :column="2" border class="section">
          <el-descriptions-item label="交易哈希" :span="2">
            <span class="hash">{{ certificate.tx_hash }}</span>
            <el-button size="small" text type="primary" @click="copyHash(certificate.tx_hash)">
              复制
            </el-button>
          </el-descriptions-item>
          <el-descriptions-item label="区块高度">{{ certificate.block_number }}</el-descriptions-item>
          <el-descriptions-item label="存证时间">{{ formatDate(certificate.confirmed_at) }}</el-descriptions-item>
          <el-descriptions-item label="存证状态">
            <el-tag type="success" size="small">已确认</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="验证状态">
            <el-tag :type="certificate.verified ? 'success' : 'danger'" size="small">
              {{ certificate.verified ? '验证通过' : '验证失败' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <!-- 权属信息 -->
        <el-descriptions title="权属信息" :column="2" border class="section">
          <el-descriptions-item label="权利人">{{ certificate.owner_name }}</el-descriptions-item>
          <el-descriptions-item label="权利类型">{{ certificate.right_type }}</el-descriptions-item>
          <el-descriptions-item label="登记时间">{{ formatDate(certificate.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="存证有效期">永久有效</el-descriptions-item>
        </el-descriptions>

        <!-- 验证信息 -->
        <el-alert
          v-if="certificate.verified"
          title="存证验证通过"
          type="success"
          :closable="false"
          show-icon
          class="section"
        >
          <template #default>
            区块链存证数据完整，未被篡改。该证书可作为数字资产权属的区块链证据。
          </template>
        </el-alert>

        <el-alert
          v-else
          title="存证验证失败"
          type="error"
          :closable="false"
          show-icon
          class="section"
        >
          <template #default>
            区块链存证数据验证失败，数据可能被篡改。请核实数据来源。
          </template>
        </el-alert>

        <!-- 操作按钮 -->
        <div class="actions">
          <el-button type="primary" @click="downloadCertificate">下载证书</el-button>
          <el-button @click="verifyAgain">重新验证</el-button>
          <el-button @click="viewAsset">查看资产</el-button>
          <el-button @click="shareCertificate">分享</el-button>
        </div>
      </div>

      <el-empty v-else description="证书不存在或已失效" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CircleCheck, Link } from '@element-plus/icons-vue'
import { blockchainApi } from '@/api/modules'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const certificate = ref({})

async function loadCertificate() {
  loading.value = true
  try {
    const response = await blockchainApi.getCertificate(route.params.id)
    if (response.data.code === 200) {
      certificate.value = response.data.data
    }
  } catch (error) {
    ElMessage.error('加载证书失败')
  } finally {
    loading.value = false
  }
}

function copyHash(hash) {
  navigator.clipboard.writeText(hash)
  ElMessage.success('已复制到剪贴板')
}

async function verifyAgain() {
  try {
    const response = await blockchainApi.verify(certificate.value.asset_id)
    if (response.data.code === 200) {
      certificate.value.verified = response.data.data.verified
      ElMessage.success(certificate.value.verified ? '验证通过' : '验证失败')
    }
  } catch (error) {
    ElMessage.error('验证失败')
  }
}

function downloadCertificate() {
  ElMessage.info('证书下载功能开发中...')
}

function viewAsset() {
  if (certificate.value.asset_id) {
    router.push(`/assets/${certificate.value.asset_id}`)
  }
}

function shareCertificate() {
  const url = window.location.href
  navigator.clipboard.writeText(url)
  ElMessage.success('证书链接已复制')
}

function getTypeName(type) {
  const map = { image: '影像', model: '模型', vector: '矢量', document: '文献', video: '视频' }
  return map[type] || type
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(() => {
  loadCertificate()
})
</script>

<style scoped>
.certificate-page {
  padding: 20px;
  min-height: 100vh;
  background: #f5f7fa;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.certificate-content {
  max-width: 800px;
  margin: 0 auto;
}

.cert-header {
  text-align: center;
  padding: 30px 0;
  border-bottom: 2px solid #409eff;
}

.cert-header h1 {
  font-size: 28px;
  color: #333;
  margin-bottom: 10px;
}

.cert-id {
  font-size: 14px;
  color: #999;
}

.blockchain-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 15px;
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  border-radius: 8px;
  margin: 20px 0;
}

.badge-icon {
  opacity: 0.9;
}

.badge-text {
  text-align: left;
}

.badge-text div:first-child {
  font-size: 18px;
  font-weight: 600;
}

.chain-name {
  font-size: 12px;
  opacity: 0.8;
}

.section {
  margin: 20px 0;
}

.hash {
  font-family: monospace;
  font-size: 12px;
  word-break: break-all;
}

.actions {
  display: flex;
  justify-content: center;
  gap: 15px;
  padding: 30px 0;
}
</style>