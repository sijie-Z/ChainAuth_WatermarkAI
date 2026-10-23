<template>
  <div class="verify-page">
    <div class="verify-shell">
      <header class="verify-hero">
        <p class="verify-kicker">EVIDENCE PACKAGE VERIFICATION</p>
        <h1 class="verify-title">证据包核验</h1>
        <p class="verify-subtitle">
          上传平台导出的 ZIP 证据包，核验文件完整性、SHA-256 校验清单，以及包内资产、水印、证书与当前版本是否仍与平台台账一致。
          核验不需要登录，也不会把文件写入资产库。
        </p>
        <ul class="verify-facts" aria-label="核验说明">
          <li><span>01</span>ZIP 结构与体积限制</li>
          <li><span>02</span>SHA-256 完整性</li>
          <li><span>03</span>平台登记一致性</li>
        </ul>
      </header>

      <section class="verify-card upload-card" aria-labelledby="upload-title">
        <div class="card-heading">
          <div>
            <h2 id="upload-title">上传证据包</h2>
            <p>只接受平台导出的 ZIP 证据包；单个文件不超过 20MB。</p>
          </div>
          <span class="card-meta">ZIP · ≤ 20MB</span>
        </div>

        <div class="upload-grid">
          <el-upload
            ref="uploadRef"
            class="verify-upload"
            drag
            :auto-upload="false"
            :limit="1"
            :on-change="handleFileChange"
            :on-remove="resetSelection"
            :on-exceed="handleExceed"
            accept=".zip,application/zip"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              将证据包拖到此处，或 <em>点击选择</em>
            </div>
            <template #tip>
              <span class="upload-tip">文件只在本次核验期间使用，完成后立即清理</span>
            </template>
          </el-upload>

          <div v-if="file" class="file-summary">
            <el-icon class="file-icon"><Document /></el-icon>
            <div>
              <strong :title="file.name">{{ file.name }}</strong>
              <span>{{ fileSizeText }}</span>
            </div>
          </div>
        </div>

        <div class="run-row">
          <el-button
            type="primary"
            size="large"
            :loading="running"
            :disabled="!file || running"
            @click="runVerify"
          >
            <el-icon v-if="!running"><Search /></el-icon>
            {{ running ? '正在核验…' : '开始核验' }}
          </el-button>
          <p class="run-hint">
            {{ running ? '正在读取 ZIP、校验哈希并比对平台记录…' : '核验结果会区分“完整性”和“平台登记一致性”，不会合并成一个模糊结论。' }}
          </p>
        </div>
      </section>

      <template v-if="result">
        <section class="result-banner" :class="summaryTone" aria-live="polite">
          <el-icon class="summary-icon">
            <CircleCheck v-if="result.verified" />
            <CircleClose v-else-if="!result.integrity_ok" />
            <WarningFilled v-else />
          </el-icon>
          <div class="summary-copy">
            <h2>{{ result.label }}</h2>
            <p>{{ verdictText }}</p>
          </div>
          <div class="summary-flags">
            <span :class="result.integrity_ok ? 'ok' : 'bad'">
              {{ result.integrity_ok ? '完整性通过' : '完整性失败' }}
            </span>
            <span :class="result.registry_ok ? 'ok' : 'bad'">
              {{ result.registry_ok ? '登记一致' : '登记不一致' }}
            </span>
          </div>
        </section>

        <div class="result-grid">
          <section class="verify-card checks-card" aria-labelledby="checks-title">
            <div class="card-heading">
              <div>
                <h2 id="checks-title">核验项</h2>
                <p>每项独立给出结论；失败项会说明具体文件或字段。</p>
              </div>
            </div>
            <ul class="check-list">
              <li
                v-for="check in result.checks"
                :key="check.key"
                class="check-row"
                :class="check.status"
              >
                <el-icon class="check-icon">
                  <CircleCheck v-if="check.status === 'pass'" />
                  <WarningFilled v-else-if="check.status === 'warn'" />
                  <CircleClose v-else />
                </el-icon>
                <div class="check-copy">
                  <strong>{{ check.label }}</strong>
                  <span>{{ check.detail }}</span>
                </div>
                <el-tag :type="tagType(check.status)" effect="plain" size="small">
                  {{ statusText(check.status) }}
                </el-tag>
              </li>
            </ul>
          </section>

          <aside class="verify-card info-card">
            <div class="info-block">
              <h3>证据包信息</h3>
              <dl>
                <div><dt>资产编码</dt><dd>{{ result.package.asset_code || '-' }}</dd></div>
                <div><dt>资产标题</dt><dd>{{ result.package.asset_title || '-' }}</dd></div>
                <div><dt>生成时间</dt><dd>{{ formatDate(result.package.generated_at) }}</dd></div>
                <div><dt>生成人</dt><dd>{{ result.package.generated_by || '-' }}</dd></div>
              </dl>
            </div>

            <div class="info-block">
              <h3>平台登记</h3>
              <dl v-if="result.registry.asset_found">
                <div><dt>资产状态</dt><dd>{{ assetStatusText(result.registry.status) }}</dd></div>
                <div><dt>水印编号</dt><dd>{{ result.registry.watermark_id || '无' }}</dd></div>
                <div><dt>证书编号</dt><dd>{{ result.registry.certificate_id || '无' }}</dd></div>
              </dl>
              <p v-else class="not-found">平台未找到该资产编码，无法完成登记比对。</p>
            </div>

            <div class="info-block warning-block">
              <h3>注意事项</h3>
              <ul>
                <li v-for="(warning, index) in result.warnings" :key="index">{{ warning }}</li>
              </ul>
            </div>
          </aside>
        </div>
      </template>

      <section v-else class="verify-card explain-card" aria-labelledby="explain-title">
        <div class="card-heading">
          <div>
            <h2 id="explain-title">核验范围</h2>
            <p>证据包核验不等于司法鉴定，也不会伪装成“链上已验证”。</p>
          </div>
        </div>
        <dl class="explain-list">
          <div>
            <dt>会检查</dt>
            <dd>ZIP 路径与体积、SHA256SUMS、包内文件哈希、资产编码、水印编号、证书与当前/历史版本哈希。</dd>
          </div>
          <div>
            <dt>不会检查</dt>
            <dd>不会验证平台私钥签名，也不会查询真实区块链；本地模拟存证会在注意事项中明确标注。</dd>
          </div>
          <div>
            <dt>失败时</dt>
            <dd>会区分“包损坏/被改写”与“包完整但与平台记录不一致”，不会用一句“核验失败”掩盖差异。</dd>
          </div>
          <div>
            <dt>隐私</dt>
            <dd>公开核验只返回资产状态、水印/证书编号与版本匹配结果，不返回上传者、授权台账等内部信息。</dd>
          </div>
        </dl>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  CircleCheck,
  CircleClose,
  Document,
  Search,
  UploadFilled,
  WarningFilled
} from '@element-plus/icons-vue'
import { publicApi } from '@/api/modules'
import { parseBackendDate } from '@/utils'

const MAX_BYTES = 20 * 1024 * 1024

const uploadRef = ref(null)
const file = ref(null)
const running = ref(false)
const result = ref(null)

const fileSizeText = computed(() => {
  if (!file.value) return ''
  const kb = file.value.size / 1024
  return kb >= 1024 ? `${(kb / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(kb))} KB`
})

const verdictText = computed(() => {
  const data = result.value
  if (!data) return ''
  if (data.verified) {
    return '包内文件未发现缺失或被改写，资产编码、水印、证书与版本哈希均与平台记录一致。'
  }
  if (!data.integrity_ok) {
    return 'ZIP 内文件或 SHA-256 校验清单不一致，证据包可能已损坏或被修改，不能作为完整证据使用。'
  }
  return '包内文件完整，但与平台资产、水印、证书或版本记录存在差异；请查看失败项和注意事项。'
})

const summaryTone = computed(() => {
  const data = result.value
  if (!data) return ''
  if (data.verified) return 'success'
  return data.integrity_ok ? 'warning' : 'danger'
})

function handleFileChange(uploadFile) {
  const raw = uploadFile.raw
  if (!raw) return
  if (!/\.zip$/i.test(raw.name || '')) {
    ElMessage.error('请选择 ZIP 证据包')
    uploadRef.value?.clearFiles?.()
    return
  }
  if (raw.size > MAX_BYTES) {
    ElMessage.error('证据包不能超过 20MB')
    uploadRef.value?.clearFiles?.()
    return
  }
  file.value = raw
  result.value = null
}

function resetSelection() {
  file.value = null
  result.value = null
}

function handleExceed() {
  ElMessage.info('一次只核验一个证据包，请先移除当前文件')
}

async function runVerify() {
  if (!file.value || running.value) return
  running.value = true
  result.value = null
  const formData = new FormData()
  formData.append('file', file.value)
  try {
    const response = await publicApi.verifyEvidencePackage(formData)
    if (response.data?.code === 200) {
      result.value = response.data.data
      ElMessage.success('证据包核验完成')
    } else {
      ElMessage.error(response.data?.message || '核验未完成')
    }
  } catch {
    // 全局拦截器已显示可读错误
  } finally {
    running.value = false
  }
}

function statusText(status) {
  if (status === 'pass') return '通过'
  if (status === 'warn') return '注意'
  return '失败'
}

function tagType(status) {
  if (status === 'pass') return 'success'
  if (status === 'warn') return 'warning'
  return 'danger'
}

function assetStatusText(status) {
  const map = { published: '已发布', draft: '草稿', pending: '待审核', rejected: '已驳回', deleted: '已删除' }
  return map[status] || status || '-'
}

function formatDate(value) {
  const date = parseBackendDate(value)
  return date ? date.toLocaleString('zh-CN') : (value || '-')
}

onBeforeUnmount(() => {
  file.value = null
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.verify-page {
  min-height: 100vh;
  padding: 36px 24px 72px;
  background: $bg-secondary;
}

.verify-shell {
  max-width: 1120px;
  margin: 0 auto;
}

.verify-hero {
  position: relative;
  margin-bottom: 24px;
  padding: 8px 4px 24px;
  border-bottom: 1px solid $border-color;

  &::after {
    content: '';
    position: absolute;
    right: 8px;
    bottom: -1px;
    width: 96px;
    height: 2px;
    background: $accent-color;
  }
}

.verify-kicker {
  margin: 0 0 12px;
  font-family: $font-mono;
  font-size: 11px;
  letter-spacing: 0.22em;
  color: $text-placeholder;
}

.verify-title {
  margin: 0 0 12px;
  font-family: $font-display;
  font-size: 34px;
  font-weight: 600;
  letter-spacing: 0.06em;
  color: $text-primary;
}

.verify-subtitle {
  max-width: 780px;
  margin: 0;
  font-size: 14px;
  line-height: 1.9;
  color: $text-secondary;
}

.verify-facts {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 28px;
  margin: 20px 0 0;
  padding: 0;
  list-style: none;

  li {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: $text-secondary;
  }

  span {
    font-family: $font-mono;
    font-size: 10px;
    color: $accent-color;
  }
}

.verify-card {
  padding: 26px 28px;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
  box-shadow: $shadow-sm;
}

.upload-card {
  margin-bottom: 22px;
}

.card-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 18px;

  h2 {
    margin: 0 0 6px;
    font-family: $font-display;
    font-size: 19px;
    font-weight: 600;
    color: $text-primary;
  }

  p {
    margin: 0;
    font-size: 13px;
    line-height: 1.7;
    color: $text-secondary;
  }
}

.card-meta {
  flex-shrink: 0;
  padding-top: 4px;
  font-family: $font-mono;
  font-size: 11px;
  color: $text-placeholder;
}

.upload-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(220px, 0.75fr);
  gap: 18px;
}

.verify-upload {
  :deep(.el-upload) {
    width: 100%;
  }

  :deep(.el-upload-dragger) {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 178px;
    padding: 26px 20px;
    background: $bg-secondary;
    border: 1px dashed $border-dark;
    border-radius: $radius-md;

    &:hover {
      border-color: $primary-color;
    }
  }

  :deep(.el-icon--upload) {
    margin-bottom: 10px;
    font-size: 36px;
    color: $primary-color;
  }

  :deep(.el-upload__text) {
    font-size: 14px;
    color: $text-secondary;

    em {
      color: $primary-dark;
      font-style: normal;
      font-weight: 600;
    }
  }
}

.upload-tip {
  display: block;
  font-size: 11px;
  color: $text-placeholder;
}

.file-summary {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  padding: 16px;
  background: $bg-secondary;
  border: 1px solid $border-color;
  border-radius: $radius-md;

  .file-icon {
    flex-shrink: 0;
    font-size: 30px;
    color: $primary-color;
  }

  div {
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 0;
  }

  strong {
    overflow: hidden;
    font-size: 12px;
    color: $text-primary;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  span {
    font-family: $font-mono;
    font-size: 10px;
    color: $text-placeholder;
  }
}

.run-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px 18px;
  margin-top: 20px;
  padding-top: 18px;
  border-top: 1px solid $border-light;
}

.run-hint {
  margin: 0;
  font-size: 12px;
  color: $text-placeholder;
}

.result-banner {
  display: flex;
  align-items: center;
  gap: 18px;
  margin-bottom: 20px;
  padding: 20px 24px;
  border-radius: $radius-lg;
  border: 1px solid $border-color;
  background: $bg-card;

  &.success {
    background: $bg-secondary;
    border-color: $primary-color;
  }

  &.warning {
    border-color: $accent-color;
  }

  &.danger {
    border-color: $accent-color;
    background: #fdf6f3;
  }

  .summary-icon {
    flex-shrink: 0;
    font-size: 38px;
  }

  &.success .summary-icon { color: $primary-color; }
  &.warning .summary-icon { color: $accent-color; }
  &.danger .summary-icon { color: $accent-color; }
}

.summary-copy {
  min-width: 0;

  h2 {
    margin: 0 0 4px;
    font-family: $font-display;
    font-size: 20px;
    font-weight: 600;
    color: $text-primary;
  }

  p {
    margin: 0;
    font-size: 13px;
    line-height: 1.7;
    color: $text-secondary;
  }
}

.summary-flags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-left: auto;

  span {
    padding: 5px 10px;
    border: 1px solid $border-color;
    border-radius: $radius-full;
    font-size: 11px;
    background: $bg-card;

    &.ok { color: $primary-dark; border-color: $primary-color; }
    &.bad { color: $accent-color; border-color: $accent-color; }
  }
}

.result-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(280px, 0.75fr);
  gap: 20px;
  align-items: start;
}

.check-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.check-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 13px 0;
  border-top: 1px solid $border-light;

  &:first-child {
    border-top: none;
    padding-top: 2px;
  }

  .check-icon {
    flex-shrink: 0;
    margin-top: 1px;
    font-size: 17px;
  }

  &.pass .check-icon { color: $primary-color; }
  &.warn .check-icon { color: $accent-color; }
  &.fail .check-icon { color: $accent-color; }

  .el-tag {
    flex-shrink: 0;
    margin-left: auto;
  }
}

.check-copy {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;

  strong {
    font-size: 13px;
    color: $text-primary;
  }

  span {
    font-size: 11px;
    line-height: 1.6;
    color: $text-placeholder;
    word-break: break-word;
  }
}

.info-card {
  position: sticky;
  top: 84px;
}

.info-block {
  padding-top: 14px;
  margin-top: 14px;
  border-top: 1px solid $border-light;

  &:first-child {
    padding-top: 0;
    margin-top: 0;
    border-top: none;
  }

  h3 {
    margin: 0 0 10px;
    font-family: $font-display;
    font-size: 15px;
    font-weight: 600;
    color: $text-primary;
  }

  dl {
    margin: 0;
  }

  dl div {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    padding: 5px 0;
    font-size: 12px;
  }

  dt {
    color: $text-placeholder;
    white-space: nowrap;
  }

  dd {
    margin: 0;
    font-family: $font-mono;
    font-size: 11px;
    color: $text-secondary;
    text-align: right;
    word-break: break-all;
  }

  ul {
    margin: 0;
    padding-left: 18px;
  }

  li {
    margin-bottom: 6px;
    font-size: 11px;
    line-height: 1.7;
    color: $text-secondary;
  }
}

.not-found {
  margin: 0;
  font-size: 12px;
  color: $accent-color;
}

.warning-block {
  background: $bg-secondary;
  border-radius: $radius-sm;
  padding: 14px;
  border-top: none;
}

.explain-card {
  margin-top: 22px;
}

.explain-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px 32px;
  margin: 0;

  div {
    padding-top: 14px;
    border-top: 1px solid $border-light;
  }

  dt {
    margin-bottom: 5px;
    font-family: $font-mono;
    font-size: 12px;
    color: $primary-dark;
  }

  dd {
    margin: 0;
    font-size: 13px;
    line-height: 1.8;
    color: $text-secondary;
  }
}

@media (max-width: 900px) {
  .result-grid {
    grid-template-columns: 1fr;
  }

  .info-card {
    position: static;
  }

  .summary-flags {
    margin-left: 0;
  }
}

@media (max-width: 720px) {
  .verify-page {
    padding: 24px 16px 56px;
  }

  .verify-title {
    font-size: 28px;
  }

  .verify-card {
    padding: 20px 18px;
  }

  .upload-grid {
    grid-template-columns: 1fr;
  }

  .card-heading {
    flex-direction: column;
    gap: 6px;
  }

  .card-meta {
    padding-top: 0;
  }

  .result-banner {
    flex-wrap: wrap;
    align-items: flex-start;
  }

  .summary-copy {
    flex: 1;
  }

  .check-row {
    flex-wrap: wrap;
  }

  .check-row .el-tag {
    margin-left: 27px;
  }

  .explain-list {
    grid-template-columns: 1fr;
  }
}
</style>
