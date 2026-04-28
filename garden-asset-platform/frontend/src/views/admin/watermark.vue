<template>
  <div class="admin-watermark">
    <el-card>
      <template #header>
        <span>水印处理管理</span>
      </template>

      <!-- 批量处理 -->
      <el-row :gutter="20">
        <el-col :span="12">
          <el-card shadow="hover">
            <template #header>批量嵌入水印</template>
            <el-form label-width="80px">
              <el-form-item label="选择资产">
                <el-select v-model="batchEmbed.assets" multiple placeholder="选择待嵌入资产" filterable>
                  <el-option
                    v-for="a in pendingAssets"
                    :key="a.id"
                    :label="a.title"
                    :value="a.id"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="水印算法">
                <el-select v-model="batchEmbed.algorithm">
                  <el-option label="DCT域水印" value="dct" />
                  <el-option label="LSB水印" value="lsb" />
                  <el-option label="矢量水印" value="vector" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="batchEmbed.loading" @click="doBatchEmbed">
                  开始嵌入
                </el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </el-col>

        <el-col :span="12">
          <el-card shadow="hover">
            <template #header>批量提取水印</template>
            <el-form label-width="80px">
              <el-form-item label="选择资产">
                <el-select v-model="batchExtract.assets" multiple placeholder="选择已嵌入资产" filterable>
                  <el-option
                    v-for="a in embeddedAssets"
                    :key="a.id"
                    :label="a.title"
                    :value="a.id"
                  />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button type="success" :loading="batchExtract.loading" @click="doBatchExtract">
                  开始提取
                </el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </el-col>
      </el-row>

      <!-- 水印记录 -->
      <el-card style="margin-top: 20px">
        <template #header>水印操作记录</template>
        <el-table :data="watermarkLogs" v-loading="logsLoading" stripe>
          <el-table-column prop="asset_code" label="资产编码" width="180" />
          <el-table-column prop="asset_title" label="资产标题" min-width="200" show-overflow-tooltip />
          <el-table-column prop="operation" label="操作类型" width="100">
            <template #default="{ row }">
              <el-tag :type="row.operation === 'embed' ? 'success' : 'warning'" size="small">
                {{ row.operation === 'embed' ? '嵌入' : '提取' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="watermark_id" label="水印ID" width="180" />
          <el-table-column prop="nc_value" label="NC值" width="100">
            <template #default="{ row }">
              {{ row.nc_value ? row.nc_value.toFixed(4) : '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="operator" label="操作人" width="100" />
          <el-table-column prop="created_at" label="操作时间" width="140">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { assetApi, watermarkApi } from '@/api/modules'

const pendingAssets = ref([])
const embeddedAssets = ref([])
const watermarkLogs = ref([])
const logsLoading = ref(false)

const batchEmbed = ref({
  assets: [],
  algorithm: 'dct',
  loading: false
})

const batchExtract = ref({
  assets: [],
  loading: false
})

async function loadAssets() {
  try {
    const [pendingRes, embeddedRes] = await Promise.all([
      assetApi.getList({ watermark_status: 'pending', per_page: 100 }),
      assetApi.getList({ watermark_status: 'embedded', per_page: 100 })
    ])

    if (pendingRes.data.code === 200) {
      pendingAssets.value = pendingRes.data.data.items
    }
    if (embeddedRes.data.code === 200) {
      embeddedAssets.value = embeddedRes.data.data.items
    }
  } catch (error) {
    ElMessage.error('加载资产失败')
  }
}

async function loadLogs() {
  logsLoading.value = true
  try {
    const response = await watermarkApi.getLogs()
    if (response.data.code === 200) {
      watermarkLogs.value = response.data.data
    }
  } catch (error) {
    console.error('加载日志失败:', error)
  } finally {
    logsLoading.value = false
  }
}

async function doBatchEmbed() {
  if (batchEmbed.value.assets.length === 0) {
    ElMessage.warning('请选择资产')
    return
  }

  batchEmbed.value.loading = true
  let successCount = 0
  let failCount = 0

  for (const assetId of batchEmbed.value.assets) {
    try {
      await watermarkApi.embed(assetId, { algorithm: batchEmbed.value.algorithm })
      successCount++
    } catch {
      failCount++
    }
  }

  batchEmbed.value.loading = false
  ElMessage.success(`批量嵌入完成，成功${successCount}个，失败${failCount}个`)
  batchEmbed.value.assets = []
  loadAssets()
  loadLogs()
}

async function doBatchExtract() {
  if (batchExtract.value.assets.length === 0) {
    ElMessage.warning('请选择资产')
    return
  }

  batchExtract.value.loading = true
  let successCount = 0

  for (const assetId of batchExtract.value.assets) {
    try {
      await watermarkApi.extract(assetId)
      successCount++
    } catch {
      // ignore
    }
  }

  batchExtract.value.loading = false
  ElMessage.success(`批量提取完成，成功${successCount}个`)
  batchExtract.value.assets = []
  loadLogs()
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

onMounted(() => {
  loadAssets()
  loadLogs()
})
</script>

<style scoped>
.admin-watermark {
  padding: 0;
}
</style>