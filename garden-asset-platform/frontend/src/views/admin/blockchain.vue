<template>
  <div class="admin-blockchain">
    <el-card>
      <template #header>
        <span>区块链存证管理</span>
      </template>

      <!-- 区块链状态 -->
      <el-row :gutter="20">
        <el-col :span="8">
          <el-card shadow="hover" class="status-card">
            <div class="stat">
              <div class="stat-value">{{ chainStatus.totalCertificates }}</div>
              <div class="stat-label">存证总数</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover" class="status-card">
            <div class="stat">
              <div class="stat-value">{{ chainStatus.pendingAssets }}</div>
              <div class="stat-label">待上链资产</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover" class="status-card">
            <div class="stat">
              <div class="stat-value">{{ chainStatus.nodeStatus }}</div>
              <div class="stat-label">节点状态</div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 批量上链 -->
      <el-card style="margin-top: 20px">
        <template #header>批量上链存证</template>
        <el-form inline>
          <el-form-item label="待上链资产">
            <el-select v-model="batchRegister.assets" multiple placeholder="选择资产" filterable>
              <el-option
                v-for="a in pendingAssets"
                :key="a.id"
                :label="`${a.asset_code} - ${a.title}`"
                :value="a.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="batchRegister.loading" @click="doBatchRegister">
              批量上链
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 存证记录 -->
      <el-card style="margin-top: 20px">
        <template #header>存证记录</template>
        <el-table :data="certificates" v-loading="logsLoading" stripe>
          <el-table-column prop="certificate_id" label="证书ID" width="180" />
          <el-table-column prop="asset_code" label="资产编码" width="180" />
          <el-table-column prop="asset_title" label="资产标题" min-width="200" show-overflow-tooltip />
          <el-table-column prop="tx_hash" label="交易哈希" width="200">
            <template #default="{ row }">
              <span class="hash">{{ row.tx_hash }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="block_number" label="区块号" width="100" />
          <el-table-column prop="confirmed_at" label="存证时间" width="140">
            <template #default="{ row }">
              {{ formatDate(row.confirmed_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="160" fixed="right">
            <template #default="{ row }">
              <el-button size="small" @click="viewCertificate(row)">查看</el-button>
              <el-button size="small" type="primary" @click="verifyAsset(row)">验证</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { blockchainApi, assetApi } from '@/api/modules'

const router = useRouter()

const chainStatus = ref({
  totalCertificates: 0,
  pendingAssets: 0,
  nodeStatus: '正常'
})

const pendingAssets = ref([])
const certificates = ref([])
const logsLoading = ref(false)

const batchRegister = ref({
  assets: [],
  loading: false
})

async function loadStatus() {
  try {
    const response = await blockchainApi.getStatus()
    if (response.data.code === 200) {
      chainStatus.value = response.data.data
    }
  } catch (error) {
    console.error('加载状态失败:', error)
  }
}

async function loadPendingAssets() {
  try {
    const response = await assetApi.getList({
      watermark_status: 'embedded',
      chain_status: 'pending',
      per_page: 100
    })
    if (response.data.code === 200) {
      pendingAssets.value = response.data.data.items
      chainStatus.value.pendingAssets = pendingAssets.value.length
    }
  } catch (error) {
    console.error('加载待上链资产失败:', error)
  }
}

async function loadCertificates() {
  logsLoading.value = true
  try {
    const response = await blockchainApi.getHistory()
    if (response.data.code === 200) {
      certificates.value = response.data.data
      chainStatus.value.totalCertificates = certificates.value.length
    }
  } catch (error) {
    console.error('加载证书失败:', error)
  } finally {
    logsLoading.value = false
  }
}

async function doBatchRegister() {
  if (batchRegister.value.assets.length === 0) {
    ElMessage.warning('请选择资产')
    return
  }

  batchRegister.value.loading = true
  let successCount = 0
  let failCount = 0

  for (const assetId of batchRegister.value.assets) {
    try {
      await blockchainApi.register(assetId)
      successCount++
    } catch {
      failCount++
    }
  }

  batchRegister.value.loading = false
  ElMessage.success(`批量上链完成，成功${successCount}个，失败${failCount}个`)
  batchRegister.value.assets = []
  loadPendingAssets()
  loadCertificates()
  loadStatus()
}

function viewCertificate(row) {
  router.push(`/certificate/${row.certificate_id}`)
}

async function verifyAsset(row) {
  try {
    const response = await blockchainApi.verify(row.asset_id)
    if (response.data.code === 200) {
      const verified = response.data.data.verified
      ElMessage.success(verified ? '验证通过，数据完整' : '验证失败，数据可能被篡改')
    }
  } catch (error) {
    ElMessage.error('验证失败')
  }
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

onMounted(() => {
  loadStatus()
  loadPendingAssets()
  loadCertificates()
})
</script>

<style scoped>
.admin-blockchain {
  padding: 0;
}

.status-card {
  text-align: center;
}

.stat {
  padding: 20px 0;
}

.stat-value {
  font-size: 32px;
  font-weight: 600;
  color: #409eff;
}

.stat-label {
  font-size: 14px;
  color: #999;
  margin-top: 10px;
}

.hash {
  font-family: monospace;
  font-size: 12px;
  word-break: break-all;
}
</style>