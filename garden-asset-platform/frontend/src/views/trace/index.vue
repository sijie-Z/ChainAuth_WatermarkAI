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
              ref="uploadRef"
              drag
              :auto-upload="false"
              :on-change="handleFileChange"
              :on-exceed="handleExceed"
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
          <div>
            <h2 class="result-title">溯源结果</h2>
            <p v-if="traceResult.verified" class="result-caption">
              {{ activeTab === 'upload'
                ? '已从图片中提取水印并匹配平台登记记录'
                : '水印编号与平台登记记录一致，未校验图片内容' }}
            </p>
          </div>
          <el-tag :type="traceResult.verified ? 'success' : 'danger'">
            {{ traceResult.verified ? '核验通过' : '未匹配' }}
          </el-tag>
        </header>

        <template v-if="traceResult.verified">
          <div class="verify-checks">
            <span class="verify-check ok"><span class="dot"></span>水印编号匹配</span>
            <span class="verify-check" :class="traceResult.certificate_id ? 'ok' : 'pending'">
              <span class="dot"></span>证书{{ traceResult.certificate_id ? '已签发' : '待签发' }}
            </span>
            <span class="verify-check" :class="traceResult.tx_hash ? 'ok' : 'pending'">
              <span class="dot"></span>链上记录{{ traceResult.tx_hash ? '存在' : '未找到' }}
            </span>
            <button
              v-if="traceResult.tx_hash"
              type="button"
              class="hash-copy"
              :title="traceResult.tx_hash"
              @click="copyHash"
            >
              交易哈希 {{ shortHash(traceResult.tx_hash) }}
              <el-icon><CopyDocument /></el-icon>
            </button>
          </div>

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
              <el-tag :type="traceResult.certificate_id ? 'success' : 'info'">
                {{ traceResult.certificate_id ? '已存证' : '未存证' }}
              </el-tag>
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
          <EmptyState :description="traceResult.message || '未找到对应的资产记录，可能为未授权使用'" />
        </template>
      </section>

      <!-- 侵权线索入口 -->
      <section class="report-card">
        <div class="report-copy">
          <h2>发现未授权使用？</h2>
          <p>
            可以提交疑似盗用的图片、网页链接或文字说明。系统会尝试提取水印并匹配平台登记资产，
            管理员核实后会通知权利人与举报人。
          </p>
        </div>
        <el-button type="primary" plain @click="openReportDialog">提交侵权线索</el-button>
      </section>
    </div>

    <el-dialog
      v-model="reportVisible"
      title="提交侵权线索"
      width="min(600px, 94vw)"
      :close-on-click-modal="false"
    >
      <el-alert
        type="info"
        :closable="false"
        show-icon
        class="report-alert"
        title="线索会进入后台研判"
        description="请尽量提供原始文件或来源链接；匿名提交也可以，但留下联系方式便于反馈处理结果。"
      />
      <el-form label-width="90px" class="report-form">
        <el-form-item v-if="traceResult?.asset_id" label="匹配资产">
          <span class="report-asset">
            {{ traceResult.title }} · {{ traceResult.asset_code }}
          </span>
        </el-form-item>
        <el-form-item label="线索文件">
          <div class="report-file-block">
            <el-checkbox v-if="uploadedFile" v-model="reportForm.useTraceFile">
              使用本次溯源的图片（{{ uploadedFile.name }}）
            </el-checkbox>
            <el-upload
              v-if="!uploadedFile || !reportForm.useTraceFile"
              ref="reportUploadRef"
              :auto-upload="false"
              :limit="1"
              :on-change="handleReportFile"
              accept="image/*,.zip"
            >
              <el-button plain>选择图片或 ZIP</el-button>
              <template #tip>
                <span class="report-file-tip">
                  {{ reportFile ? reportFile.name : '不超过 20MB，支持 JPG/PNG/BMP/TIFF/WebP/ZIP' }}
                </span>
              </template>
            </el-upload>
          </div>
        </el-form-item>
        <el-form-item label="来源链接">
          <el-input
            v-model="reportForm.source_url"
            placeholder="https://..."
            maxlength="500"
          />
        </el-form-item>
        <el-form-item label="情况说明">
          <el-input
            v-model="reportForm.description"
            type="textarea"
            :rows="3"
            maxlength="2000"
            show-word-limit
            placeholder="在哪个页面或场景发现、与平台资产的关系等"
          />
        </el-form-item>
        <el-form-item label="联系人">
          <el-input v-model="reportForm.reporter_name" placeholder="称呼（可选）" maxlength="100" />
        </el-form-item>
        <el-form-item label="联系方式">
          <el-input
            v-model="reportForm.contact"
            placeholder="邮箱或电话（可选）"
            maxlength="200"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reportVisible = false">取消</el-button>
        <el-button type="primary" :loading="reportSubmitting" @click="submitReport">
          提交线索
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowRight, CopyDocument, Search, UploadFilled } from '@element-plus/icons-vue'
import { watermarkApi, blockchainApi, infringementApi } from '@/api/modules'
import { copyToClipboard, parseBackendDate } from '@/utils'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const activeTab = ref('upload')
const loading = ref(false)
const watermarkId = ref('')
const uploadedFile = ref(null)
const uploadRef = ref()
const traceResult = ref(null)
const MAX_TRACE_SIZE = 20 * 1024 * 1024
const IMAGE_PATTERN = /\.(jpe?g|png|bmp|tiff?|webp)$/i

const reportVisible = ref(false)
const reportSubmitting = ref(false)
const reportUploadRef = ref()
const reportFile = ref(null)
const reportForm = reactive({
  useTraceFile: true,
  source_url: '',
  description: '',
  reporter_name: '',
  contact: ''
})

function handleFileChange(file) {
  const raw = file.raw
  if (!raw) return
  if (!raw.type.startsWith('image/') && !IMAGE_PATTERN.test(raw.name)) {
    ElMessage.error('溯源仅支持 JPG、PNG、BMP、TIFF、WebP 图片')
    uploadedFile.value = null
    uploadRef.value?.clearFiles()
    return
  }
  if (raw.size > MAX_TRACE_SIZE) {
    ElMessage.error('图片超过 20MB，请压缩后再试')
    uploadedFile.value = null
    uploadRef.value?.clearFiles()
    return
  }
  uploadedFile.value = raw
}

function handleExceed(files) {
  uploadRef.value?.clearFiles()
  const raw = files[0]
  if (!raw) return
  handleFileChange({ raw })
  uploadRef.value?.handleStart(raw)
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
      // verified / message 在响应顶层，资产信息在 data 内
      const payload = response.data
      traceResult.value = {
        ...(payload.data || {}),
        verified: payload.verified === true,
        message: payload.message || ''
      }
    } else {
      ElMessage.error(response.data.message || '溯源查询失败')
    }
  } catch (error) {
    // 未找到资产时后端可能返回 404 且 verified=false，同样展示为溯源失败
    const payload = error.response?.data
    if (payload && payload.verified === false) {
      traceResult.value = {
        ...(payload.data || {}),
        verified: false,
        message: payload.message || '未找到对应的资产记录'
      }
    } else {
      ElMessage.error(payload?.message || '溯源查询失败')
    }
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

function shortHash(value) {
  if (!value) return ''
  return value.length > 24 ? `${value.slice(0, 12)}…${value.slice(-8)}` : value
}

async function copyHash() {
  const ok = await copyToClipboard(traceResult.value?.tx_hash || '')
  ElMessage[ok ? 'success' : 'error'](ok ? '交易哈希已复制' : '复制失败')
}

function openReportDialog() {
  reportForm.useTraceFile = Boolean(uploadedFile.value)
  reportForm.source_url = ''
  reportForm.description = ''
  reportForm.reporter_name = userStore.user?.nickname || userStore.username || ''
  reportForm.contact = userStore.user?.email || ''
  reportFile.value = null
  reportUploadRef.value?.clearFiles()
  reportVisible.value = true
}

function handleReportFile(file) {
  const raw = file.raw
  if (!raw) return
  const allowed = /\.(jpe?g|png|bmp|tiff?|webp|zip)$/i
  if (!allowed.test(raw.name)) {
    ElMessage.error('仅支持图片或 ZIP 文件')
    reportFile.value = null
    reportUploadRef.value?.clearFiles()
    return
  }
  if (raw.size > MAX_TRACE_SIZE) {
    ElMessage.error('线索文件不能超过 20MB')
    reportFile.value = null
    reportUploadRef.value?.clearFiles()
    return
  }
  reportFile.value = raw
}

async function submitReport() {
  if (reportSubmitting.value) return
  const hasTraceFile = reportForm.useTraceFile && uploadedFile.value
  if (!hasTraceFile && !reportFile.value && !reportForm.source_url.trim()
    && !reportForm.description.trim() && !traceResult.value?.asset_id) {
    ElMessage.warning('请至少提供文件、匹配资产、来源链接或情况说明')
    return
  }

  reportSubmitting.value = true
  try {
    const form = new FormData()
    const file = hasTraceFile ? uploadedFile.value : reportFile.value
    if (file) form.append('file', file)
    if (traceResult.value?.asset_id) form.append('asset_id', traceResult.value.asset_id)
    if (traceResult.value?.watermark_id) {
      form.append('watermark_id', traceResult.value.watermark_id)
    }
    form.append('source_url', reportForm.source_url.trim())
    form.append('description', reportForm.description.trim())
    form.append('reporter_name', reportForm.reporter_name.trim())
    form.append('contact', reportForm.contact.trim())

    const response = await infringementApi.report(form)
    if (response.data?.code === 200) {
      const data = response.data.data || {}
      ElMessage.success(`线索已提交：${data.report_code}`)
      reportVisible.value = false
    } else {
      ElMessage.error(response.data?.message || '线索提交失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '线索提交失败')
  } finally {
    reportSubmitting.value = false
  }
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
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
<title>溯源报告 - ${escapeHtml(r.watermark_id || r.asset_code || '')}</title>
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
  <tr><td>资产编码</td><td>${escapeHtml(r.asset_code) || '-'}</td></tr>
  <tr><td>标题</td><td>${escapeHtml(r.title) || '-'}</td></tr>
  <tr><td>水印ID</td><td>${escapeHtml(r.watermark_id) || '-'}</td></tr>
  <tr><td>创建时间</td><td>${escapeHtml(formatDate(r.created_at))}</td></tr>
</table></div>` : ''}
${r.tx_hash ? `<div class="section"><h2>区块链存证</h2><table>
  <tr><td>存证状态</td><td><span class="verified">已存证</span></td></tr>
  <tr><td>证书ID</td><td>${escapeHtml(r.certificate_id) || '-'}</td></tr>
  <tr><td>交易哈希</td><td class="hash">${escapeHtml(r.tx_hash)}</td></tr>
  <tr><td>存证时间</td><td>${escapeHtml(formatDate(r.confirmed_at))}</td></tr>
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
  const date = parseBackendDate(dateStr)
  return date ? date.toLocaleDateString('zh-CN') : ''
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

.result-caption {
  margin: 4px 0 0;
  font-size: 12px;
  color: $text-placeholder;
}

.verify-checks {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 18px;
}

.verify-check {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: $radius-full;
  background: $bg-secondary;
  font-size: 12px;
  color: $text-secondary;

  .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: $text-placeholder;
  }

  &.ok {
    background: $success-bg;
    color: $success-color;

    .dot { background: $success-color; }
  }

  &.pending {
    background: $warning-bg;
    color: $warning-color;

    .dot { background: $warning-color; }
  }
}

.hash-copy {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border: 1px dashed $border-color;
  border-radius: $radius-full;
  background: $bg-card;
  font-family: $font-mono;
  font-size: 11px;
  color: $text-secondary;
  cursor: pointer;

  &:hover {
    border-color: $primary-color;
    color: $primary-color;
  }
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

.report-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  margin-top: 20px;
  padding: 22px 24px;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
}

.report-copy {
  h2 {
    margin: 0 0 6px;
    font-family: $font-display;
    font-size: 17px;
    color: $text-primary;
  }

  p {
    margin: 0;
    font-size: 13px;
    line-height: 1.7;
    color: $text-secondary;
  }
}

.report-alert {
  margin-bottom: 16px;
}

.report-asset {
  font-family: $font-mono;
  font-size: 12px;
  color: $text-secondary;
}

.report-file-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.report-file-tip {
  font-size: 12px;
  color: $text-placeholder;
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

  .report-card {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
