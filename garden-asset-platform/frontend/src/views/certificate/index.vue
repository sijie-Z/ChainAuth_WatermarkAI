<template>
  <div class="certificate-page">
    <!-- 工具栏 -->
    <div class="toolbar no-print">
      <el-button @click="$router.back()" text>
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
      <div class="toolbar-actions">
        <el-button @click="printCertificate">
          <el-icon><Printer /></el-icon>
          打印证书
        </el-button>
        <el-button @click="shareCertificate">
          <el-icon><Share /></el-icon>
          分享链接
        </el-button>
        <el-button type="primary" @click="viewAsset" :disabled="!certificate.asset_id">
          查看资产
        </el-button>
      </div>
    </div>

    <!-- 证书主体 -->
    <div v-loading="loading" class="certificate-body" ref="certBody">
      <template v-if="certificate.certificate_id">
        <!-- 顶部 -->
        <div class="cert-header">
          <div class="cert-emblem" aria-hidden="true">园</div>
          <h1 class="cert-title">数字资产存证证书</h1>
          <p class="cert-subtitle">Digital Asset Certificate of Evidence</p>
          <div class="cert-id">证书编号：{{ certificate.certificate_id }}</div>
        </div>

        <div class="cert-divider" aria-hidden="true"></div>

        <!-- 存证信息 -->
        <div class="cert-section">
          <div class="section-title">存证信息</div>
          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">资产编码</span>
              <span class="info-value">{{ certificate.asset_code || '-' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">资产类型</span>
              <span class="info-value">{{ getTypeName(certificate.asset_type) }}</span>
            </div>
            <div class="info-item full">
              <span class="info-label">资产标题</span>
              <span class="info-value">{{ certificate.asset_title || '-' }}</span>
            </div>
            <div class="info-item full">
              <span class="info-label">文件哈希 (SHA256)</span>
              <span class="info-value hash">{{ certificate.file_hash || '-' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">水印编号</span>
              <span class="info-value">{{ certificate.watermark_id || '-' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">水印状态</span>
              <el-tag :type="certificate.watermark_id ? 'success' : 'info'" size="small">
                {{ certificate.watermark_id ? '已嵌入' : '未嵌入' }}
              </el-tag>
            </div>
          </div>
        </div>

        <!-- 区块链信息 -->
        <div class="cert-section">
          <div class="section-title">区块链存证</div>
          <div class="blockchain-card">
            <el-icon class="bc-icon"><Link /></el-icon>
            <div class="bc-info">
              <div class="bc-name">FISCO BCOS 联盟链</div>
              <div class="bc-desc">国产自主可控区块链底层平台</div>
            </div>
          </div>
          <div class="info-grid">
            <div class="info-item full">
              <span class="info-label">交易哈希</span>
              <span class="info-value hash">{{ certificate.tx_hash || '-' }}</span>
              <el-button size="small" text type="primary" @click="copyHash(certificate.tx_hash)" class="no-print">
                复制
              </el-button>
            </div>
            <div class="info-item">
              <span class="info-label">区块高度</span>
              <span class="info-value">{{ certificate.block_number || '-' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">存证时间</span>
              <span class="info-value">{{ formatDate(certificate.confirmed_at) }}</span>
            </div>
          </div>
        </div>

        <!-- 权属信息 -->
        <div class="cert-section">
          <div class="section-title">权属信息</div>
          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">权利人</span>
              <span class="info-value">{{ certificate.owner_name || '-' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">权利类型</span>
              <span class="info-value">{{ certificate.right_type || '未提供' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">登记时间</span>
              <span class="info-value">{{ formatDate(certificate.created_at) || '未提供' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">有效期</span>
              <span class="info-value">{{ certificate.valid_until ? formatDate(certificate.valid_until) : '未设置' }}</span>
            </div>
          </div>
        </div>

        <!-- 链上存证状态 -->
        <div class="verify-section" :class="certificate.tx_hash ? 'verified' : 'failed'">
          <el-icon class="verify-icon">
            <CircleCheck v-if="certificate.tx_hash" />
            <CircleClose v-else />
          </el-icon>
          <div class="verify-text">
            <div class="verify-title">{{ certificate.tx_hash ? '链上存证交易已生成' : '尚未生成链上存证交易' }}</div>
            <div class="verify-desc">
              {{ certificate.tx_hash
                ? '存证信息已写入区块链，可凭交易哈希与区块高度在链上复核。'
                : '该资产尚未完成上链存证，请先完成水印嵌入与上链操作后再查看证书。' }}
            </div>
          </div>
        </div>

        <!-- 平台签章 -->
        <div class="cert-signature">
          <span class="signature-org">苏州园林数字资产平台</span>
          <span class="cert-seal" aria-hidden="true">园</span>
        </div>

        <!-- 页脚 -->
        <div class="cert-footer">
          <p>本证书由苏州园林数字资产平台签发，链上状态以交易哈希与区块高度为准</p>
          <p>证书字段以平台台账记录为准，如需权属证明请联系权利人核验</p>
          <p class="cert-footer-date">签发日期：{{ formatDate(certificate.created_at) || '未提供' }}</p>
        </div>
      </template>

      <el-empty v-else-if="!loading" :description="loadError ? '证书加载失败' : '证书不存在或已失效'">
        <el-button v-if="loadError" type="primary" @click="loadCertificate">重试</el-button>
        <el-button v-else type="primary" @click="$router.push('/home')">返回首页</el-button>
      </el-empty>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Printer, Share, Link, CircleCheck, CircleClose } from '@element-plus/icons-vue'
import { blockchainApi } from '@/api/modules'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const loadError = ref(false)
const certificate = ref({})
const certBody = ref(null)

async function loadCertificate() {
  loading.value = true
  loadError.value = false
  try {
    const response = await blockchainApi.getCertificate(route.params.id)
    if (response.data.code === 200) {
      // 后端返回 { data: { certificate: {...}, asset: {...} } }
      const payload = response.data.data || {}
      const certificateData = payload.certificate || {}
      const assetData = payload.asset || {}
      certificate.value = {
        ...assetData,
        ...certificateData,
        asset_title: assetData.title || certificateData.asset_title || '',
        owner_name: certificateData.creator_name || assetData.owner_name || '',
        confirmed_at: certificateData.confirmed_at || certificateData.created_at,
        right_type: getOwnershipName(certificateData.ownership_type)
      }
    } else {
      certificate.value = {}
    }
  } catch {
    loadError.value = true
    certificate.value = {}
  } finally {
    loading.value = false
  }
}

function copyHash(hash) {
  if (!hash) return
  navigator.clipboard.writeText(hash)
  ElMessage.success('已复制到剪贴板')
}

function printCertificate() {
  window.print()
}

function viewAsset() {
  if (certificate.value.asset_id) {
    router.push(`/assets/${certificate.value.asset_id}`)
  }
}

function shareCertificate() {
  navigator.clipboard.writeText(window.location.href)
  ElMessage.success('证书链接已复制')
}

function getTypeName(type) {
  if (!type) return '-'
  const map = { image: '影像', model: '模型', vector: '矢量', document: '文献', video: '视频' }
  return map[type] || type
}

function getOwnershipName(type) {
  const map = { original: '原创', authorized: '授权使用', derived: '衍生作品' }
  return map[type] || '未提供'
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(() => {
  loadCertificate()
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.certificate-page {
  min-height: 100vh;
  padding: 24px;
  background: $bg-secondary;
}

.toolbar {
  max-width: 860px;
  margin: 0 auto 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

// 纸面
.certificate-body {
  position: relative;
  max-width: 860px;
  margin: 0 auto;
  padding: 48px 56px;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  box-shadow: $shadow-sm;
  overflow: hidden;
}

// 证头
.cert-header {
  position: relative;
  margin-bottom: 28px;
  text-align: center;
}

.cert-emblem {
  width: 44px;
  height: 44px;
  margin: 0 auto 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: $bg-secondary;
  border: 1px solid $border-color;
  border-radius: $radius-sm;
  color: $primary-dark;
  font-family: $font-display;
  font-size: 22px;
  line-height: 1;
  user-select: none;
}

.cert-title {
  margin: 0 0 6px;
  font-family: $font-display;
  font-size: 30px;
  font-weight: 600;
  color: $text-primary;
  letter-spacing: 0.12em;
}

.cert-subtitle {
  margin: 0 0 12px;
  font-size: 12px;
  color: $text-placeholder;
  letter-spacing: 0.2em;
}

.cert-id {
  font-family: $font-mono;
  font-size: 13px;
  color: $text-secondary;
}

.cert-divider {
  margin: 28px 0;
  border-top: 1px solid $border-color;
}

// 分节
.cert-section {
  margin-bottom: 28px;
}

.section-title {
  margin-bottom: 16px;
  padding-left: 12px;
  border-left: 2px solid $accent-color;
  font-family: $font-display;
  font-size: 16px;
  font-weight: 600;
  color: $text-primary;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px 24px;

  .info-item {
    display: flex;
    flex-direction: column;
    gap: 4px;

    &.full {
      grid-column: 1 / -1;
    }
  }

  .info-label {
    font-size: 12px;
    color: $text-placeholder;
  }

  .info-value {
    font-size: 13px;
    font-weight: 500;
    color: $text-primary;

    &.hash {
      font-family: $font-mono;
      font-size: 11px;
      word-break: break-all;
      color: $text-secondary;
    }
  }
}

.blockchain-card {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 16px;
  padding: 18px 20px;
  background: $bg-secondary;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
  color: $primary-dark;

  .bc-icon {
    flex-shrink: 0;
    font-size: 28px;
    color: $primary-color;
  }

  .bc-name {
    font-family: $font-display;
    font-size: 16px;
    font-weight: 600;
  }

  .bc-desc {
    font-size: 12px;
    color: $text-secondary;
  }
}

// 验证结果
.verify-section {
  display: flex;
  align-items: center;
  gap: 18px;
  margin-bottom: 28px;
  padding: 22px 24px;
  border-radius: $radius-lg;

  &.verified {
    background: $bg-secondary;
    border: 1px solid $border-color;
    color: $primary-color;
  }

  &.failed {
    background: $bg-card;
    border: 1px solid $accent-color;
    color: $accent-color;
  }

  .verify-icon {
    flex-shrink: 0;
    font-size: 40px;
  }

  .verify-text {
    flex: 1;
    min-width: 0;
  }

  .verify-title {
    margin-bottom: 4px;
    font-family: $font-display;
    font-size: 16px;
    font-weight: 600;
  }

  .verify-desc {
    font-size: 13px;
    line-height: 1.7;
    color: $text-secondary;
  }
}

// 朱砂印章
.cert-signature {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 16px;
  margin-bottom: 20px;
  padding-top: 4px;
}

.signature-org {
  font-family: $font-display;
  font-size: 14px;
  letter-spacing: 0.08em;
  color: $text-secondary;
}

.cert-seal {
  width: 48px;
  height: 48px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: $accent-color;
  border-radius: $radius-sm;
  color: $bg-card;
  font-family: $font-display;
  font-size: 24px;
  line-height: 1;
  transform: rotate(-6deg);
  user-select: none;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}

// 页脚
.cert-footer {
  padding-top: 22px;
  border-top: 1px solid $border-color;
  text-align: center;

  p {
    margin: 4px 0;
    font-size: 12px;
    color: $text-placeholder;
  }

  .cert-footer-date {
    margin-top: 8px;
    font-family: $font-mono;
  }
}

// 打印样式
@media print {
  .certificate-page {
    padding: 0;
    background: $bg-card;
  }

  .no-print,
  .toolbar {
    display: none !important;
  }

  .certificate-body {
    max-width: 100%;
    padding: 40px 32px;
    border-radius: 0;
    box-shadow: none;
  }
}

@media (max-width: 576px) {
  .certificate-page {
    padding: 16px;
  }

  .toolbar {
    flex-wrap: wrap;
  }

  .certificate-body {
    padding: 24px 20px;
  }

  .cert-title {
    font-size: 22px;
    letter-spacing: 0.08em;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }

  .cert-signature {
    justify-content: flex-start;
  }
}
</style>
