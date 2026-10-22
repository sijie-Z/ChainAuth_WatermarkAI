<template>
  <div class="license-apply">
    <header class="page-bar">
      <router-link to="/assets" class="page-back">
        <el-icon><ArrowLeft /></el-icon>
        返回资产档案
      </router-link>
      <h1 class="page-title">申请授权</h1>
    </header>

    <!-- 资产加载中 -->
    <el-card v-if="assetLoading" class="asset-info-card">
      <el-skeleton :rows="3" animated />
    </el-card>

    <!-- 资产缺失或加载失败：阻止继续填写 -->
    <el-card v-else-if="assetError" class="asset-info-card">
      <el-empty :description="assetError">
        <el-button type="primary" @click="goBack">返回资产档案</el-button>
      </el-empty>
    </el-card>

    <template v-else>
    <!-- 资产信息 -->
    <el-card class="asset-info-card">
      <template #header>
        <div class="card-header">
          <span>资产信息</span>
          <span v-if="asset.asset_code" class="asset-code">{{ asset.asset_code }}</span>
        </div>
      </template>
      <el-descriptions :column="isMobile ? 1 : 3" border>
        <el-descriptions-item label="资产编码">{{ asset.asset_code }}</el-descriptions-item>
        <el-descriptions-item label="标题">{{ asset.title }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{ getTypeName(asset.asset_type) }}</el-descriptions-item>
        <el-descriptions-item label="所属园林">{{ asset.garden_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="水印状态">
          <StatusTag :status="asset.watermark_status || 'none'" kind="watermark" />
        </el-descriptions-item>
        <el-descriptions-item label="存证状态">
          <StatusTag :status="asset.chain_status || 'none'" kind="chain" />
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 申请表单 -->
    <el-card class="form-card">
      <template #header>
        <div class="card-header">
          <span>授权信息</span>
        </div>
      </template>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px" class="apply-form">
        <el-form-item label="授权类型" prop="license_type">
          <el-radio-group v-model="form.license_type">
            <el-radio-button value="personal">个人使用</el-radio-button>
            <el-radio-button value="academic">学术研究</el-radio-button>
            <el-radio-button value="commercial">商业使用</el-radio-button>
            <el-radio-button value="display">展览展示</el-radio-button>
            <el-radio-button value="derivative">衍生创作</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="使用目的" prop="usage_purpose_code">
          <el-select v-model="form.usage_purpose_code" placeholder="选择使用目的" style="width: 100%">
            <el-option label="个人学习" value="personal_learning" />
            <el-option label="教学科研" value="teaching_research" />
            <el-option label="商业宣传" value="commercial_marketing" />
            <el-option label="出版发行" value="publication" />
            <el-option label="公开展览" value="exhibition" />
            <el-option label="衍生创作" value="derivative" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>

        <el-form-item label="用途说明" prop="purpose">
          <el-input v-model="form.purpose" type="textarea" :rows="3" placeholder="请详细描述使用目的" />
        </el-form-item>

        <el-form-item label="使用渠道">
          <el-checkbox-group v-model="form.scope">
            <el-checkbox label="online">网络发布</el-checkbox>
            <el-checkbox label="print">印刷出版</el-checkbox>
            <el-checkbox label="exhibition">公开展览</el-checkbox>
            <el-checkbox label="broadcast">广播传播</el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-form-item label="授权地域">
          <el-select v-model="form.territory" style="width: 180px">
            <el-option label="中国大陆" value="中国大陆" />
            <el-option label="中国港澳台" value="中国港澳台" />
            <el-option label="全球" value="全球" />
            <el-option label="海外" value="海外" />
          </el-select>
          <span class="form-hint">下载时需申报使用地域，与授权地域一致</span>
        </el-form-item>

        <el-form-item label="可下载格式">
          <el-checkbox-group v-model="form.allowed_formats">
            <el-checkbox
              v-for="format in formatOptions"
              :key="format"
              :label="format"
            >
              {{ format }}
            </el-checkbox>
          </el-checkbox-group>
          <span class="form-hint">不勾选表示不限制；限制后仅允许下载这些源格式</span>
        </el-form-item>

        <el-form-item label="下载次数">
          <el-input
            v-model="form.max_downloads"
            placeholder="留空表示不限制"
            style="width: 180px"
          />
          <span class="form-hint">单次授权最多可下载的次数（1-10000）</span>
        </el-form-item>

        <el-form-item label="使用期限" prop="valid_period">
          <el-select v-model="form.valid_period" placeholder="选择期限">
            <el-option label="1个月" value="1m" />
            <el-option label="3个月" value="3m" />
            <el-option label="6个月" value="6m" />
            <el-option label="1年" value="1y" />
            <el-option label="永久" value="permanent" />
          </el-select>
        </el-form-item>

        <el-form-item label="联系方式" prop="contact">
          <el-input v-model="form.contact" placeholder="联系电话或邮箱" />
        </el-form-item>

        <el-form-item label="附加说明">
          <el-input v-model="form.remarks" type="textarea" :rows="2" placeholder="其他需要说明的事项" />
        </el-form-item>

        <!-- 授权协议 -->
        <el-form-item label="授权协议">
          <el-checkbox v-model="form.agree">
            我已阅读并同意
            <el-link type="primary" @click="showAgreement">《数字资产使用授权协议》</el-link>
          </el-checkbox>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="submitting" :disabled="!form.agree" @click="doSubmit">
            提交申请
          </el-button>
          <el-button @click="goBack">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
    </template>

    <!-- 授权协议对话框 -->
    <el-dialog v-model="agreementVisible" title="数字资产使用授权协议" width="min(600px, 92vw)">
      <div class="agreement-content">
        <h4>一、总则</h4>
        <p>本协议是苏州园林数字资产平台（以下简称"本平台"）与用户之间关于数字资产使用授权的法律协议。</p>

        <h4>二、授权内容</h4>
        <p>1. 本平台授权用户在约定范围内使用指定的数字资产。</p>
        <p>2. 用户不得超出授权范围使用数字资产，不得进行二次授权。</p>
        <p>3. 用户在使用过程中需保留水印标识，不得去除或篡改。</p>

        <h4>三、知识产权</h4>
        <p>1. 数字资产的知识产权归原权利人所有。</p>
        <p>2. 本授权不转移知识产权，仅授予使用权。</p>
        <p>3. 用户使用时应当注明来源。</p>

        <h4>四、违约责任</h4>
        <p>违反本协议的，本平台有权终止授权，并追究法律责任。</p>
      </div>
      <template #footer>
        <el-button type="primary" @click="agreementVisible = false">我已阅读</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import { assetApi, licenseApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const formRef = ref()
const submitting = ref(false)
const agreementVisible = ref(false)
const assetLoading = ref(true)
const assetError = ref('')
const isMobile = ref(window.innerWidth <= 768)

const asset = ref({})
const form = ref({
  license_type: 'personal',
  usage_purpose_code: 'personal_learning',
  purpose: '',
  scope: ['online'],
  territory: '中国大陆',
  allowed_formats: [],
  max_downloads: '',
  valid_period: '3m',
  contact: '',
  remarks: '',
  agree: false
})

const FORMAT_LIMITS = {
  image: ['JPG', 'PNG', 'TIFF', 'WEBP'],
  vector: ['ZIP', 'SHP', 'GEOJSON', 'KML'],
  document: ['PDF', 'DOC', 'DOCX', 'DWG', 'DXF'],
  video: ['MP4', 'MOV', 'AVI', 'MKV'],
  model: ['OBJ', 'FBX', 'GLTF', 'GLB', 'STL', 'ZIP']
}

const formatOptions = computed(() => {
  const list = [...(FORMAT_LIMITS[asset.value.asset_type] || [])]
  const current = (asset.value.file_format || '').toUpperCase()
  if (current && !list.includes(current)) list.unshift(current)
  return list
})

const rules = {
  license_type: [{ required: true, message: '请选择授权类型', trigger: 'change' }],
  usage_purpose_code: [{ required: true, message: '请选择使用目的', trigger: 'change' }],
  purpose: [{ required: true, message: '请填写用途说明', trigger: 'blur' }],
  valid_period: [{ required: true, message: '请选择使用期限', trigger: 'change' }],
  contact: [{ required: true, message: '请填写联系方式', trigger: 'blur' }]
}

async function loadAsset() {
  const assetId = route.query.asset_id
  if (!assetId) {
    assetError.value = '未指定要申请授权的资产'
    assetLoading.value = false
    return
  }

  try {
    const response = await assetApi.getDetail(assetId)
    if (response.data.code === 200) {
      asset.value = response.data.data
      const current = (asset.value.file_format || '').toUpperCase()
      form.value.allowed_formats = current ? [current] : []
    } else {
      assetError.value = response.data.message || '资产不存在或不可申请授权'
    }
  } catch {
    assetError.value = '资产加载失败，请返回资产档案后重试'
  } finally {
    assetLoading.value = false
  }
}

async function doSubmit() {
  if (!asset.value.id) {
    ElMessage.error('资产信息尚未加载，无法提交申请')
    return
  }

  try {
    await formRef.value.validate()
  } catch {
    return
  }

  submitting.value = true
  try {
    const scopeLabels = {
      online: '网络发布',
      print: '印刷出版',
      exhibition: '公开展览',
      broadcast: '广播传播'
    }
    const scopeText = form.value.scope.map(item => scopeLabels[item] || item).join('、')
    const purpose = [
      form.value.purpose,
      scopeText ? `使用范围：${scopeText}` : '',
      form.value.remarks ? `附加说明：${form.value.remarks}` : ''
    ].filter(Boolean).join('\n')

    const data = {
      asset_id: asset.value.id,
      ...form.value,
      allowed_channels: form.value.scope,
      max_downloads: form.value.max_downloads === '' ? null : form.value.max_downloads,
      purpose
    }
    delete data.scope
    delete data.agree
    delete data.remarks
    const response = await licenseApi.apply(data)
    if (response.data?.code === 200) {
      ElMessage.success('申请提交成功，请等待审批')
      // 直接落到“申请记录”，用户能立刻看到刚提交的申请
      await router.push('/license/my?tab=pending')
    } else {
      ElMessage.error(response.data?.message || '申请提交失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '申请提交失败')
  } finally {
    submitting.value = false
  }
}

function showAgreement() {
  agreementVisible.value = true
}

function goBack() {
  router.push('/assets')
}

function getTypeName(type) {
  const map = { image: '影像', model: '模型', vector: '矢量', document: '文献', video: '视频' }
  return map[type] || type
}

onMounted(() => {
  loadAsset()
  window.addEventListener('resize', handleResize)
  const currentUser = userStore.user
  if (currentUser) {
    form.value.contact = currentUser.phone || currentUser.email || ''
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})

function handleResize() {
  isMobile.value = window.innerWidth <= 768
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.license-apply {
  max-width: 960px;
  margin: 0 auto;
  padding: $spacing-2xl $spacing-3xl;
  min-height: 100vh;
  background: $bg-primary;

  :deep(.el-card__header) {
    padding: $spacing-lg $spacing-xl;
    border-bottom: 1px solid $border-light;
  }

  :deep(.el-card__body) {
    padding: $spacing-xl;
  }
}

// ========== 页眉 ==========
.page-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: $spacing-md;
  padding-bottom: $spacing-md;
  margin-bottom: $spacing-xl;
  border-bottom: 1px solid $border-light;
}

.page-back {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: $font-size-sm;
  color: $text-secondary;
  transition: color $transition-fast;

  &:hover {
    color: $primary-dark;
  }
}

.page-title {
  font-family: $font-display;
  font-size: 23px;
  font-weight: $font-weight-semibold;
  line-height: $line-height-tight;
  letter-spacing: 0.02em;
  color: $text-primary;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: $spacing-md;
  font-family: $font-display;
  font-size: $font-size-lg;
  font-weight: $font-weight-semibold;
  color: $text-primary;

  .asset-code {
    font-family: $font-mono;
    font-size: $font-size-xs;
    font-weight: $font-weight-normal;
    letter-spacing: 0.08em;
    color: $text-placeholder;
  }
}

.asset-info-card {
  margin-bottom: $spacing-xl;
}

.apply-form {
  :deep(.el-radio-group) {
    flex-wrap: wrap;
    row-gap: $spacing-sm;
  }

  :deep(.el-checkbox-group) {
    display: flex;
    flex-wrap: wrap;
    gap: $spacing-xs $spacing-lg;
  }
}

.agreement-content {
  max-height: 400px;
  overflow-y: auto;
  line-height: $line-height-relaxed;
  font-size: $font-size-sm;
  color: $text-secondary;

  h4 {
    margin: $spacing-lg 0 $spacing-sm;
    font-family: $font-display;
    font-size: $font-size-md;
    color: $text-primary;
  }

  p {
    margin: $spacing-xs 0;
  }
}

.form-hint {
  margin-left: 10px;
  font-size: 12px;
  line-height: 1.6;
  color: $text-placeholder;
}

@media (max-width: $breakpoint-md) {
  .license-apply {
    padding: $spacing-lg;
  }

  .asset-info-card {
    margin-bottom: $spacing-lg;
  }

  .apply-form {
    :deep(.el-form-item) {
      flex-direction: column;
      align-items: flex-start;
    }

    :deep(.el-form-item__label) {
      width: auto !important;
      margin-bottom: 6px;
      text-align: left;
    }

    :deep(.el-form-item__content) {
      width: 100%;
    }
  }
}
</style>
