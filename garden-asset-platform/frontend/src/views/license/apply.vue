<template>
  <div class="license-apply">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>申请授权</span>
          <el-button text @click="goBack">返回</el-button>
        </div>
      </template>

      <!-- 资产信息 -->
      <el-card shadow="hover" class="asset-info-card">
        <template #header>资产信息</template>
        <el-descriptions :column="3" border>
          <el-descriptions-item label="资产编码">{{ asset.asset_code }}</el-descriptions-item>
          <el-descriptions-item label="标题">{{ asset.title }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ getTypeName(asset.asset_type) }}</el-descriptions-item>
          <el-descriptions-item label="所属园林">{{ asset.garden_name }}</el-descriptions-item>
          <el-descriptions-item label="水印状态">
            <StatusTag :status="asset.watermark_status || 'pending'" />
          </el-descriptions-item>
          <el-descriptions-item label="存证状态">
            <StatusTag :status="asset.chain_status || 'pending'" />
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 申请表单 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="授权类型" prop="license_type">
          <el-radio-group v-model="form.license_type">
            <el-radio-button label="personal">个人使用</el-radio-button>
            <el-radio-button label="academic">学术研究</el-radio-button>
            <el-radio-button label="commercial">商业使用</el-radio-button>
            <el-radio-button label="display">展览展示</el-radio-button>
            <el-radio-button label="derivative">衍生创作</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="使用目的" prop="purpose">
          <el-input v-model="form.purpose" type="textarea" :rows="3" placeholder="请详细描述使用目的" />
        </el-form-item>

        <el-form-item label="使用范围">
          <el-checkbox-group v-model="form.scope">
            <el-checkbox label="online">网络发布</el-checkbox>
            <el-checkbox label="print">印刷出版</el-checkbox>
            <el-checkbox label="exhibition">公开展览</el-checkbox>
            <el-checkbox label="broadcast">广播传播</el-checkbox>
          </el-checkbox-group>
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

    <!-- 授权协议对话框 -->
    <el-dialog v-model="agreementVisible" title="数字资产使用授权协议" width="600px">
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
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { assetApi, licenseApi } from '@/api/modules'

const route = useRoute()
const router = useRouter()

const formRef = ref()
const submitting = ref(false)
const agreementVisible = ref(false)

const asset = ref({})
const form = ref({
  license_type: 'personal',
  purpose: '',
  scope: [],
  valid_period: '3m',
  contact: '',
  remarks: '',
  agree: false
})

const rules = {
  license_type: [{ required: true, message: '请选择授权类型', trigger: 'change' }],
  purpose: [{ required: true, message: '请填写使用目的', trigger: 'blur' }],
  valid_period: [{ required: true, message: '请选择使用期限', trigger: 'change' }],
  contact: [{ required: true, message: '请填写联系方式', trigger: 'blur' }]
}

async function loadAsset() {
  const assetId = route.query.asset_id
  if (!assetId) return

  try {
    const response = await assetApi.getDetail(assetId)
    if (response.data.code === 200) {
      asset.value = response.data.data
    }
  } catch (error) {
    ElMessage.error('加载资产失败')
  }
}

async function doSubmit() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  submitting.value = true
  try {
    const data = {
      asset_id: asset.value.id,
      ...form.value
    }
    const response = await licenseApi.apply(data)
    if (response.data.code === 200) {
      ElMessage.success('申请提交成功，请等待审批')
      router.push('/license/my')
    }
  } catch (error) {
    ElMessage.error('申请提交失败')
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
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.license-apply {
  padding: $spacing-lg;
  min-height: 100vh;
  background: $bg-primary;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.asset-info-card {
  margin-bottom: $spacing-lg;
}

.agreement-content {
  max-height: 400px;
  overflow-y: auto;
  line-height: 1.8;

  h4 {
    margin: 15px 0 10px;
    color: $text-primary;
  }

  p {
    margin: 5px 0;
    color: $text-secondary;
    font-size: $font-size-sm;
  }
}

@media (max-width: $breakpoint-sm) {
  .license-apply {
    padding: $spacing-md;
  }

  .asset-info-card {
    margin-bottom: $spacing-md;
  }
}
</style>
