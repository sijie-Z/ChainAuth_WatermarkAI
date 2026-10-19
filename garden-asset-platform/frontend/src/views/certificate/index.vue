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
        <!-- 证书水印背景 -->
        <div class="cert-bg-pattern"></div>

        <!-- 顶部装饰 -->
        <div class="cert-header">
          <div class="cert-header-decoration">
            <svg viewBox="0 0 200 20" fill="none">
              <path d="M0 10 Q50 0 100 10 Q150 20 200 10" stroke="currentColor" stroke-width="1.5" fill="none" opacity="0.3"/>
              <circle cx="100" cy="10" r="3" fill="currentColor" opacity="0.4"/>
              <circle cx="80" cy="10" r="2" fill="currentColor" opacity="0.2"/>
              <circle cx="120" cy="10" r="2" fill="currentColor" opacity="0.2"/>
            </svg>
          </div>
          <div class="cert-logo">
            <svg viewBox="0 0 32 32" fill="none" width="40" height="40">
              <path d="M16 2L4 10v12l12 8 12-8V10L16 2z" fill="url(#certLogoGrad)"/>
              <path d="M16 8L8 13v6l8 5 8-5v-6l-8-5z" fill="white" fill-opacity="0.3"/>
              <defs>
                <linearGradient id="certLogoGrad" x1="4" y1="2" x2="28" y2="30">
                  <stop stop-color="#2f6b5a"/>
                  <stop offset="1" stop-color="#1c5145"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
          <h1 class="cert-title">数字资产存证证书</h1>
          <p class="cert-subtitle">Digital Asset Certificate of Evidence</p>
          <div class="cert-id">证书编号：{{ certificate.certificate_id }}</div>
        </div>

        <div class="cert-divider">
          <span class="divider-icon">
            <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
            </svg>
          </span>
        </div>

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
              <el-tag type="success" size="small">已嵌入</el-tag>
            </div>
          </div>
        </div>

        <!-- 区块链信息 -->
        <div class="cert-section">
          <div class="section-title">区块链存证</div>
          <div class="blockchain-card">
            <div class="bc-icon">
              <svg viewBox="0 0 48 48" fill="none" width="48" height="48">
                <rect x="2" y="2" width="44" height="44" rx="12" fill="currentColor" opacity="0.1"/>
                <path d="M24 10L16 15v10l8 5 8-5V15L24 10z" fill="currentColor" opacity="0.6"/>
                <path d="M24 17L19 20.5v5l5 3 5-3v-5L24 17z" fill="currentColor"/>
              </svg>
            </div>
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
              <span class="info-value">{{ certificate.right_type || '著作权' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">登记时间</span>
              <span class="info-value">{{ formatDate(certificate.created_at) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">有效期</span>
              <span class="info-value">永久有效</span>
            </div>
          </div>
        </div>

        <!-- 验证结果 -->
        <div class="verify-section" :class="{ verified: certificate.verified, failed: !certificate.verified }">
          <div class="verify-icon">
            <svg v-if="certificate.verified" viewBox="0 0 64 64" fill="none">
              <circle cx="32" cy="32" r="28" stroke="currentColor" stroke-width="2"/>
              <path d="M20 32L28 40L44 24" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <svg v-else viewBox="0 0 64 64" fill="none">
              <circle cx="32" cy="32" r="28" stroke="currentColor" stroke-width="2"/>
              <path d="M24 24L40 40M40 24L24 40" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
            </svg>
          </div>
          <div class="verify-text">
            <div class="verify-title">{{ certificate.verified ? '存证验证通过' : '存证验证失败' }}</div>
            <div class="verify-desc">
              {{ certificate.verified
                ? '区块链存证数据完整，未被篡改。该证书可作为数字资产权属的区块链证据。'
                : '区块链存证数据验证失败，数据可能被篡改。请核实数据来源。' }}
            </div>
          </div>
          <el-button v-if="!certificate.verified" size="small" @click="verifyAgain" class="no-print">
            重新验证
          </el-button>
        </div>

        <!-- 页脚 -->
        <div class="cert-footer">
          <p>本证书由苏州园林数字资产平台基于FISCO BCOS区块链技术签发</p>
          <p>证书数据已上链存证，不可篡改，永久可追溯</p>
          <p class="cert-footer-date">签发日期：{{ formatDate(certificate.created_at || new Date().toISOString()) }}</p>
        </div>
      </template>

      <el-empty v-else-if="!loading" description="证书不存在或已失效">
        <el-button type="primary" @click="$router.push('/home')">返回首页</el-button>
      </el-empty>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Printer, Share } from '@element-plus/icons-vue'
import { blockchainApi } from '@/api/modules'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const certificate = ref({})
const certBody = ref(null)

async function loadCertificate() {
  loading.value = true
  try {
    const response = await blockchainApi.getCertificate(route.params.id)
    if (response.data.code === 200) {
      certificate.value = response.data.data
    }
  } catch {
    ElMessage.error('加载证书失败')
  } finally {
    loading.value = false
  }
}

function copyHash(hash) {
  if (!hash) return
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
  } catch {
    ElMessage.error('验证失败')
  }
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

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.certificate-page {
  min-height: 100vh;
  background: $bg-primary;
  padding: 24px;
}

.toolbar {
  max-width: 860px;
  margin: 0 auto 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.toolbar-actions {
  display: flex;
  gap: 8px;
}

.certificate-body {
  max-width: 860px;
  margin: 0 auto;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  box-shadow: $shadow-md;
  padding: 48px 56px;
  position: relative;
  overflow: hidden;
}

.cert-bg-pattern {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(circle at 20% 20%, rgba(47, 107, 90, 0.04) 0%, transparent 50%),
                    radial-gradient(circle at 80% 80%, rgba(47, 107, 90, 0.04) 0%, transparent 50%);
  pointer-events: none;
}

.cert-header {
  text-align: center;
  margin-bottom: 24px;
  position: relative;
}

.cert-header-decoration {
  color: $primary-color;
  margin-bottom: 16px;
}

.cert-logo {
  margin-bottom: 20px;
}

.cert-title {
  font-family: $font-display;
  font-size: 30px;
  font-weight: 600;
  color: $text-primary;
  margin: 0 0 4px;
  letter-spacing: 0.12em;
}

.cert-subtitle {
  font-size: $font-size-xs;
  color: $text-placeholder;
  margin: 0 0 12px;
  letter-spacing: 0.2em;
}

.cert-id {
  font-size: $font-size-sm;
  color: $text-secondary;
  font-family: $font-mono;
}

.cert-divider {
  text-align: center;
  margin: 28px 0;
  position: relative;

  &::before {
    content: '';
    position: absolute;
    left: 0;
    right: 0;
    top: 50%;
    height: 1px;
    background: linear-gradient(90deg, transparent, $border-color, transparent);
  }

  .divider-icon {
    display: inline-flex;
    padding: 0 16px;
    background: $bg-card;
    position: relative;
    color: $primary-color;
  }
}

.cert-section {
  margin-bottom: 28px;
}

.section-title {
  font-family: $font-display;
  font-size: $font-size-lg;
  font-weight: 600;
  color: $text-primary;
  margin-bottom: 16px;
  padding-left: 12px;
  border-left: 2px solid $accent-color;
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
    font-size: $font-size-xs;
    color: $text-placeholder;
  }

  .info-value {
    font-size: $font-size-sm;
    color: $text-primary;
    font-weight: $font-weight-medium;

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
  gap: 16px;
  padding: 20px;
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.08), rgba(5, 150, 105, 0.04));
  border-radius: $radius-lg;
  margin-bottom: 16px;
  color: $primary-dark;

  .bc-name {
    font-size: $font-size-lg;
    font-weight: $font-weight-semibold;
  }

  .bc-desc {
    font-size: $font-size-xs;
    color: $text-secondary;
  }
}

.verify-section {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 24px;
  border-radius: $radius-lg;
  margin-bottom: 28px;

  &.verified {
    background: $success-bg;
    color: $success-color;
  }

  &.failed {
    background: $error-bg;
    color: $error-color;
  }

  .verify-icon {
    width: 64px;
    height: 64px;
    flex-shrink: 0;

    svg {
      width: 100%;
      height: 100%;
    }
  }

  .verify-text {
    flex: 1;
  }

  .verify-title {
    font-size: $font-size-lg;
    font-weight: $font-weight-semibold;
    margin-bottom: 4px;
  }

  .verify-desc {
    font-size: $font-size-sm;
    color: $text-secondary;
  }
}

.cert-footer {
  text-align: center;
  padding-top: 24px;
  border-top: 1px solid $border-light;

  p {
    margin: 4px 0;
    font-size: $font-size-xs;
    color: $text-placeholder;
  }

  .cert-footer-date {
    font-family: $font-mono;
    margin-top: 8px;
  }
}

// 打印样式
@media print {
  .certificate-page {
    background: white;
    padding: 0;
  }

  .no-print, .toolbar {
    display: none !important;
  }

  .certificate-body {
    box-shadow: none;
    border-radius: 0;
    padding: 40px 32px;
    max-width: 100%;
  }
}

@media (max-width: $breakpoint-sm) {
  .certificate-body {
    padding: 24px 20px;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }

  .cert-title {
    font-size: 22px;
  }
}
</style>
