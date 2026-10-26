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
            :on-change="handleFileChange"
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

        <section
          v-if="pendingLoading || pendingSessions.length || pendingError"
          class="resume-panel"
          aria-label="未完成的上传"
        >
          <header class="resume-head">
            <div>
              <strong>未完成的上传</strong>
              <span v-if="pendingSessions.length">
                服务端已保留 {{ pendingTtlHours }} 小时；重新选择同一文件即可从断点继续
              </span>
            </div>
            <el-button
              v-if="pendingError"
              link
              type="primary"
              size="small"
              @click="loadPendingSessions"
            >
              重试
            </el-button>
          </header>
          <p v-if="pendingError" class="resume-error">{{ pendingError }}</p>
          <p v-else-if="pendingLoading && !pendingSessions.length" class="resume-hint">
            正在检查未完成的大文件上传…
          </p>
          <article
            v-for="session in visiblePendingSessions"
            :key="session.upload_id"
            class="resume-item"
          >
            <div class="resume-main">
              <strong class="resume-name">{{ session.filename }}</strong>
              <span class="resume-meta">
                {{ formatFileSize(session.expected_size) }} ·
                已上传 {{ formatFileSize(session.received_size) }}
                （{{ sessionProgressText(session) }}%）
              </span>
              <el-progress
                :percentage="sessionProgressText(session)"
                :stroke-width="4"
                :show-text="false"
              />
            </div>
            <div class="resume-actions">
              <el-button
                size="small"
                type="primary"
                plain
                :disabled="!canResumeSession(session)"
                @click="pickFileForResume(session)"
              >
                {{ canResumeSession(session) ? '选择文件继续' : '其他页面续传中' }}
              </el-button>
              <el-button
                size="small"
                link
                type="danger"
                @click="cancelPending(session)"
              >
                放弃
              </el-button>
            </div>
          </article>
        </section>

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
                  v-if="item.resumeSession && !item.assetId && ['ready', 'failed'].includes(item.status)"
                  size="small"
                  type="warning"
                  effect="plain"
                  disable-transitions
                >
                  续传 {{ sessionProgressText(item.resumeSession) }}%
                </el-tag>
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
                v-if="item.assetId && !uploading"
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
            <el-checkbox v-model="form.auto_chain" :disabled="!form.auto_watermark && hasWatermarkable">
              自动上链存证（无盲水印类型按文件哈希存证）
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
import { onBeforeRouteLeave, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Files, UploadFilled } from '@element-plus/icons-vue'
import { assetApi, gardenApi, watermarkApi, blockchainApi, taskApi } from '@/api/modules'
import { formatFileSize } from '@/utils'
import { computeFileFingerprint, computeFilePrefixHash, findResumableSession, sessionProgress } from '@/utils/resumable'

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
const pendingSessions = ref([])
const pendingLoading = ref(false)
const pendingError = ref('')
const pendingTtlHours = ref(48)
const resumeTargetId = ref('')
let pendingRefreshTimer = null

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
const visiblePendingSessions = computed(() => {
  const bound = new Set(
    queue.value.map(item => item.resumeSession?.upload_id).filter(Boolean)
  )
  return pendingSessions.value.filter(session => !bound.has(session.upload_id))
})

watch(hasWatermarkable, supported => {
  if (supported) {
    form.value.auto_watermark = true
  } else {
    form.value.auto_watermark = false
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

function sessionProgressText(session) {
  return sessionProgress(session)
}

async function loadPendingSessions() {
  if (pendingLoading.value) return
  pendingLoading.value = true
  pendingError.value = ''
  try {
    const response = await assetApi.listUploadSessions()
    if (response.data?.code === 200) {
      pendingSessions.value = response.data.data?.items || []
      pendingTtlHours.value = response.data.data?.ttl_hours || 48
    } else {
      pendingError.value = response.data?.message || '读取未完成上传失败'
    }
  } catch (error) {
    pendingError.value = errorText(error, '读取未完成上传失败')
  } finally {
    pendingLoading.value = false
  }
}

function pickFileForResume(session) {
  resumeTargetId.value = session?.upload_id || ''
  // 清空 el-upload 内部文件列表，确保再次选择同一个文件仍触发 change
  uploadRef.value?.clearFiles()
  const input = uploadRef.value?.$el?.querySelector('input[type=file]')
  if (input) {
    input.click()
  } else {
    ElMessage.info('请点击上方选择区域，选择同名文件继续上传')
  }
}

async function cancelPending(session) {
  try {
    await ElMessageBox.confirm(
      `放弃《${session.filename}》的未完成上传？已上传的分块会被删除，无法恢复。`,
      '放弃上传',
      {
        type: 'warning',
        confirmButtonText: '放弃',
        cancelButtonText: '保留'
      }
    )
  } catch {
    return
  }
  try {
    const response = await assetApi.cancelUploadSession(session.upload_id)
    if (response.data?.code === 200) {
      saveUploadLease(session.upload_id, '')
      pendingSessions.value = pendingSessions.value.filter(
        row => row.upload_id !== session.upload_id
      )
      ElMessage.success('已放弃未完成的上传')
    } else {
      ElMessage.error(response.data?.message || '放弃上传失败')
    }
  } catch (error) {
    ElMessage.error(errorText(error, '放弃上传失败'))
  }
}

function releaseResumeSession(item) {
  const session = item.resumeSession
  if (
    session
    && !pendingSessions.value.some(row => row.upload_id === session.upload_id)
  ) {
    pendingSessions.value.unshift(session)
  }
  item.resumeSession = null
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
  if (raw.size <= 0) {
    ElMessage.error(`${raw.name} 是空文件，不能上传`)
    return null
  }
  return ext
}

async function handleFileChange(uploadFile) {
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
  let fingerprint = ''
  try {
    fingerprint = await computeFileFingerprint(raw)
  } catch (error) {
    ElMessage.error(errorText(error, '无法计算文件指纹，请使用现代浏览器'))
    return
  }
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
    publishing: false,
    fingerprint,
    uploadLease: '',
    resumeSession: null
  }

  // 已被队列项绑定的会话不能再次匹配，避免两个文件交错写入同一临时文件
  const boundIds = new Set(
    queue.value.map(row => row.resumeSession?.upload_id).filter(Boolean)
  )
  const availableSessions = pendingSessions.value.filter(
    session => !boundIds.has(session.upload_id)
  )
  const targeted = availableSessions.find(
    session => session.upload_id === resumeTargetId.value
  )
  const matched = (
    targeted
    && targeted.filename === raw.name
    && Number(targeted.expected_size) === raw.size
    && (!targeted.fingerprint || targeted.fingerprint === fingerprint)
  )
    ? targeted
    : findResumableSession(availableSessions, raw, fingerprint)
  resumeTargetId.value = ''
  if (matched) {
    item.resumeSession = matched
    item.progress = Math.max(
      1,
      Math.round(sessionProgress(matched) * 0.55)
    )
    if (matched.title) item.title = matched.title
    if (matched.asset_type) item.detectedType = matched.asset_type
    // 会话里保存了上次填写的信息；表单为空时自动带出，避免重新填写
    if (!form.value.garden_id && matched.garden_id) {
      form.value.garden_id = matched.garden_id
    }
    if (!form.value.description && matched.description) {
      form.value.description = matched.description
    }
    if (
      (!form.value.tags || !form.value.tags.length)
      && Array.isArray(matched.tags)
      && matched.tags.length
    ) {
      form.value.tags = matched.tags.slice(0, 20)
    }
    pendingSessions.value = pendingSessions.value.filter(
      session => session.upload_id !== matched.upload_id
    )
    ElMessage.info(
      `${raw.name} 检测到未完成上传，将从 ${sessionProgress(matched)}% 处继续`
    )
  }
  queue.value.push(item)
}

function removeItem(item) {
  if (uploading.value) return
  releaseResumeSession(item)
  if (item.previewUrl) URL.revokeObjectURL(item.previewUrl)
  queue.value = queue.value.filter(row => row.uid !== item.uid)
  // el-upload 内部也会保留 File 引用；清掉以免多次增删后占用内存
  uploadRef.value?.clearFiles()
  loadPendingSessions()
}

function clearQueue() {
  if (uploading.value) return
  queue.value.forEach(item => {
    releaseResumeSession(item)
    if (item.previewUrl) URL.revokeObjectURL(item.previewUrl)
  })
  queue.value = []
  uploadRef.value?.clearFiles()
  loadPendingSessions()
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

function savedUploadLease(uploadId) {
  try {
    return sessionStorage.getItem(`upload-lease:${uploadId}`) || ''
  } catch {
    return ''
  }
}

function saveUploadLease(uploadId, token) {
  try {
    if (token) sessionStorage.setItem(`upload-lease:${uploadId}`, token)
    else sessionStorage.removeItem(`upload-lease:${uploadId}`)
  } catch {
    // 浏览器禁用存储时仍可在当前页面续传
  }
}

function canResumeSession(session) {
  return !session.lease_active || Boolean(savedUploadLease(session.upload_id))
}

async function claimSession(item, session) {
  const payload = {
    fingerprint: item.fingerprint,
    lease_token: savedUploadLease(session.upload_id) || undefined
  }
  if (!session.fingerprint) {
    payload.prefix_hash = await computeFilePrefixHash(item.raw)
  }
  const response = await assetApi.claimUploadSession(session.upload_id, payload)
  const data = response.data?.data
  if (response.data?.code !== 200 || !data?.lease_token) {
    throw new Error(response.data?.message || '认领上传会话失败')
  }
  item.uploadLease = data.lease_token
  item.resumeSession = data
  saveUploadLease(session.upload_id, data.lease_token)
  return data
}

async function resolveUploadSession(item, title, options) {
  const candidate = item.resumeSession
  if (candidate) {
    let current = null
    try {
      const response = await assetApi.getUploadSession(candidate.upload_id)
      current = response.data?.data
    } catch (error) {
      if (error.response?.status !== 404) throw error
    }
    if (current?.status === 'completed' && current.asset_id) {
      item.resumeSession = null
      item.uploadLease = ''
      saveUploadLease(candidate.upload_id, '')
      return {
        session: null,
        completed: {
          data: { code: 200, data: { asset_id: current.asset_id } }
        }
      }
    }
    if (
      current?.status === 'uploading'
      && Number(current.expected_size) === item.raw.size
    ) {
      const claimed = await claimSession(item, current)
      // 用户在断点恢复后可能修改了标题/园林/标签，续传前同步到会话
      const synced = await assetApi.updateUploadSession(
        candidate.upload_id,
        {
          title,
          description: options.description,
          garden_id: options.garden_id,
          tags: options.tags,
          asset_type: options.type
        },
        { headers: { 'X-Upload-Lease': item.uploadLease } }
      )
      if (synced.data?.code === 200 && synced.data.data) {
        return { session: { ...claimed, ...synced.data.data }, completed: null }
      }
      throw new Error(synced.data?.message || '同步上传信息失败')
    }
    item.resumeSession = null
  }

  const sessionResponse = await assetApi.createUploadSession({
    filename: item.raw.name,
    size: item.raw.size,
    asset_type: options.type,
    title,
    description: options.description,
    garden_id: options.garden_id,
    tags: options.tags,
    fingerprint: item.fingerprint
  })
  if (sessionResponse.data?.code !== 200) {
    throw new Error(sessionResponse.data?.message || '创建上传会话失败')
  }
  const session = sessionResponse.data.data
  const claimed = await claimSession(item, session)
  return { session: claimed, completed: null }
}

async function uploadResumable(item, options) {
  const title = item.title.trim() || item.name.replace(/\.[^/.]+$/, '')
  const resolved = await resolveUploadSession(item, title, options)
  if (resolved.completed) return resolved.completed
  const session = resolved.session
  const chunkSize = session.chunk_size || 4 * 1024 * 1024
  let received = Number(session.received_size || 0)
  let attempts = 0

  item.progress = Math.max(
    item.progress,
    Math.min(55, Math.round((received / item.raw.size) * 55))
  )
  recalcOverall()

  while (received < item.raw.size) {
    const chunk = item.raw.slice(received, received + chunkSize)
    try {
      const chunkResponse = await assetApi.uploadChunk(
        session.upload_id,
        chunk,
        received,
        {
          timeout: 0,
          headers: { 'X-Upload-Lease': item.uploadLease },
          onUploadProgress: (event) => {
            if (!event.total) return
            const uploaded = received + event.loaded
            item.progress = Math.min(
              55,
              Math.max(1, Math.round((uploaded / item.raw.size) * 55))
            )
            recalcOverall()
          }
        }
      )
      received = Number(chunkResponse.data?.data?.received_size ?? received + chunk.size)
      item.progress = Math.min(
        55,
        Math.max(1, Math.round((received / item.raw.size) * 55))
      )
      recalcOverall()
    } catch (error) {
      attempts += 1
      const statusResponse = await assetApi.getUploadSession(session.upload_id).catch(() => null)
      const current = statusResponse?.data?.data
      if (current?.status === 'completed' && current.asset_id) {
        item.resumeSession = null
        item.uploadLease = ''
        saveUploadLease(session.upload_id, '')
        return {
          data: { code: 200, data: { asset_id: current.asset_id } }
        }
      }
      if (attempts >= 3) throw error
      if (error.response?.data?.error === 'upload_lease_required') {
        await claimSession(item, current || session)
      }
      // 网络中断后查询服务端已接收位置，从断点继续
      const serverOffset = Number(current?.received_size)
      if (Number.isFinite(serverOffset) && serverOffset >= 0) {
        received = serverOffset
      }
      if (received >= item.raw.size) break
      await new Promise(resolve => setTimeout(resolve, 600 * attempts))
    }
  }

  const completed = await assetApi.completeUploadSession(session.upload_id, {
    headers: { 'X-Upload-Lease': item.uploadLease }
  })
  if (completed.data?.code !== 200) {
    throw new Error(completed.data?.message || '合并文件失败')
  }
  item.resumeSession = null
  item.uploadLease = ''
  saveUploadLease(session.upload_id, '')
  return completed
}

async function processItem(item, batchForm) {
  const options = {
    ...batchForm,
    type: batchForm.asset_type || item.detectedType
  }
  item.status = 'uploading'
  item.progress = 1
  item.error = ''
  item.warning = ''
  recalcOverall()

  try {
    // 所有大小的文件都走会话上传：开始上传后刷新页面也能恢复。
    const response = await uploadResumable(item, options)
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

    const type = options.type
    const needsWatermark = ['image', 'vector'].includes(type)

    if (!needsWatermark) {
      item.watermarkReady = true
    } else if (options.auto_watermark) {
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
      options.auto_chain
      && (item.watermarkReady || !needsWatermark)
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

  const batchForm = {
    ...form.value,
    tags: [...(form.value.tags || [])]
  }
  // 上传与任务轮询彼此独立；并发 2 个可显著缩短多文件等待，
  // 同时避免一次性占满后端缩略图/水印 CPU。
  let cursor = 0
  const worker = async () => {
    while (cursor < targets.length) {
      const item = targets[cursor]
      cursor += 1
      if (item.status === 'failed') {
        item.status = 'ready'
        item.error = ''
        item.progress = 0
      }
      uploadMessage.value = `正在处理：${item.name}`
      await processItem(item, batchForm)
    }
  }
  const workerCount = Math.min(2, targets.length)
  await Promise.all(Array.from({ length: workerCount }, worker))

  uploading.value = false
  recalcOverall()
  const failed = failedCount.value
  overallStatus.value = failed ? 'warning' : 'success'
  uploadMessage.value = `处理完成：成功 ${doneCount.value} 件${failed ? `，失败 ${failed} 件` : ''}`
  ElMessage[failed ? 'warning' : 'success'](
    failed ? `上传完成，${failed} 个文件失败，可在队列中查看原因` : '全部文件处理完成，资产已保存为草稿'
  )
  loadPendingSessions()
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
  loadPendingSessions()
  pendingRefreshTimer = window.setInterval(loadPendingSessions, 30000)
  window.addEventListener('beforeunload', handleBeforeUnload)
})

onUnmounted(() => {
  if (pendingRefreshTimer) window.clearInterval(pendingRefreshTimer)
  window.removeEventListener('beforeunload', handleBeforeUnload)
  queue.value.forEach(item => {
    if (item.previewUrl) URL.revokeObjectURL(item.previewUrl)
  })
})

function handleBeforeUnload(event) {
  if (!uploading.value) return
  event.preventDefault()
  event.returnValue = ''
}

onBeforeRouteLeave(() => {
  if (!uploading.value) return true
  return window.confirm(
    '上传仍在进行，离开页面会中断当前批次。8MB 以上文件可在重新打开后从“未完成的上传”恢复；小文件需要重新选择。确定离开？'
  )
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

.resume-panel {
  margin-bottom: 20px;
  padding: 14px 16px;
  border: 1px solid rgba(230, 162, 60, 0.45);
  border-radius: $radius-md;
  background: rgba(230, 162, 60, 0.08);
}

.resume-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 10px;
  margin-bottom: 10px;
  border-bottom: 1px solid rgba(230, 162, 60, 0.25);

  strong {
    font-size: 13px;
    color: $text-primary;
  }

  span {
    display: block;
    margin-top: 4px;
    font-size: 12px;
    color: $text-secondary;
  }
}

.resume-hint,
.resume-error {
  margin: 0;
  font-size: 12px;
  color: $text-secondary;
}

.resume-error {
  color: $error-color;
}

.resume-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px dashed rgba(230, 162, 60, 0.3);

  &:last-child {
    border-bottom: none;
    padding-bottom: 0;
  }
}

.resume-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.resume-name {
  font-size: 13px;
  color: $text-primary;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.resume-meta {
  font-size: 12px;
  color: $text-placeholder;
}

.resume-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 0 0 auto;
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
  .resume-item { flex-wrap: wrap; }
  .resume-actions { width: 100%; justify-content: flex-end; }
}
</style>
