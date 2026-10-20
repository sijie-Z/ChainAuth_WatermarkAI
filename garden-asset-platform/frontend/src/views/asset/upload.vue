<template>
  <div class="upload-page">
    <header class="page-head">
      <router-link to="/assets" class="back-link">
        <el-icon><ArrowLeft /></el-icon>
        返回资产档案
      </router-link>
      <h1 class="page-title">上传资产</h1>
      <p class="page-subtitle">文件入库后可按需自动嵌入水印并上链存证。</p>
    </header>

    <section class="form-card">
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        class="upload-form"
      >
        <el-form-item label="资产文件" prop="file">
          <el-upload
            ref="uploadRef"
            drag
            :auto-upload="false"
            :limit="1"
            :on-change="handleFileChange"
            :on-exceed="handleExceed"
            :before-remove="beforeRemove"
            accept="image/*,.shp,.zip,.pdf,.mp4"
            class="asset-uploader"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              将文件拖到此处，或 <em>点击选择文件</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持影像（.jpg/.png）、矢量（.shp/.zip）、文献（.pdf）、视频（.mp4）
              </div>
            </template>
          </el-upload>
        </el-form-item>

        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" placeholder="请输入资产标题" maxlength="100" show-word-limit />
        </el-form-item>

        <div class="form-grid">
          <el-form-item label="资产类型" prop="asset_type">
            <el-select v-model="form.asset_type" placeholder="请选择类型">
              <el-option label="影像" value="image" />
              <el-option label="三维模型" value="model" />
              <el-option label="矢量数据" value="vector" />
              <el-option label="文献" value="document" />
              <el-option label="视频" value="video" />
            </el-select>
          </el-form-item>

          <el-form-item label="所属园林" prop="garden_id">
            <el-select v-model="form.garden_id" placeholder="请选择园林">
              <el-option v-for="g in gardens" :key="g.id" :label="g.name" :value="g.id" />
            </el-select>
          </el-form-item>
        </div>

        <el-form-item label="描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="4"
            placeholder="记录资产的来源、拍摄/制作信息或权属说明"
          />
        </el-form-item>

        <el-form-item label="标签">
          <el-select v-model="form.tags" multiple filterable allow-create placeholder="输入标签">
            <el-option label="古典建筑" value="古典建筑" />
            <el-option label="山水景观" value="山水景观" />
            <el-option label="园林植物" value="园林植物" />
            <el-option label="文物古迹" value="文物古迹" />
            <el-option label="历史文献" value="历史文献" />
          </el-select>
        </el-form-item>

        <el-form-item label="水印与存证">
          <div class="option-row">
            <el-checkbox v-model="form.auto_watermark" :disabled="!canWatermark">
              上传后自动嵌入水印<template v-if="!canWatermark">（仅影像/矢量）</template>
            </el-checkbox>
            <el-checkbox v-model="form.auto_chain" :disabled="!form.auto_watermark">
              水印嵌入后自动上链存证
            </el-checkbox>
          </div>
        </el-form-item>

        <el-form-item>
          <div class="form-actions">
            <el-button type="primary" :loading="uploading" @click="submitUpload">
              {{ uploading ? '上传中…' : '开始上传' }}
            </el-button>
            <el-button :disabled="uploading" @click="resetForm">重置</el-button>
          </div>
        </el-form-item>
      </el-form>
    </section>

    <section v-if="uploadProgress > 0" class="progress-card">
      <h2 class="progress-title">上传进度</h2>
      <el-progress :percentage="uploadProgress" :status="uploadStatus" />
      <p class="progress-message" aria-live="polite">{{ uploadMessage }}</p>

      <!-- 上传成功：明确草稿状态并提供提交发布入口 -->
      <div v-if="createdAssetId" class="draft-panel">
        <el-alert type="info" :closable="false" show-icon title="资产已保存为草稿">
          草稿不会出现在公开的资产档案中。点击「提交发布」后进入管理员审核，审核通过后才会公开展示。
        </el-alert>
        <div class="progress-actions">
          <el-button type="primary" :loading="publishing" @click="submitPublish">
            提交发布
          </el-button>
          <el-button @click="goToDetail">查看资产详情</el-button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled, ArrowLeft } from '@element-plus/icons-vue'
import { assetApi, gardenApi, watermarkApi, blockchainApi } from '@/api/modules'

const router = useRouter()

const formRef = ref()
const uploadRef = ref()
const gardens = ref([])
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadStatus = ref('')
const uploadMessage = ref('')
const createdAssetId = ref('')
const publishing = ref(false)

const form = ref({
  file: null,
  title: '',
  asset_type: '',
  garden_id: '',
  description: '',
  tags: [],
  auto_watermark: true,
  auto_chain: false
})

const rules = {
  file: [{ required: true, message: '请上传资产文件', trigger: 'change' }],
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  asset_type: [{ required: true, message: '请选择资产类型', trigger: 'change' }],
  garden_id: [{ required: true, message: '请选择所属园林', trigger: 'change' }]
}

// 当前水印算法只覆盖影像与矢量数据
const canWatermark = computed(() => ['image', 'vector'].includes(form.value.asset_type))

watch(canWatermark, supported => {
  if (!supported) form.value.auto_watermark = false
})

async function loadGardens() {
  try {
    const response = await gardenApi.getList()
    if (response.data.code === 200) {
      gardens.value = response.data.data
    }
  } catch (error) {
    console.error('加载园林失败:', error)
  }
}

function handleFileChange(file) {
  form.value.file = file.raw
  if (!form.value.title) {
    form.value.title = file.name.replace(/\.[^/.]+$/, '')
  }
}

function handleExceed() {
  ElMessage.warning('只能上传一个文件')
}

function beforeRemove(file) {
  return ElMessageBox.confirm('确定移除该文件？')
}

async function submitUpload() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  if (!form.value.file) {
    ElMessage.warning('请先选择文件')
    return
  }

  uploading.value = true
  createdAssetId.value = ''
  uploadProgress.value = 10
  uploadMessage.value = '正在上传文件…'
  uploadStatus.value = ''

  try {
    const formData = new FormData()
    formData.append('file', form.value.file)
    formData.append('title', form.value.title)
    formData.append('asset_type', form.value.asset_type)
    formData.append('garden_id', form.value.garden_id)
    formData.append('description', form.value.description)
    formData.append('tags', JSON.stringify(form.value.tags))

    uploadProgress.value = 30
    uploadMessage.value = '正在创建资产记录…'

    const response = await assetApi.create(formData)
    if (response.data.code !== 200) {
      throw new Error(response.data.message || '创建资产失败')
    }

    const assetId = response.data.data?.asset_id
    if (!assetId) {
      throw new Error('上传响应缺少资产ID')
    }

    createdAssetId.value = assetId
    uploadProgress.value = 50
    uploadMessage.value = '资产创建成功，当前为草稿状态'

    // 文件已入库，后续水印/存证失败不应把整个上传判定为失败
    let watermarkEmbedded = false
    if (form.value.auto_watermark) {
      uploadMessage.value = '正在嵌入水印…'
      uploadProgress.value = 60
      try {
        await watermarkApi.embed(assetId)
        watermarkEmbedded = true
        uploadProgress.value = 75
        uploadMessage.value = '水印嵌入成功'
      } catch (error) {
        uploadMessage.value = '水印嵌入失败，资产已保存为草稿'
        ElMessage.warning(error.response?.data?.message || '水印嵌入失败，可稍后在资产详情页重试')
      }
    }

    if (form.value.auto_chain && form.value.auto_watermark && watermarkEmbedded) {
      uploadMessage.value = '正在上链存证…'
      uploadProgress.value = 85
      try {
        await blockchainApi.register(assetId)
        uploadProgress.value = 95
        uploadMessage.value = '存证完成'
      } catch (error) {
        ElMessage.warning(error.response?.data?.message || '上链存证失败，可稍后在资产详情页重试')
      }
    }

    uploadProgress.value = 100
    uploadStatus.value = 'success'
    uploadMessage.value = '上传完成，资产已保存为草稿'

    ElMessage.success('资产上传成功，当前为草稿状态')
  } catch (error) {
    uploadStatus.value = 'exception'
    uploadMessage.value = '上传失败：' + (error.response?.data?.message || error.message || '未知错误')
    ElMessage.error('上传失败')
  } finally {
    uploading.value = false
  }
}

async function submitPublish() {
  if (!createdAssetId.value || publishing.value) return

  publishing.value = true
  try {
    const response = await assetApi.publish(createdAssetId.value)
    if (response.data.code === 200) {
      ElMessage.success('已提交发布，请等待管理员审核')
      router.push(`/assets/${createdAssetId.value}`)
    } else {
      ElMessage.error(response.data.message || '提交发布失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '提交发布失败')
  } finally {
    publishing.value = false
  }
}

function goToDetail() {
  if (createdAssetId.value) {
    router.push(`/assets/${createdAssetId.value}`)
  }
}

function resetForm() {
  formRef.value.resetFields()
  uploadRef.value.clearFiles()
  form.value.file = null
  uploadProgress.value = 0
  uploadMessage.value = ''
  uploadStatus.value = ''
  createdAssetId.value = ''
}

onMounted(() => {
  loadGardens()
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
  max-width: 880px;
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
  max-width: 880px;
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
    padding: 32px 20px;
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

.option-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 24px;
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
    gap: 10px;
    margin-top: 14px;
  }
}

@media (max-width: 768px) {
  .upload-page { padding: 18px 16px 40px; }
  .form-card,
  .progress-card { padding: 20px 16px; }
  .form-grid { grid-template-columns: 1fr; gap: 0; }
  .form-actions { width: 100%; }
  .form-actions .el-button { flex: 1; }
}
</style>
