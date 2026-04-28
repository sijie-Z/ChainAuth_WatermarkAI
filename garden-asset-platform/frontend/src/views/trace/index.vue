<template>
  <div class="trace-container">
    <el-card>
      <template #header>
        <span>溯源查询</span>
      </template>

      <!-- 查询方式选择 -->
      <el-tabs v-model="activeTab">
        <el-tab-pane label="上传图片溯源" name="upload">
          <el-upload
            drag
            :auto-upload="false"
            :on-change="handleFileChange"
            :limit="1"
            accept="image/*"
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              将图片拖到此处，或 <em>点击上传</em>
            </div>
          </el-upload>
        </el-tab-pane>

        <el-tab-pane label="水印ID溯源" name="watermark">
          <el-input
            v-model="watermarkId"
            placeholder="请输入水印ID，如：ZY-IMG-20260315143522-A3F8"
            style="width: 400px"
          />
        </el-tab-pane>
      </el-tabs>

      <el-button type="primary" :loading="loading" @click="doTrace" style="margin-top: 20px">
        开始溯源
      </el-button>
    </el-card>

    <!-- 溯源结果 -->
    <el-card v-if="traceResult" class="result-card">
      <template #header>
        <span>溯源结果</span>
        <el-tag :type="traceResult.verified ? 'success' : 'danger'" style="margin-left: 10px">
          {{ traceResult.verified ? '验证通过' : '验证失败' }}
        </el-tag>
      </template>

      <template v-if="traceResult.verified">
        <!-- 资产信息 -->
        <el-descriptions title="资产信息" :column="2" border>
          <el-descriptions-item label="资产编码">{{ traceResult.asset_code }}</el-descriptions-item>
          <el-descriptions-item label="标题">{{ traceResult.title }}</el-descriptions-item>
          <el-descriptions-item label="水印ID">{{ traceResult.watermark_id }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDate(traceResult.created_at) }}</el-descriptions-item>
        </el-descriptions>

        <!-- 区块链存证 -->
        <el-descriptions title="区块链存证" :column="2" border style="margin-top: 20px">
          <el-descriptions-item label="存证状态">
            <el-tag type="success">已存证</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="证书ID">
            <el-link type="primary" @click="viewCertificate">{{ traceResult.certificate_id }}</el-link>
          </el-descriptions-item>
          <el-descriptions-item label="交易哈希">
            <span class="hash">{{ traceResult.tx_hash }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="存证时间">{{ formatDate(traceResult.confirmed_at) }}</el-descriptions-item>
        </el-descriptions>

        <!-- 操作 -->
        <div style="margin-top: 20px">
          <el-button type="primary" @click="viewAsset">查看资产详情</el-button>
          <el-button @click="downloadReport">下载溯源报告</el-button>
        </div>
      </template>

      <template v-else>
        <el-empty description="未找到对应的资产记录，可能为未授权使用">
          <el-button type="primary">举报侵权</el-button>
        </el-empty>
      </template>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
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
      // 上传图片溯源
      const formData = new FormData()
      formData.append('file', uploadedFile.value)
      response = await watermarkApi.trace(formData)
    } else if (activeTab.value === 'watermark' && watermarkId.value) {
      // 水印ID溯源
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
  ElMessage.info('报告生成中...')
  // TODO: 实现报告下载
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN')
}
</script>

<style scoped>
.trace-container {
  padding: 20px;
  min-height: 100vh;
  background: #f5f7fa;
}

.result-card {
  margin-top: 20px;
}

.hash {
  font-family: monospace;
  font-size: 12px;
  word-break: break-all;
}
</style>