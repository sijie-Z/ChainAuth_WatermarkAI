<template>
  <div class="trace-page">
    <div class="trace-shell">
      <header class="trace-header">
        <div class="trace-heading">
          <h1 class="trace-title">溯源查询</h1>
          <p class="trace-subtitle">上传图片或输入水印编号，核验资产来源与链上存证记录。</p>
        </div>
        <router-link to="/home" class="trace-back">
          返回首页
          <el-icon><ArrowRight /></el-icon>
        </router-link>
      </header>

      <!-- 查询表单 -->
      <section class="query-card">
        <el-tabs v-model="activeTab">
          <el-tab-pane label="上传图片溯源" name="upload">
            <el-upload
              drag
              :auto-upload="false"
              :on-change="handleFileChange"
              :limit="1"
              accept="image/*"
            >
              <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
              <div class="el-upload__text">
                将图片拖到此处，或 <em>点击上传</em>
              </div>
            </el-upload>
          </el-tab-pane>

          <el-tab-pane label="水印ID溯源" name="watermark">
            <el-input
              v-model="watermarkId"
              placeholder="请输入水印ID，如：ZY-IMG-20260315143522-A3F8"
              class="watermark-input"
            />
          </el-tab-pane>
        </el-tabs>

        <div class="query-actions">
          <el-button type="primary" :loading="loading" @click="doTrace">
            <el-icon><Search /></el-icon>
            开始溯源
          </el-button>
        </div>
      </section>

      <!-- 溯源结果 -->
      <section v-if="traceResult" class="result-card">
        <header class="result-header">
          <h2 class="result-title">溯源结果</h2>
          <el-tag :type="traceResult.verified ? 'success' : 'danger'">
            {{ traceResult.verified ? '验证通过' : '验证失败' }}
          </el-tag>
        </header>

        <template v-if="traceResult.verified">
          <!-- 资产信息 -->
          <el-descriptions title="资产信息" :column="2" border>
            <el-descriptions-item label="资产编码">{{ traceResult.asset_code }}</el-descriptions-item>
            <el-descriptions-item label="标题">{{ traceResult.title }}</el-descriptions-item>
            <el-descriptions-item label="水印ID">{{ traceResult.watermark_id }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatDate(traceResult.created_at) }}</el-descriptions-item>
          </el-descriptions>

          <!-- 区块链存证 -->
          <el-descriptions title="区块链存证" :column="2" border class="result-block">
            <el-descriptions-item label="存证状态">
              <el-tag type="success">已存证</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="证书ID">
              <el-link type="primary" @click="viewCertificate">{{ traceResult.certificate_id }}</el-link>
            </el-descriptions-item>
            <el-descriptions-item label="交易哈希">
              <span class="mono">{{ traceResult.tx_hash }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="存证时间">{{ formatDate(traceResult.confirmed_at) }}</el-descriptions-item>
          </el-descriptions>

          <!-- 操作 -->
          <div class="result-actions">
            <el-button type="primary" @click="viewAsset">查看资产详情</el-button>
            <el-button @click="downloadReport">下载溯源报告</el-button>
          </div>
        </template>

        <template v-else>
          <EmptyState description="未找到对应的资产记录，可能为未授权使用">
            <template #action>
              <el-button type="primary">举报侵权</el-button>
            </template>
          </EmptyState>
        </template>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowRight, Search, UploadFilled } from '@element-plus/icons-vue'
import { watermarkApi, blockchainApi } from '@/api/modules'

const router = useRouter()

const activeTab = ref('upload')
const loading = ref(false)
const watermarkId = ref('')
const uploadedFile = ref(null)
const traceResult = ref(null)

function handleFileChange(file) {
  uploadedFile.value = file.raw
}

async function doTrace() {
  loading.value = true
  traceResult.value = null

  try {
    let response

    if (activeTab.value === 'upload' && uploadedFile.value) {
      const formData = new FormData()
      formData.append('file', uploadedFile.value)
      response = await watermarkApi.trace(formData)
    } else if (activeTab.value === 'watermark' && watermarkId.value) {
      response = await blockchainApi.verifyByWatermark(watermarkId.value)
    } else {
      ElMessage.warning('请上传图片或输入水印ID')
      return
    }

    if (response.data.code === 200) {
      traceResult.value = response.data.data
    }
  } catch (error) {
    ElMessage.error('溯源查询失败')
  } finally {
    loading.value = false
  }
}

function viewAsset() {
  if (traceResult.value?.asset_id) {
    router.push(`/assets/${traceResult.value.asset_id}`)
  }
}

function viewCertificate() {
  if (traceResult.value?.certificate_id) {
    router.push(`/certificate/${traceResult.value.certificate_id}`)
  }
}

function downloadReport() {
  const r = traceResult.value
  if (!r) {
    ElMessage.warning('无溯源结果可下载')
    return
  }
  const reportHtml = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>溯源报告 - ${r.watermark_id || r.asset_code || ''}</title>
<style>
  body { font-family: "Microsoft YaHei", sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; color: #333; }
  h1 { text-align: center; border-bottom: 2px solid #2f6b5a; padding-bottom: 16px; }
  .section { margin: 24px 0; }
  .section h2 { font-size: 16px; border-left: 4px solid #2f6b5a; padding-left: 10px; }
  table { width: 100%; border-collapse: collapse; }
  td { padding: 10px 14px; border: 1px solid #d8e1da; }
  td:first-child { background: #f4f6f2; font-weight: bold; width: 140px; }
  .verified { color: #3f7d5b; font-weight: bold; }
  .failed { color: #a6402f; font-weight: bold; }
  .hash { font-family: monospace; font-size: 12px; word-break: break-all; }
  .footer { text-align: center; color: #5b675f; font-size: 12px; margin-top: 40px; border-top: 1px solid #eee; padding-top: 16px; }
  @media print { body { margin: 0; padding: 20px; } }
</style>
</head>
<body>
<h1>数字资产溯源报告</h1>
<div class="section">
  <h2>溯源状态</h2>
  <p class="${r.verified ? 'verified' : 'failed'}">${r.verified ? '验证通过 — 该资产已在平台注册并获得合法授权' : '验证失败 — 未找到对应资产记录'}</p>
</div>
${r.asset_code ? `<div class="section"><h2>资产信息</h2><table>
  <tr><td>资产编码</td><td>${r.asset_code || '-'}</td></tr>
  <tr><td>标题</td><td>${r.title || '-'}</td></tr>
  <tr><td>水印ID</td><td>${r.watermark_id || '-'}</td></tr>
  <tr><td>创建时间</td><td>${formatDate(r.created_at)}</td></tr>
</table></div>` : ''}
${r.tx_hash ? `<div class="section"><h2>区块链存证</h2><table>
  <tr><td>存证状态</td><td><span class="verified">已存证</span></td></tr>
  <tr><td>证书ID</td><td>${r.certificate_id || '-'}</td></tr>
  <tr><td>交易哈希</td><td class="hash">${r.tx_hash}</td></tr>
  <tr><td>存证时间</td><td>${formatDate(r.confirmed_at)}</td></tr>
</table></div>` : ''}
<div class="footer">
  <p>本报告由苏州园林数字资产平台生成</p>
  <p>报告生成时间：${new Date().toLocaleString('zh-CN')}</p>
</div>
</body>
</html>`
  const blob = new Blob([reportHtml], { type: 'text/html;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `溯源报告_${r.watermark_id || r.asset_code || 'report'}.html`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  ElMessage.success('报告已下载')
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN')
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.trace-page {
  min-height: 100vh;
  padding: 40px 24px 64px;
  background: $bg-secondary;
}

.trace-shell {
  max-width: 880px;
  margin: 0 auto;
}

// 页头
.trace-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding-bottom: 20px;
  margin-bottom: 24px;
  border-bottom: 1px solid $border-color;
}

.trace-heading {
  min-width: 0;
}

.trace-title {
  margin: 0 0 6px;
  font-family: $font-display;
  font-size: 28px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: $text-primary;
}

.trace-subtitle {
  margin: 0;
  font-size: 14px;
  line-height: 1.7;
  color: $text-secondary;
}

.trace-back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  font-size: 13px;
  color: $primary-color;

  &:hover {
    color: $primary-dark;
  }
}

// 查询与结果卡片
.query-card,
.result-card {
  padding: 28px 32px;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
  box-shadow: $shadow-sm;
}

.result-card {
  margin-top: 24px;
}

.query-actions {
  margin-top: 20px;
}

.watermark-input {
  width: 420px;
  max-width: 100%;
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 16px;
  margin-bottom: 20px;
  border-bottom: 1px solid $border-color;
}

.result-title {
  margin: 0;
  font-family: $font-display;
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.03em;
  color: $text-primary;
}

.result-block {
  margin-top: 20px;
}

.result-actions {
  display: flex;
  gap: 12px;
  margin-top: 20px;
}

.mono {
  font-family: $font-mono;
  font-size: 12px;
  word-break: break-all;
}

:deep(.el-upload-dragger) {
  background: $bg-secondary;
  border: 1px dashed $border-color;
  border-radius: $radius-md;
}

:deep(.el-descriptions__title) {
  font-family: $font-display;
  font-size: 15px;
  font-weight: 600;
  color: $text-primary;
}

@media (max-width: 576px) {
  .trace-page {
    padding: 24px 16px 48px;
  }

  .trace-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .query-card,
  .result-card {
    padding: 20px 18px;
  }

  .result-actions {
    flex-direction: column;
  }
}
</style>
