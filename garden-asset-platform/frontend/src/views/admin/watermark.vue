<template>
  <div class="admin-watermark">
    <header class="page-head">
      <div class="page-heading">
        <h1 class="page-title">水印处理管理</h1>
        <p class="page-subtitle">为园林数字资产嵌入与提取隐形水印，留存操作记录</p>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="refreshAll">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </header>

    <!-- 批量处理 -->
    <div class="content-card">
      <div class="batch-grid">
        <section class="batch-panel">
          <h2 class="card-title">批量嵌入水印</h2>
          <el-form label-width="80px" class="panel-form">
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
            <el-form-item>
              <span class="algorithm-hint">算法由后端按资产类型自动选择：影像使用 DCT/QIM，矢量使用坐标扰动。</span>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="batchEmbed.loading" @click="doBatchEmbed">
                开始嵌入
              </el-button>
            </el-form-item>
          </el-form>
        </section>

        <section class="batch-panel">
          <h2 class="card-title">批量提取水印</h2>
          <el-form label-width="80px" class="panel-form">
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
              <el-button type="primary" :loading="batchExtract.loading" @click="doBatchExtract">
                开始提取
              </el-button>
            </el-form-item>
          </el-form>
        </section>
      </div>
    </div>

    <!-- 水印记录 -->
    <div class="content-card">
      <div class="card-head">
        <h2 class="card-title">水印操作记录</h2>
      </div>
      <el-table :data="watermarkLogs" v-loading="logsLoading" stripe>
        <el-table-column prop="asset_code" label="资产编码" width="180" class-name="cell-code" />
        <el-table-column prop="asset_title" label="资产标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="operation" label="操作类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.operation === 'embed' ? 'success' : 'warning'" size="small">
              {{ row.operation === 'embed' ? '嵌入' : '提取' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="watermark_id" label="水印ID" width="180" class-name="cell-code" />
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
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
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
    // 后端 watermark_status 枚举：none / embedded / verified / failed
    // 待嵌入只取 none；可提取的资产包括 embedded 与 verified
    const [pendingRes, embeddedRes, verifiedRes] = await Promise.all([
      assetApi.getList({ watermark_status: 'none', per_page: 100 }),
      assetApi.getList({ watermark_status: 'embedded', per_page: 100 }),
      assetApi.getList({ watermark_status: 'verified', per_page: 100 })
    ])

    if (pendingRes.data?.code === 200) {
      const items = pendingRes.data.data.items || []
      // 只展示支持水印的影像与矢量资产，避免批量操作必然失败
      pendingAssets.value = items.filter(asset =>
        ['image', 'vector'].includes(asset.asset_type)
      )
    }

    const embeddedItems = []
    for (const res of [embeddedRes, verifiedRes]) {
      if (res.data?.code === 200) {
        embeddedItems.push(...(res.data.data.items || []))
      }
    }
    // 两个下拉的数据源不同，且合并时去重
    const seen = new Set()
    embeddedAssets.value = embeddedItems.filter(asset => {
      if (seen.has(asset.id)) return false
      seen.add(asset.id)
      return true
    })
  } catch (error) {
    console.error('加载资产失败:', error)
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

function refreshAll() {
  loadAssets()
  loadLogs()
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
      const response = await watermarkApi.embed(assetId)
      if (response.data?.code === 200) {
        successCount++
      } else {
        failCount++
      }
    } catch {
      failCount++
    }
  }

  batchEmbed.value.loading = false
  const message = `批量嵌入完成，成功${successCount}个，失败${failCount}个`
  if (failCount > 0) {
    ElMessage.warning(message)
  } else {
    ElMessage.success(message)
  }
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
  let failCount = 0

  for (const assetId of batchExtract.value.assets) {
    try {
      const response = await watermarkApi.extract(assetId)
      if (response.data?.code === 200) {
        successCount++
      } else {
        failCount++
      }
    } catch {
      failCount++
    }
  }

  batchExtract.value.loading = false
  const message = `批量提取完成，成功${successCount}个，失败${failCount}个`
  if (failCount > 0) {
    ElMessage.warning(message)
  } else {
    ElMessage.success(message)
  }
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

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.admin-watermark {
  min-height: 100%;
  padding: 24px 28px 32px;
}

// ========== 页面头部 ==========
.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: $spacing-lg;
  margin-bottom: $spacing-xl;

  .page-title {
    font-family: $font-display;
    font-size: 22px;
    font-weight: $font-weight-semibold;
    line-height: $line-height-tight;
    color: $text-primary;
    letter-spacing: 0.01em;
  }

  .page-subtitle {
    margin-top: 6px;
    font-size: 13px;
    color: $text-secondary;
  }
}

.page-actions {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  flex-shrink: 0;
}

// ========== 内容卡片 ==========
.content-card {
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
  box-shadow: $shadow-sm;
  padding: $spacing-xl;

  & + & {
    margin-top: $spacing-xl;
  }
}

.card-title {
  font-family: $font-display;
  font-size: 16px;
  font-weight: $font-weight-semibold;
  color: $text-primary;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: $spacing-md;
  margin-bottom: $spacing-lg;
}

// ========== 批量处理双栏 ==========
.batch-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: $spacing-2xl;
}

.batch-panel {
  min-width: 0;

  .card-title {
    margin-bottom: $spacing-lg;
  }

  & + & {
    border-left: 1px solid $border-light;
    padding-left: $spacing-2xl;
  }
}

.panel-form {
  :deep(.el-select) {
    width: 100%;
  }
}

// 按钮内图标与文字间距
:deep(.el-button > span) {
  gap: 6px;
  align-items: center;
}

// 台账编码使用等宽字体
:deep(.cell-code) {
  font-family: $font-mono;
  font-size: 12px;
  color: $text-secondary;
  font-variant-numeric: tabular-nums;
}

.algorithm-hint {
  font-size: 12px;
  line-height: 1.7;
  color: $text-placeholder;
}

// ========== 响应式 ==========
@media (max-width: 768px) {
  .admin-watermark {
    padding: 16px;
  }

  .page-head {
    flex-direction: column;
    align-items: flex-start;
    gap: $spacing-md;
  }

  .content-card {
    padding: 16px;
  }

  .batch-grid {
    grid-template-columns: 1fr;
    gap: $spacing-xl;
  }

  .batch-panel + .batch-panel {
    border-left: none;
    padding-left: 0;
    border-top: 1px solid $border-light;
    padding-top: $spacing-xl;
  }
}
</style>
