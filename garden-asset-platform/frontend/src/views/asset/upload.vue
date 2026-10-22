<template>
  <div class="upload-page">
    <header class="page-head">
      <router-link to="/assets" class="back-link">
        <el-icon><ArrowLeft /></el-icon>
        返回资产档案
      </router-link>
      <h1 class="page-title">上传资产</h1>
      <p class="page-subtitle">支持一次选择多个文件；每件资产都会生成独立的编码与版本记录。</p>
    </header>

    <section class="form-card">
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        class="upload-form"
      >
        <el-form-item label="资产文件">
          <el-upload
            ref="uploadRef"
            drag
            multiple
            :auto-upload="false"
            :show-file-list="false"
            :limit="50"
            :on-change="handleFileChange"
            :on-exceed="handleExceed"
            accept="image/*,.shp,.geojson,.kml,.kmz,.zip,.pdf,.doc,.docx,.dwg,.dxf,.mp4,.mov,.avi,.mkv,.obj,.fbx,.gltf,.glb,.stl"
            class="asset-uploader"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              将文件拖到此处，或 <em>点击选择文件</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                可多选，最多 50 个；支持影像、SHP/GeoJSON/KML/ZIP 矢量、PDF/Word/CAD 文献、视频与 OBJ/GLB 等三维模型
              </div>
            </template>
          </el-upload>
        </el-form-item>

        <section v-if="queue.length" class="queue-panel" aria-label="待上传文件队列">
          <header class="queue-head">
            <div>
              <strong>待上传文件</strong>
              <span>{{ queue.length }} 个 · {{ totalSizeText }}</span>
            </div>
            <el-button
              v-if="!uploading && !hasStarted"
              link
              type="danger"
              size="small"
              @click="clearQueue"
            >
              清空
            </el-button>
          </header>

          <article
            v-for="item in queue"
            :key="item.uid"
            class="queue-item"
            :class="`status-${item.status}`"
          >
            <div class="queue-thumb">
              <img v-if="item.previewUrl" :src="item.previewUrl" :alt="item.name" />
              <el-icon v-else><Files /></el-icon>
            </div>
            <div class="queue-main">
              <el-input
                v-model="item.title"
                size="small"
                maxlength="100"
                :disabled="item.status === 'uploading' || item.status === 'watermarking' || item.status === 'chaining'"
                class="queue-title"
                :aria-label="`${item.name} 的资产标题`"
              />
              <div class="queue-meta">
                <el-tag size="small" effect="plain">{{ typeLabel(resolveType(item)) }}</el-tag>
                <span>{{ formatFileSize(item.size) }}</span>
                <span class="queue-file-name">{{ item.name }}</span>
                <el-tag
                  v-if="item.status !== 'ready'"
                  size="small"
                  :type="statusTagType(item)"
                >
                  {{ statusLabel(item) }}
                </el-tag>
              </div>
              <el-progress
                v-if="item.status !== 'ready'"
                :percentage="item.progress"
                :stroke-width="4"
                :status="item.status === 'failed' ? 'exception' : (item.status === 'done' ? 'success' : undefined)"
                :show-text="false"
              />
              <p v-if="item.error" class="queue-error">{{ item.error }}</p>
            </div>
            <div class="queue-actions">
              <el-button
                v-if="item.assetId"
                link
                type="primary"
                size="small"
                @click="goToAsset(item)"
              >
                查看
              </el-button>
              <el-button
                v-if="item.assetId && item.watermarkReady && !item.published"
                size="small"
                type="primary"
                plain
                :loading="item.publishing"
                @click="submitPublish(item)"
              >
                提交发布
              </el-button>
              <el-button
                v-if="!item.assetId && !uploading"
                link
                type="danger"
                size="small"
                @click="removeItem(item)"
              >
                移除
              </el-button>
            </div>
          </article>
        </section>

        <div class="form-grid">
          <el-form-item label="统一资产类型（可选）">
            <el-select v-model="form.asset_type" placeholder="默认按扩展名自动识别">
              <el-option label="影像" value="image" />
              <el-option label="三维模型" value="model" />
              <el-option label="矢量数据" value="vector" />
              <el-option label="文献" value="document" />
              <el-option label="视频" value="video" />
            </el-select>
          </el-form-item>

          <el-form-item label="所属园林" prop="garden_id">
            <el-select
              v-model="form.garden_id"
              :loading="gardenLoading"
              :disabled="gardenError"
              placeholder="请选择园林"
              style="width: 100%"
            >
              <el-option v-for="g in gardens" :key="g.id" :label="g.name" :value="g.id" />
            </el-select>
            <div v-if="gardenError" class="garden-error">
              园林列表加载失败，暂时无法上传
              <el-button link type="primary" size="small" @click="loadGardens">重试</el-button>
            </div>
          </el-form-item>
        </div>

        <el-form-item label="描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="4"
            placeholder="记录资产的来源、拍摄/制作信息或权属说明（批量上传时应用到全部文件）"
          />
        </el-form-item>

        <el-form-item label="标签">
          <el-select v-model="form.tags" multiple filterable allow-create placeholder="输入标签（批量上传时应用到全部文件）">
            <el-option label="古典建筑" value="古典建筑" />
            <el-option label="山水景观" value="山水景观" />
            <el-option label="园林植物" value="园林植物" />
            <el-option label="文物古迹" value="文物古迹" />
            <el-option label="历史文献" value="历史文献" />
          </el-select>
        </el-form-item>

        <el-form-item label="水印与存证">
          <div class="option-row">
            <el-checkbox v-model="form.auto_watermark" :disabled="!hasWatermarkable">
              上传后自动嵌入水印<template v-if="!hasWatermarkable">（仅影像/矢量）</template>
            </el-checkbox>
            <el-checkbox v-model="form.auto_chain" :disabled="!form.auto_watermark">
              水印嵌入后自动上链存证
            </el-checkbox>
          </div>
          <p class="watermark-hint">
            水印与存证按文件逐个处理；失败不会回滚已创建的文件，可在资产详情页重试。
          </p>
        </el-form-item>

        <el-form-item>
          <div class="form-actions">
            <el-button
              type="primary"
              :loading="uploading"
              :disabled="queue.length === 0"
              @click="submitUpload"
            >
              {{ uploading ? '正在处理…' : (queue.length ? `开始上传 ${pendingCount} 个文件` : '开始上传') }}
            </el-button>
            <el-button :disabled="uploading" @click="resetForm">重置</el-button>
          </div>
        </el-form-item>
      </el-form>
    </section>

    <section v-if="hasStarted" class="progress-card">
      <h2 class="progress-title">处理进度</h2>
      <el-progress :percentage="overallProgress" :status="overallStatus" />
      <p class="progress-message" aria-live="polite">{{ uploadMessage }}</p>

      <div v-if="!uploading" class="draft-panel">
        <el-alert
          :type="failedCount ? 'warning' : 'info'"
          :closable="false"
          show-icon
          :title="failedCount ? `有 ${failedCount} 个文件处理失败` : '文件已保存为草稿'"
        >
          草稿不会出现在公开资产档案中。完成水印后可在队列里提交发布，或前往“我的资产”统一处理；
          审核通过后才会公开展示。
        </el-alert>
        <div class="progress-actions">
          <el-button type="primary" @click="goToMyAssets">前往我的资产</el-button>
          <el-button v-if="doneCount === 1 && singleDoneItem" @click="goToAsset(singleDoneItem)">
            查看草稿详情
          </el-button>
          <el-button @click="resetForm">继续上传</el-button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Files, UploadFilled } from '@element-plus/icons-vue'
import { assetApi, gardenApi, watermarkApi, blockchainApi, taskApi } from '@/api/modules'
import { formatFileSize } from '@/utils'

const router = useRouter()

const formRef = ref()
const uploadRef = ref()
const gardens = ref([])
const gardenLoading = ref(false)
const gardenError = ref(false)
const uploading = ref(false)
const hasStarted = ref(false)
const overallProgress = ref(0)
const uploadMessage = ref('')
const overallStatus = ref('')
const queue = ref([])
let queueSeq = 0

const TYPE_BY_EXT = {
  jpg: 'image', jpeg: 'image', png: 'image', gif: 'image', bmp: 'image', tiff: 'image', webp: 'image',
  shp: 'vector', geojson: 'vector', kml: 'vector', kmz: 'vector', zip: 'vector',
  pdf: 'document', doc: 'document', docx: 'document', dwg: 'document', dxf: 'document',
  mp4: 'video', mov: 'video', avi: 'video', mkv: 'video',
  obj: 'model', fbx: 'model', gltf: 'model', glb: 'model', stl: 'model'
}

const TYPE_LABELS = {
  image: '影像',
  vector: '矢量',
  model: '三维模型',
  document: '文献',
  video: '视频'
}

const form = ref({
  asset_type: '',
  garden_id: '',
  description: '',
  tags: [],
  auto_watermark: true,
  auto_chain: false
})

const rules = {
  garden_id: [{ required: true, message: '请选择所属园林', trigger: 'change' }]
}

const pendingCount = computed(
  () => queue.value.filter(item => item.status === 'ready' || item.status === 'failed').length
)
const doneCount = computed(() => queue.value.filter(item => item.status === 'done').length)
const failedCount = computed(() => queue.value.filter(item => item.status === 'failed').length)
const singleDoneItem = computed(() => {
  const done = queue.value.filter(item => item.status === 'done')
  return done.length === 1 ? done[0] : null
})
const totalSizeText = computed(() => formatFileSize(
  queue.value.reduce((sum, item) => sum + (item.size || 0), 0)
))
const hasWatermarkable = computed(() =>
  queue.value.some(item => ['image', 'vector'].includes(resolveType(item)))
)

watch(hasWatermarkable, supported => {
  if (supported) {
    form.value.auto_watermark = true
  } else {
    form.value.auto_watermark = false
    form.value.auto_chain = false
  }
}, { immediate: true })

async function loadGardens() {
  gardenLoading.value = true
  gardenError.value = false
  try {
    const response = await gardenApi.getList()
    if (response.data.code === 200 && response.data.data?.length) {
      gardens.value = response.data.data
    } else {
      gardenError.value = true
    }
  } catch (error) {
    console.error('加载园林失败:', error)
    gardenError.value = true
  } finally {
    gardenLoading.value = false
  }
}

const MAX_UPLOAD_SIZE = 500 * 1024 * 1024
const MAX_QUEUE_SIZE = 50

function resolveType(item) {
  return form.value.asset_type || item.detectedType || ''
}

function typeLabel(type) {
  return TYPE_LABELS[type] || '待识别'
}

function statusLabel(item) {
  const labels = {
    uploading: '上传中',
    watermarking: '嵌水印',
    chaining: '上链中',
    done: item.error ? '已完成（有提示）' : '已完成',
    failed: '失败'
  }
  return labels[item.status] || '待上传'
}

function statusTagType(item) {
  if (item.status === 'failed') return 'danger'
  if (item.status === 'done' && item.error) return 'warning'
  if (item.status === 'done') return 'success'
  return 'info'
}

function validateFile(raw) {
  const ext = (raw.name.split('.').pop() || '').toLowerCase()
  if (!TYPE_BY_EXT[ext]) {
    ElMessage.error(`不支持的文件格式：${raw.name}`)
    return null
  }
  if (raw.size > MAX_UPLOAD_SIZE) {
    ElMessage.error(`${raw.name} 超过 500MB 上传限制`)
    return null
  }
  return ext
}

function handleFileChange(uploadFile) {
  const raw = uploadFile.raw
  if (!raw) return
  const ext = validateFile(raw)
  if (!ext) {
    return
  }
  if (queue.value.length >= MAX_QUEUE_SIZE) {
    ElMessage.warning(`一次最多上传 ${MAX_QUEUE_SIZE} 个文件`)
    return
  }
  const duplicated = queue.value.some(item =>
    item.name === raw.name && item.size === raw.size && item.lastModified === raw.lastModified
  )
  if (duplicated) {
    ElMessage.warning(`${raw.name} 已在队列中`)
    return
  }

  const detectedType = TYPE_BY_EXT[ext]
  const item = {
    uid: `queue-${++queueSeq}`,
    raw,
    name: raw.name,
    size: raw.size,
    lastModified: raw.lastModified,
    detectedType,
    title: raw.name.replace(/\.[^/.]+$/, ''),
    previewUrl: detectedType === 'image' ? URL.createObjectURL(raw) : '',
    status: 'ready',
    progress: 0,
    error: '',
    warning: '',
    assetId: '',
    watermarkReady: false,
    published: false,
    publishing: false
  }
  queue.value.push(item)
}

function handleExceed() {
  ElMessage.warning(`一次最多上传 ${MAX_QUEUE_SIZE} 个文件`)
}

function removeItem(item) {
  if (uploading.value) return
  if (item.previewUrl) URL.revokeObjectURL(item.previewUrl)
  queue.value = queue.value.filter(row => row.uid !== item.uid)
}

function clearQueue() {
  if (uploading.value) return
  queue.value.forEach(item => {
    if (item.previewUrl) URL.revokeObjectURL(item.previewUrl)
  })
  queue.value = []
  uploadRef.value?.clearFiles()
}

function recalcOverall() {
  if (!queue.value.length) {
    overallProgress.value = 0
    return
  }
  const total = queue.value.reduce((sum, item) => sum + (item.progress || 0), 0)
  overallProgress.value = Math.round(total / queue.value.length)
}

function errorText(error, fallback) {
  return error.response?.data?.message || error.message || fallback
}

async function waitForTask(taskId, onProgress) {
  for (let attempt = 0; attempt < 160; attempt += 1) {
    await new Promise(resolve => setTimeout(resolve, 1500))
    let task = null
    try {
      const response = await taskApi.get(taskId)
      task = response.data?.data
    } catch {
      continue
    }
    if (!task) continue
    onProgress?.(task)
    if (task.status === 'succeeded') return task
    if (['failed', 'cancelled'].includes(task.status)) {
      throw new Error(task.error_message || '后台任务失败')
    }
  }
  throw new Error('任务处理超时，请稍后在资产详情页查看')
}

async function processItem(item) {
  item.status = 'uploading'
  item.progress = 1
  item.error = ''
  item.warning = ''
  recalcOverall()

  try {
    const formData = new FormData()
    formData.append('file', item.raw)
    formData.append('title', item.title.trim() || item.name.replace(/\.[^/.]+$/, ''))
    formData.append('asset_type', resolveType(item))
    formData.append('garden_id', form.value.garden_id)
    formData.append('description', form.value.description)
    formData.append('tags', JSON.stringify(form.value.tags))

    const response = await assetApi.create(formData, {
      // 大文件可能远超全局 30 秒超时
      timeout: 0,
      onUploadProgress: (event) => {
        if (!event.total) return
        item.progress = Math.min(55, Math.max(1, Math.round((event.loaded / event.total) * 55)))
        recalcOverall()
      }
    })
    if (response.data.code !== 200) {
      throw new Error(response.data.message || '创建资产失败')
    }
    const assetId = response.data.data?.asset_id
    if (!assetId) {
      throw new Error('上传响应缺少资产ID')
    }
    item.assetId = assetId
    item.progress = 60
    recalcOverall()

    const type = resolveType(item)
    const needsWatermark = ['image', 'vector'].includes(type)

    if (!needsWatermark) {
      item.watermarkReady = true
    } else if (form.value.auto_watermark) {
      item.status = 'watermarking'
      item.progress = 65
      recalcOverall()
      try {
        const response = await watermarkApi.embed(assetId, { async: true })
        if (response.data?.code === 202) {
          const taskData = response.data.data || {}
          if (!taskData.worker_enabled) {
            throw new Error('后台 worker 未启用，任务已排队')
          }
          await waitForTask(taskData.task_id, (task) => {
            item.progress = 65 + Math.round((task.progress || 0) * 0.15)
            recalcOverall()
          })
        }
        item.watermarkReady = true
        item.progress = 80
      } catch (error) {
        item.warning = `水印嵌入失败：${errorText(error, '可稍后在资产详情页重试')}`
        item.watermarkReady = false
      }
      recalcOverall()
    }

    if (
      form.value.auto_chain
      && form.value.auto_watermark
      && item.watermarkReady
      && needsWatermark
    ) {
      item.status = 'chaining'
      item.progress = 85
      recalcOverall()
      try {
        const response = await blockchainApi.register(assetId, { async: true })
        if (response.data?.code === 202) {
          const taskData = response.data.data || {}
          if (!taskData.worker_enabled) {
            throw new Error('后台 worker 未启用，任务已排队')
          }
          await waitForTask(taskData.task_id, (task) => {
            item.progress = 85 + Math.round((task.progress || 0) * 0.11)
            recalcOverall()
          })
        }
        item.progress = 96
      } catch (error) {
        item.warning = [item.warning, `上链存证失败：${errorText(error, '可稍后在资产详情页重试')}`]
          .filter(Boolean)
          .join('；')
      }
      recalcOverall()
    }

    item.status = 'done'
    item.progress = 100
    item.error = item.warning || ''
  } catch (error) {
    item.status = 'failed'
    item.progress = 0
    item.error = errorText(error, '上传失败')
  } finally {
    recalcOverall()
  }
}

async function submitUpload() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  if (!queue.value.length) {
    ElMessage.warning('请先选择文件')
    return
  }
  if (gardenError.value) {
    ElMessage.warning('园林列表尚未加载成功，请重试后再上传')
    return
  }

  const targets = queue.value.filter(item => item.status !== 'done')
  if (!targets.length) {
    ElMessage.info('队列中的文件都已处理完成')
    return
  }
  if (targets.some(item => !resolveType(item))) {
    ElMessage.error('有文件无法识别资产类型，请选择统一资产类型后重试')
    return
  }

  uploading.value = true
  hasStarted.value = true
  overallStatus.value = ''
  uploadMessage.value = `开始处理 ${targets.length} 个文件…`
  overallProgress.value = 0

  for (const item of targets) {
    if (item.status === 'failed') {
      item.status = 'ready'
      item.error = ''
      item.progress = 0
    }
    uploadMessage.value = `正在处理：${item.name}`
    await processItem(item)
  }

  uploading.value = false
  recalcOverall()
  const failed = failedCount.value
  overallStatus.value = failed ? 'warning' : 'success'
  uploadMessage.value = `处理完成：成功 ${doneCount.value} 件${failed ? `，失败 ${failed} 件` : ''}`
  ElMessage[failed ? 'warning' : 'success'](
    failed ? `上传完成，${failed} 个文件失败，可在队列中查看原因` : '全部文件处理完成，资产已保存为草稿'
  )
}

async function submitPublish(item) {
  if (!item.assetId || item.publishing) return
  item.publishing = true
  try {
    const response = await assetApi.publish(item.assetId)
    if (response.data.code === 200) {
      item.published = true
      ElMessage.success(`《${item.title}》已提交发布，等待审核`)
    } else {
      ElMessage.error(response.data.message || '提交发布失败')
    }
  } catch (error) {
    ElMessage.error(errorText(error, '提交发布失败'))
  } finally {
    item.publishing = false
  }
}

function goToAsset(item) {
  if (item?.assetId) router.push(`/assets/${item.assetId}`)
}

function goToMyAssets() {
  router.push('/my-assets')
}

function resetForm() {
  if (uploading.value) return
  clearQueue()
  formRef.value?.resetFields()
  form.value.asset_type = ''
  form.value.description = ''
  form.value.tags = []
  form.value.auto_watermark = true
  form.value.auto_chain = false
  hasStarted.value = false
  overallProgress.value = 0
  overallStatus.value = ''
  uploadMessage.value = ''
}

onMounted(() => {
  loadGardens()
})

onUnmounted(() => {
  queue.value.forEach(item => {
    if (item.previewUrl) URL.revokeObjectURL(item.previewUrl)
  })
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.upload-page {
  min-height: 100vh;
  background: $bg-primary;
  padding: 28px 32px 48px;
}

.page-head {
  max-width: 920px;
  margin: 0 auto 20px;

  .back-link {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    color: $text-secondary;
    margin-bottom: 14px;

    &:hover { color: $primary-dark; }
  }

  .page-title {
    font-family: $font-display;
    font-size: 26px;
    font-weight: 600;
    color: $text-primary;
    margin-bottom: 6px;
  }

  .page-subtitle {
    font-size: 14px;
    color: $text-secondary;
  }
}

.form-card,
.progress-card {
  max-width: 920px;
  margin: 0 auto;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
  box-shadow: $shadow-sm;
  padding: 28px;
}

.progress-card {
  margin-top: 16px;
}

.upload-form {
  :deep(.el-form-item__label) {
    font-size: 13px;
    color: $text-secondary;
    padding-bottom: 6px;
  }

  :deep(.el-form-item) {
    margin-bottom: 20px;
  }

  :deep(.el-select) {
    width: 100%;
  }
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.asset-uploader {
  width: 100%;

  :deep(.el-upload) {
    width: 100%;
  }

  :deep(.el-upload-dragger) {
    width: 100%;
    padding: 30px 20px;
    background: $bg-secondary;
    border: 1px dashed $border-color;
    border-radius: $radius-md;
    transition: border-color $transition-fast, background $transition-fast;

    &:hover {
      border-color: $primary-color;
      background: $bg-hover;
    }
  }

  :deep(.el-upload__tip) {
    font-size: 12px;
    color: $text-placeholder;
  }

  .el-icon--upload {
    font-size: 40px;
    color: $primary-light;
    margin-bottom: 8px;
  }
}

.queue-panel {
  margin-bottom: 20px;
  padding: 14px 16px;
  border: 1px solid $border-light;
  border-radius: $radius-md;
  background: $bg-secondary;
}

.queue-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 10px;
  margin-bottom: 10px;
  border-bottom: 1px solid $border-light;

  strong {
    font-size: 13px;
    color: $text-primary;
  }

  span {
    margin-left: 8px;
    font-size: 12px;
    color: $text-placeholder;
  }
}

.queue-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid $border-light;

  &:last-child {
    border-bottom: none;
    padding-bottom: 0;
  }
}

.queue-thumb {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 44px;
  flex: 0 0 56px;
  overflow: hidden;
  border-radius: $radius-xs;
  background: $bg-card;
  border: 1px solid $border-light;
  color: $text-placeholder;
  font-size: 20px;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.queue-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.queue-title {
  max-width: 420px;

  :deep(.el-input__inner) {
    font-size: 13px;
  }
}

.queue-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 11px;
  color: $text-placeholder;
}

.queue-file-name {
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.queue-error {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: $error-color;
}

.queue-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 0 0 auto;
}

.option-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 24px;
}

.watermark-hint {
  width: 100%;
  margin: 8px 0 0;
  font-size: 12px;
  line-height: 1.6;
  color: $text-placeholder;
}

.form-actions {
  display: flex;
  gap: 10px;
}

.progress-title {
  font-family: $font-display;
  font-size: 17px;
  font-weight: 600;
  margin-bottom: 14px;
}

.progress-message {
  margin-top: 10px;
  font-size: 13px;
  color: $text-secondary;
}

.draft-panel {
  margin-top: 18px;

  .progress-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 14px;
  }
}

.garden-error {
  margin-top: 4px;
  font-size: 12px;
  color: $error-color;
}

@media (max-width: 768px) {
  .upload-page { padding: 18px 16px 40px; }
  .form-card,
  .progress-card { padding: 20px 16px; }
  .form-grid { grid-template-columns: 1fr; gap: 0; }
  .form-actions { width: 100%; }
  .form-actions .el-button { flex: 1; }

  .queue-title { max-width: none; }
  .queue-item { flex-wrap: wrap; }
  .queue-actions { width: 100%; justify-content: flex-end; }
}
</style>
