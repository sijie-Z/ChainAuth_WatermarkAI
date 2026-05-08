<template>
  <div class="upload-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>上传资产</span>
          <el-button text @click="goBack">返回</el-button>
        </div>
      </template>

      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <!-- 文件上传 -->
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
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              将文件拖到此处，或 <em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持影像(.jpg/.png)、矢量(.shp/.zip)、文献(.pdf)、视频(.mp4)
              </div>
            </template>
          </el-upload>
        </el-form-item>

        <!-- 基本信息 -->
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" placeholder="请输入资产标题" maxlength="100" show-word-limit />
        </el-form-item>

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

        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="4" placeholder="请输入资产描述" />
        </el-form-item>

        <!-- 标签 -->
        <el-form-item label="标签">
          <el-select v-model="form.tags" multiple filterable allow-create placeholder="输入标签">
            <el-option label="古典建筑" value="古典建筑" />
            <el-option label="山水景观" value="山水景观" />
            <el-option label="园林植物" value="园林植物" />
            <el-option label="文物古迹" value="文物古迹" />
            <el-option label="历史文献" value="历史文献" />
          </el-select>
        </el-form-item>

        <!-- 水印选项 -->
        <el-form-item label="水印设置">
          <el-checkbox v-model="form.auto_watermark">上传后自动嵌入水印</el-checkbox>
          <el-checkbox v-model="form.auto_chain" :disabled="!form.auto_watermark">水印嵌入后自动上链存证</el-checkbox>
        </el-form-item>

        <!-- 提交按钮 -->
        <el-form-item>
          <el-button type="primary" :loading="uploading" @click="submitUpload">
            {{ uploading ? '上传中...' : '开始上传' }}
          </el-button>
          <el-button @click="resetForm">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 上传进度 -->
    <el-card v-if="uploadProgress > 0" class="progress-card">
      <template #header>上传进度</template>
      <el-progress :percentage="uploadProgress" :status="uploadStatus" />
      <div class="progress-message">{{ uploadMessage }}</div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { assetApi, gardenApi, watermarkApi, blockchainApi } from '@/api/modules'

const router = useRouter()

const formRef = ref()
const uploadRef = ref()
const gardens = ref([])
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadStatus = ref('')
const uploadMessage = ref('')

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
  uploadProgress.value = 10
  uploadMessage.value = '正在上传文件...'
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
    uploadMessage.value = '正在创建资产记录...'

    const response = await assetApi.create(formData)
    if (response.data.code !== 200) {
      throw new Error(response.data.message)
    }

    const assetId = response.data.data.id
    uploadProgress.value = 50
    uploadMessage.value = '资产创建成功'

    if (form.value.auto_watermark) {
      uploadMessage.value = '正在嵌入水印...'
      uploadProgress.value = 60
      await watermarkApi.embed(assetId)
      uploadProgress.value = 75
      uploadMessage.value = '水印嵌入成功'
    }

    if (form.value.auto_chain && form.value.auto_watermark) {
      uploadMessage.value = '正在上链存证...'
      uploadProgress.value = 85
      await blockchainApi.register(assetId)
      uploadProgress.value = 95
      uploadMessage.value = '存证完成'
    }

    uploadProgress.value = 100
    uploadStatus.value = 'success'
    uploadMessage.value = '上传完成！'

    ElMessage.success('资产上传成功')

    setTimeout(() => {
      router.push(`/assets/${assetId}`)
    }, 1500)

  } catch (error) {
    uploadStatus.value = 'exception'
    uploadMessage.value = '上传失败: ' + (error.message || '未知错误')
    ElMessage.error('上传失败')
  } finally {
    uploading.value = false
  }
}

function resetForm() {
  formRef.value.resetFields()
  uploadRef.value.clearFiles()
  form.value.file = null
  uploadProgress.value = 0
  uploadMessage.value = ''
}

function goBack() {
  router.push('/assets')
}

onMounted(() => {
  loadGardens()
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.upload-container {
  padding: $spacing-lg;
  min-height: 100vh;
  background: $bg-primary;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.progress-card {
  margin-top: $spacing-lg;
}

.progress-message {
  margin-top: $spacing-sm;
  color: $text-secondary;
  font-size: $font-size-sm;
}
</style>
