<template>
  <div class="lab-page">
    <div class="lab-shell">
      <header class="lab-hero">
        <p class="lab-kicker">WATERMARK ROBUSTNESS LAB</p>
        <h1 class="lab-title">水印鲁棒性实验室</h1>
        <p class="lab-subtitle">
          上传一张图片，平台会真实执行 DCT + QIM 盲水印嵌入，再分别施加压缩、噪声与缩放攻击，
          逐项提取并给出 PSNR、NC 与水印 ID 恢复结果。所有指标来自本次计算，不使用预置数据。
        </p>
        <ul class="lab-facts" aria-label="实验说明">
          <li><span class="fact-index">01</span>真实算法嵌入与提取</li>
          <li><span class="fact-index">02</span>8 项可复现攻击</li>
          <li><span class="fact-index">03</span>结果不写入资产库</li>
        </ul>
      </header>

      <section class="lab-card upload-card" aria-labelledby="sample-title">
        <div class="card-heading">
          <div>
            <h2 id="sample-title">样本图片</h2>
            <p>建议使用包含建筑细节与平滑天空的实景照片，最长边会自动缩放到 {{ maxSide }}px。</p>
          </div>
          <span class="card-meta">PNG / JPG / WebP · ≤ 10MB</span>
        </div>

        <div class="upload-grid">
          <el-upload
            ref="uploadRef"
            class="lab-upload"
            drag
            :auto-upload="false"
            :limit="1"
            :on-change="handleFileChange"
            :on-remove="handleRemove"
            :on-exceed="handleExceed"
            accept="image/png,image/jpeg,image/webp,image/bmp,image/tiff"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">将图片拖到此处，或 <em>点击选择</em></div>
            <template #tip>
              <span class="upload-tip">一次只分析一张图片；实验通常在数秒内完成</span>
            </template>
          </el-upload>

          <figure v-if="previewUrl" class="sample-preview">
            <img :src="previewUrl" :alt="fileName || '待分析图片预览'" />
            <figcaption>
              <strong>{{ fileName }}</strong>
              <span>{{ fileSizeText }}</span>
            </figcaption>
          </figure>
        </div>

        <div class="run-row">
          <el-button
            type="primary"
            size="large"
            :loading="running"
            :disabled="!file || running"
            @click="runBenchmark"
          >
            <el-icon v-if="!running"><Cpu /></el-icon>
            {{ running ? '正在执行真实计算…' : '开始鲁棒性实验' }}
          </el-button>
          <p v-if="running" class="run-hint" role="status">
            已运行 {{ elapsed }} 秒：正在逐项施加攻击并提取水印，请勿关闭页面。
          </p>
          <p v-else class="run-hint">嵌入强度 α = 32，水印图与 ID 使用同一频域量化流程。</p>
        </div>
      </section>

      <template v-if="result">
        <div class="result-bar">
          <p>
            <strong>实验结果</strong>
            <span>以下指标来自本次真实计算 · {{ result.summary.total }} 项攻击</span>
          </p>
          <el-button plain size="small" @click="downloadReport">
            <el-icon><Download /></el-icon>
            下载实验报告
          </el-button>
        </div>

        <section class="summary-strip" aria-live="polite" aria-label="实验结果摘要">
          <article class="summary-card id-card">
            <span class="summary-label">本次嵌入的水印 ID</span>
            <strong class="summary-id" :title="result.watermark_id">{{ result.watermark_id }}</strong>
            <span class="summary-note"
              >重复 {{ result.watermark.id_repeat }} 份 · {{ result.watermark.side }}×{{
                result.watermark.side
              }}
              水印图</span
            >
          </article>
          <article class="summary-card">
            <span class="summary-label">PSNR</span>
            <strong class="summary-value">{{ result.psnr }}<small>dB</small></strong>
            <span class="summary-note">嵌入前后峰值信噪比</span>
          </article>
          <article class="summary-card">
            <span class="summary-label">ID 恢复率</span>
            <strong class="summary-value"
              >{{ result.summary.recovered }}<small>/ {{ result.summary.total }}</small></strong
            >
            <span class="summary-note">{{ result.summary.verdict }}</span>
          </article>
          <article class="summary-card">
            <span class="summary-label">本次总耗时</span>
            <strong class="summary-value"
              >{{ (result.total_ms / 1000).toFixed(1) }}<small>s</small></strong
            >
            <span class="summary-note"
              >嵌入 {{ result.embed_ms }}ms · 工作尺寸 {{ result.source.working_width }}×{{
                result.source.working_height
              }}</span
            >
          </article>
        </section>

        <div class="result-grid">
          <section class="lab-card attacks-card" aria-labelledby="attacks-title">
            <div class="card-heading">
              <div>
                <h2 id="attacks-title">攻击测试</h2>
                <p>NC 越接近 1 表示提取出的水印图与原始水印越相似；ID 恢复要求逐字符完全一致。</p>
              </div>
              <span class="card-meta"
                >{{ result.summary.recovered }} / {{ result.summary.total }} 恢复</span
              >
            </div>

            <ul class="attack-list">
              <li
                v-for="attack in result.attacks"
                :key="attack.key"
                class="attack-row"
                :class="{ recovered: attack.id_recovered, failed: !attack.id_recovered }"
              >
                <div class="attack-main">
                  <span class="attack-status" aria-hidden="true">
                    <el-icon v-if="attack.id_recovered"><CircleCheck /></el-icon>
                    <el-icon v-else><WarningFilled /></el-icon>
                  </span>
                  <div class="attack-copy">
                    <strong>{{ attack.label }}</strong>
                    <span>{{ attack.description }}</span>
                  </div>
                  <el-tag
                    :type="attack.id_recovered ? 'success' : 'danger'"
                    effect="plain"
                    size="small"
                  >
                    {{ attack.id_recovered ? 'ID 已恢复' : 'ID 未恢复' }}
                  </el-tag>
                </div>
                <div class="attack-metrics">
                  <span class="nc-label">NC</span>
                  <span class="nc-track" role="img" :aria-label="`NC ${attack.nc.toFixed(4)}`">
                    <span
                      class="nc-fill"
                      :class="ncTone(attack.nc)"
                      :style="{ width: ncWidth(attack.nc) }"
                    ></span>
                  </span>
                  <span class="nc-value">{{ attack.nc.toFixed(4) }}</span>
                  <span class="attack-time">{{ attack.extract_ms }} ms</span>
                  <span v-if="attack.error" class="attack-error">{{ attack.error }}</span>
                </div>
              </li>
            </ul>
          </section>

          <aside class="lab-card preview-card" aria-labelledby="preview-title">
            <div class="card-heading">
              <div>
                <h2 id="preview-title">提取出的水印</h2>
                <p>每张缩略图都是对应攻击后真实提取的结果。</p>
              </div>
            </div>

            <figure class="wm-original">
              <img :src="result.watermark_preview" alt="平台原始水印图" />
              <figcaption>原始水印</figcaption>
            </figure>

            <div class="wm-grid">
              <figure v-for="attack in recoveredPreviews" :key="attack.key">
                <img :src="attack.watermark_preview" :alt="`${attack.label} 后提取的水印`" />
                <figcaption>{{ attack.label }}</figcaption>
              </figure>
            </div>

            <p v-if="recoveredPreviews.length === 0" class="wm-empty">
              本次没有攻击通过 ID 校验，可换一张纹理更丰富的图片再试。
            </p>

            <div class="boundary-note">
              <strong>算法边界</strong>
              <p>
                裁剪会破坏嵌入区域，不在本实验的攻击列表中；实际溯源需结合存证记录与人工核验。
                实验只处理上传图片的临时副本，完成后立即清理。
              </p>
            </div>
          </aside>
        </div>

        <p class="lab-disclaimer">{{ result.disclaimer }}</p>
      </template>

      <section v-else class="lab-card explain-card" aria-labelledby="explain-title">
        <div class="card-heading">
          <div>
            <h2 id="explain-title">指标怎么看</h2>
            <p>实验室不给出“通过 / 不通过”的营销结论，只展示本次图片的真实计算结果。</p>
          </div>
        </div>
        <dl class="explain-list">
          <div>
            <dt>PSNR</dt>
            <dd>嵌入前后图像的峰值信噪比，一般高于 30dB 时肉眼难以察觉差异。</dd>
          </div>
          <div>
            <dt>NC</dt>
            <dd>归一化相关度，衡量提取出的水印图与原始水印的相似程度，越接近 1 越好。</dd>
          </div>
          <div>
            <dt>ID 恢复</dt>
            <dd>对提取比特做多数表决后，水印 ID 必须与嵌入值逐字符一致才算恢复成功。</dd>
          </div>
          <div>
            <dt>边界</dt>
            <dd>JPEG 50 与组合攻击对图像内容敏感，失败时会如实标记，不替换样本或重试到成功。</dd>
          </div>
        </dl>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { CircleCheck, Cpu, Download, UploadFilled, WarningFilled } from '@element-plus/icons-vue'
import { watermarkApi } from '@/api/modules'

const MAX_BYTES = 10 * 1024 * 1024
const maxSide = 640

const uploadRef = ref(null)
const file = ref(null)
const previewUrl = ref('')
const running = ref(false)
const elapsed = ref(0)
const result = ref(null)
let timer = null

const fileName = computed(() => file.value?.name || '')
const fileSizeText = computed(() => {
  if (!file.value) return ''
  const kb = file.value.size / 1024
  return kb >= 1024 ? `${(kb / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(kb))} KB`
})
const recoveredPreviews = computed(() =>
  (result.value?.attacks.filter(item => item.id_recovered && item.watermark_preview) || []).slice(
    0,
    6
  )
)

function stopTimer() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

function revokePreview() {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = ''
  }
}

function resetSelection() {
  revokePreview()
  file.value = null
  result.value = null
  elapsed.value = 0
  stopTimer()
}

function handleFileChange(uploadFile) {
  const raw = uploadFile.raw
  if (!raw) return
  const isImage =
    raw.type.startsWith('image/') || /\.(png|jpe?g|webp|bmp|tiff?)$/i.test(raw.name || '')
  if (!isImage) {
    ElMessage.error('请选择图片文件')
    uploadRef.value?.clearFiles?.()
    return
  }
  if (raw.size > MAX_BYTES) {
    ElMessage.error('图片不能超过 10MB')
    uploadRef.value?.clearFiles?.()
    return
  }
  revokePreview()
  file.value = raw
  previewUrl.value = URL.createObjectURL(raw)
  result.value = null
}

function handleRemove() {
  resetSelection()
}

function handleExceed() {
  ElMessage.info('一次只分析一张图片，请先移除当前图片')
}

function ncWidth(nc) {
  return `${Math.max(2, Math.min(100, Math.round(nc * 100)))}%`
}

function ncTone(nc) {
  if (nc >= 0.9) return 'good'
  if (nc >= 0.6) return 'fair'
  return 'poor'
}

async function runBenchmark() {
  if (!file.value || running.value) return

  running.value = true
  result.value = null
  elapsed.value = 0
  timer = setInterval(() => {
    elapsed.value += 1
  }, 1000)

  const formData = new FormData()
  formData.append('file', file.value)

  try {
    const response = await watermarkApi.benchmark(formData)
    if (response.data?.code === 200) {
      result.value = response.data.data
      ElMessage.success('鲁棒性实验完成')
      await nextTick()
      document.querySelector('.result-bar')?.scrollIntoView({
        block: 'start',
        behavior: 'smooth'
      })
    } else {
      ElMessage.error(response.data?.message || '实验未完成')
    }
  } catch {
    // 全局拦截器已给出可读错误，这里保留当前样本便于重试
  } finally {
    running.value = false
    stopTimer()
  }
}

function downloadReport() {
  const data = result.value
  if (!data) return

  const lines = [
    '# 水印鲁棒性实验报告',
    '',
    `- 生成时间：${new Date().toLocaleString('zh-CN')}`,
    `- 样本文件：${fileName.value || '未命名'}`,
    `- 工作尺寸：${data.source.working_width}×${data.source.working_height}` +
      `（原图 ${data.source.original_width}×${data.source.original_height}` +
      `${data.source.downscaled ? '，已缩放' : ''}）`,
    `- 水印 ID：${data.watermark_id}`,
    `- 算法：${data.method}，α = ${data.alpha}，ID 重复 ${data.watermark.id_repeat} 份`,
    `- 嵌入 PSNR：${data.psnr} dB`,
    `- ID 恢复：${data.summary.recovered}/${data.summary.total}（${data.summary.verdict}）`,
    `- 总耗时：${(data.total_ms / 1000).toFixed(1)} 秒`,
    '',
    '| 攻击 | NC | ID 恢复 | 提取耗时 |',
    '| --- | --- | --- | --- |',
    ...data.attacks.map(
      attack =>
        `| ${attack.label} | ${attack.nc.toFixed(4)} | ${attack.id_recovered ? '是' : '否'} | ` +
        `${attack.extract_ms} ms |`
    ),
    '',
    `> ${data.disclaimer}`,
    '> 本报告由平台根据本次真实计算生成，未使用预置数据。'
  ]

  const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `watermark-lab-${data.watermark_id}.md`
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

onBeforeUnmount(() => {
  revokePreview()
  stopTimer()
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.lab-page {
  min-height: 100vh;
  padding: 36px 24px 72px;
  background: $bg-secondary;
}

.lab-shell {
  max-width: 1180px;
  margin: 0 auto;
}

.lab-hero {
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

.lab-kicker {
  margin: 0 0 12px;
  font-family: $font-mono;
  font-size: 11px;
  letter-spacing: 0.24em;
  color: $text-placeholder;
}

.lab-title {
  margin: 0 0 12px;
  font-family: $font-display;
  font-size: 36px;
  font-weight: 600;
  letter-spacing: 0.06em;
  color: $text-primary;
}

.lab-subtitle {
  max-width: 760px;
  margin: 0;
  font-size: 14px;
  line-height: 1.9;
  color: $text-secondary;
}

.lab-facts {
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

  .fact-index {
    font-family: $font-mono;
    font-size: 10px;
    color: $accent-color;
  }
}

.lab-card {
  padding: 26px 28px;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
  box-shadow: $shadow-sm;
}

.card-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 20px;

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

.upload-card {
  margin-bottom: 22px;
}

.upload-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(220px, 0.65fr);
  gap: 20px;
  align-items: stretch;
}

.lab-upload {
  :deep(.el-upload) {
    width: 100%;
  }

  :deep(.el-upload-dragger) {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 212px;
    padding: 28px 20px;
    background: $bg-secondary;
    border: 1px dashed $border-dark;
    border-radius: $radius-md;

    &:hover {
      border-color: $primary-color;
    }
  }

  :deep(.el-icon--upload) {
    margin-bottom: 12px;
    font-size: 38px;
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

  :deep(.el-upload__tip) {
    margin-top: 8px;
  }
}

.upload-tip {
  display: block;
  font-size: 11px;
  color: $text-placeholder;
}

.sample-preview {
  display: flex;
  flex-direction: column;
  margin: 0;
  overflow: hidden;
  background: $bg-secondary;
  border: 1px solid $border-color;
  border-radius: $radius-md;

  img {
    width: 100%;
    height: 168px;
    object-fit: cover;
  }

  figcaption {
    display: flex;
    flex-direction: column;
    gap: 3px;
    padding: 10px 12px;
    min-width: 0;

    strong {
      overflow: hidden;
      font-size: 12px;
      font-weight: 500;
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
}

.run-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px 18px;
  margin-top: 22px;
  padding-top: 20px;
  border-top: 1px solid $border-light;
}

.run-hint {
  margin: 0;
  font-size: 12px;
  color: $text-placeholder;
}

.result-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin: 0 2px 12px;
  scroll-margin-top: 78px;

  p {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 6px 12px;
    margin: 0;
  }

  strong {
    font-family: $font-display;
    font-size: 18px;
    font-weight: 600;
    color: $text-primary;
  }

  span {
    font-size: 11px;
    color: $text-placeholder;
  }
}

.summary-strip {
  display: grid;
  grid-template-columns: 1.5fr repeat(3, 1fr);
  gap: 14px;
  margin-bottom: 22px;
  scroll-margin-top: 78px;
}

.summary-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
  padding: 18px 20px;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-md;

  &.id-card {
    background: $primary-dark;
    border-color: $primary-dark;

    .summary-label,
    .summary-note {
      color: rgba(252, 253, 251, 0.66);
    }

    .summary-id {
      color: #fcfdfb;
    }
  }
}

.summary-label {
  font-size: 11px;
  letter-spacing: 0.08em;
  color: $text-placeholder;
}

.summary-id {
  overflow: hidden;
  font-family: $font-mono;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.01em;
  color: $text-primary;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.summary-value {
  font-family: $font-display;
  font-size: 30px;
  font-weight: 600;
  line-height: 1;
  color: $primary-dark;

  small {
    margin-left: 4px;
    font-family: $font-mono;
    font-size: 11px;
    font-weight: 400;
    color: $text-placeholder;
  }
}

.summary-note {
  font-size: 11px;
  line-height: 1.5;
  color: $text-placeholder;
}

.result-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(280px, 0.75fr);
  gap: 20px;
  align-items: start;
}

.attack-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.attack-row {
  padding: 14px 0;
  border-top: 1px solid $border-light;

  &:first-child {
    border-top: none;
    padding-top: 2px;
  }
}

.attack-main {
  display: flex;
  align-items: flex-start;
  gap: 10px;

  .el-tag {
    flex-shrink: 0;
    margin-left: auto;
  }
}

.attack-status {
  display: inline-flex;
  padding-top: 1px;
  font-size: 17px;

  .recovered & {
    color: $primary-color;
  }

  .failed & {
    color: $accent-color;
  }
}

.attack-copy {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;

  strong {
    font-size: 13px;
    font-weight: 600;
    color: $text-primary;
  }

  span {
    font-size: 11px;
    line-height: 1.5;
    color: $text-placeholder;
  }
}

.attack-metrics {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 8px 0 0 27px;
}

.nc-label,
.attack-time {
  font-family: $font-mono;
  font-size: 10px;
  color: $text-placeholder;
}

.attack-time {
  margin-left: auto;
}

.nc-track {
  flex: 1;
  max-width: 240px;
  height: 4px;
  overflow: hidden;
  background: $bg-secondary;
  border-radius: $radius-full;
}

.nc-fill {
  display: block;
  height: 100%;
  border-radius: $radius-full;

  &.good {
    background: $primary-color;
  }
  &.fair {
    background: $accent-color;
  }
  &.poor {
    background: $text-placeholder;
  }
}

.nc-value {
  min-width: 48px;
  font-family: $font-mono;
  font-size: 11px;
  color: $text-secondary;
  text-align: right;
}

.attack-error {
  font-size: 10px;
  color: $accent-color;
}

.preview-card {
  position: sticky;
  top: 84px;
}

.wm-original {
  margin: 0 0 16px;
  padding: 14px;
  background: #fff;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  text-align: center;

  img {
    width: 112px;
    height: 112px;
    image-rendering: pixelated;
  }

  figcaption {
    margin-top: 6px;
    font-size: 11px;
    color: $text-placeholder;
  }
}

.wm-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;

  figure {
    margin: 0;
    padding: 10px;
    background: #fff;
    border: 1px solid $border-color;
    border-radius: $radius-sm;
    text-align: center;
  }

  img {
    width: 76px;
    height: 76px;
    image-rendering: pixelated;
  }

  figcaption {
    margin-top: 5px;
    overflow: hidden;
    font-size: 10px;
    color: $text-placeholder;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.wm-empty {
  margin: 0;
  font-size: 12px;
  line-height: 1.7;
  color: $text-placeholder;
}

.boundary-note {
  margin-top: 18px;
  padding: 14px 16px;
  background: $bg-secondary;
  border-left: 2px solid $accent-color;
  border-radius: 0 $radius-sm $radius-sm 0;

  strong {
    display: block;
    margin-bottom: 5px;
    font-family: $font-display;
    font-size: 13px;
    color: $text-primary;
  }

  p {
    margin: 0;
    font-size: 11px;
    line-height: 1.7;
    color: $text-secondary;
  }
}

.lab-disclaimer {
  margin: 18px 2px 0;
  font-size: 11px;
  line-height: 1.7;
  color: $text-placeholder;
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
    letter-spacing: 0.06em;
    color: $primary-dark;
  }

  dd {
    margin: 0;
    font-size: 13px;
    line-height: 1.8;
    color: $text-secondary;
  }
}

@media (max-width: 960px) {
  .summary-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .result-grid {
    grid-template-columns: 1fr;
  }

  .preview-card {
    position: static;
  }
}

@media (max-width: 720px) {
  .lab-page {
    padding: 24px 16px 56px;
  }

  .lab-title {
    font-size: 28px;
  }

  .lab-card {
    padding: 20px 18px;
  }

  .upload-grid {
    grid-template-columns: 1fr;
  }

  .sample-preview img {
    height: 150px;
  }

  .summary-strip {
    grid-template-columns: 1fr;
  }

  .result-bar {
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
  }

  .card-heading {
    flex-direction: column;
    gap: 6px;
  }

  .card-meta {
    padding-top: 0;
  }

  .attack-metrics {
    flex-wrap: wrap;
    margin-left: 0;
  }

  .nc-track {
    max-width: none;
  }

  .explain-list {
    grid-template-columns: 1fr;
  }
}
</style>
