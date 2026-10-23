<template>
  <div class="admin-assets">
    <header class="page-head">
      <div class="page-heading">
        <h1 class="page-title">资产管理</h1>
        <p class="page-subtitle">登记、检索与维护园林数字资产档案</p>
      </div>
      <div class="page-actions">
        <el-button plain :disabled="assets.length === 0" @click="exportCurrentPage">
          导出当前页
        </el-button>
        <el-button type="primary" @click="goToUpload">
          <el-icon><Upload /></el-icon>
          上传资产
        </el-button>
      </div>
    </header>

    <div class="content-card">
      <!-- 搜索 -->
      <el-form inline class="filter-form">
        <el-form-item>
          <el-input v-model="search.keyword" placeholder="搜索标题/编码" clearable />
        </el-form-item>
        <el-form-item>
          <el-select v-model="search.asset_type" placeholder="类型" clearable>
            <el-option label="影像" value="image" />
            <el-option label="模型" value="model" />
            <el-option label="矢量" value="vector" />
            <el-option label="文献" value="document" />
            <el-option label="视频" value="video" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-select v-model="search.status" placeholder="资产状态" clearable>
            <el-option label="草稿" value="draft" />
            <el-option label="待审核" value="pending" />
            <el-option label="已发布" value="published" />
            <el-option label="已驳回" value="rejected" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-select v-model="search.watermark_status" placeholder="水印状态" clearable>
            <el-option label="未嵌入" value="none" />
            <el-option label="已嵌入" value="embedded" />
            <el-option label="已验证" value="verified" />
            <el-option label="失败" value="failed" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-select v-model="search.chain_status" placeholder="存证状态" clearable>
            <el-option label="未存证" value="none" />
            <el-option label="存证中" value="pending" />
            <el-option label="已存证" value="confirmed" />
            <el-option label="失败" value="failed" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 批量操作 -->
      <div v-if="selectedRows.length" class="batch-bar">
        <span class="batch-count">已选 {{ selectedRows.length }} 件资产</span>
        <el-button
          v-if="canProcessAssets"
          size="small"
          type="primary"
          plain
          :loading="batchRunning === 'watermark'"
          :disabled="!!batchRunning"
          @click="bulkWatermark"
        >
          批量嵌水印
        </el-button>
        <el-button
          v-if="canProcessAssets"
          size="small"
          type="success"
          plain
          :loading="batchRunning === 'chain'"
          :disabled="!!batchRunning"
          @click="bulkChain"
        >
          批量上链
        </el-button>
        <el-button
          v-if="canApprove && pendingSelected.length"
          size="small"
          type="success"
          plain
          :loading="batchRunning === 'approve'"
          :disabled="!!batchRunning"
          @click="bulkApprove"
        >
          批量通过（{{ pendingSelected.length }}）
        </el-button>
        <el-button
          v-if="canApprove && pendingSelected.length"
          size="small"
          type="danger"
          plain
          :loading="batchRunning === 'reject'"
          :disabled="!!batchRunning"
          @click="bulkReject"
        >
          批量驳回
        </el-button>
        <el-button size="small" text :disabled="!!batchRunning" @click="clearSelection">取消选择</el-button>
      </div>

      <!-- 表格 -->
      <el-skeleton :loading="loading" animated :rows="8">
        <template #template>
          <div v-for="i in 8" :key="i" class="skeleton-row">
            <el-skeleton-item variant="text" style="width: 160px" />
            <el-skeleton-item variant="text" style="flex: 1" />
            <el-skeleton-item variant="text" style="width: 60px" />
            <el-skeleton-item variant="text" style="width: 60px" />
            <el-skeleton-item variant="text" style="width: 60px" />
            <el-skeleton-item variant="text" style="width: 80px" />
            <el-skeleton-item variant="text" style="width: 120px" />
          </div>
        </template>
        <template #default>
          <el-table
            ref="tableRef"
            :data="assets"
            stripe
            row-key="id"
            @selection-change="handleSelectionChange"
          >
            <el-table-column v-if="canProcessAssets" type="selection" width="44" />
            <el-table-column prop="asset_code" label="编码" width="220" class-name="cell-code" />
            <el-table-column label="标题" min-width="200">
              <template #default="{ row }">
                <div class="asset-title-cell">
                  <span class="asset-title-text">{{ row.title }}</span>
                  <span class="asset-title-sub">
                    {{ row.uploader_name || '-' }} · {{ formatDate(row.created_at) }}
                  </span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="asset_type" label="类型" width="70">
              <template #default="{ row }">
                <el-tag size="small">{{ getTypeName(row.asset_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag size="small" :type="getAssetStatus(row.status).type">
                  {{ getAssetStatus(row.status).label }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="watermark_status" label="水印" width="80">
              <template #default="{ row }">
                <el-tag size="small" :type="getWatermarkStatus(row.watermark_status).type">
                  {{ getWatermarkStatus(row.watermark_status).label }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="chain_status" label="存证" width="80">
              <template #default="{ row }">
                <el-tag size="small" :type="getChainStatus(row.chain_status).type">
                  {{ getChainStatus(row.chain_status).label }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="300">
              <template #default="{ row }">
                <div class="row-actions">
                  <el-button size="small" link type="primary" @click="viewDetail(row.id)">查看</el-button>
                  <el-button
                    v-if="['draft', 'rejected'].includes(row.status) && isOwner(row)"
                    size="small"
                    type="primary"
                    @click="submitPublish(row)"
                  >
                    {{ row.status === 'rejected' ? '重新提交' : '提交发布' }}
                  </el-button>
                  <template v-if="row.status === 'pending' && canApproveRow(row)">
                    <el-button size="small" type="success" @click="approveAsset(row)">通过</el-button>
                    <el-button size="small" type="danger" @click="rejectAsset(row)">驳回</el-button>
                  </template>
                  <span v-else-if="row.status === 'pending' && isOwner(row)" class="owner-hint">不能审核自己上传的资产</span>
                  <el-button
                    v-if="canProcessAssets"
                    size="small"
                    type="primary"
                    plain
                    :loading="actionState[row.id] === 'watermark'"
                    :disabled="!!actionState[row.id] || ['embedded', 'verified'].includes(row.watermark_status)"
                    @click="batchWatermark(row)"
                  >
                    嵌水印
                  </el-button>
                  <el-button
                    v-if="canProcessAssets"
                    size="small"
                    type="success"
                    plain
                    :loading="actionState[row.id] === 'chain'"
                    :disabled="!!actionState[row.id] || row.chain_status === 'confirmed' || !['embedded', 'verified'].includes(row.watermark_status)"
                    @click="batchChain(row)"
                  >
                    上链
                  </el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </template>
      </el-skeleton>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="perPage"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="loadAssets"
        @current-change="loadAssets"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import { parseBackendDate } from '@/utils'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload, Search } from '@element-plus/icons-vue'
import { assetApi, watermarkApi, blockchainApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'

// 可审核资产的管理员角色（与后端角色枚举保持一致）
const ASSET_APPROVER_ROLES = ['admin', 'asset_admin', 'adm1', 'adm2']

const WATERMARK_STATUS = {
  none: { label: '未嵌入', type: 'info' },
  pending: { label: '处理中', type: 'warning' },
  embedded: { label: '已嵌入', type: 'success' },
  verified: { label: '已验证', type: 'success' },
  failed: { label: '失败', type: 'danger' }
}

const CHAIN_STATUS = {
  none: { label: '未存证', type: 'info' },
  pending: { label: '存证中', type: 'warning' },
  confirmed: { label: '已存证', type: 'success' },
  failed: { label: '失败', type: 'danger' }
}

const ASSET_STATUS = {
  draft: { label: '草稿', type: 'info' },
  pending: { label: '待审核', type: 'warning' },
  published: { label: '已发布', type: 'success' },
  rejected: { label: '已驳回', type: 'danger' },
  archived: { label: '已归档', type: 'info' },
  deleted: { label: '已删除', type: 'danger' }
}

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const canApprove = computed(() => ASSET_APPROVER_ROLES.includes(userStore.userRole))
// 嵌水印/上链仅资产管理员与超管（审批员只参与发布审核）
const canProcessAssets = computed(() => ['admin', 'asset_admin'].includes(userStore.userRole))

function canApproveRow(row) {
  return canApprove.value && !isOwner(row)
}

const pendingSelected = computed(() =>
  selectedRows.value.filter(row => row.status === 'pending' && canApproveRow(row))
)

const loading = ref(false)
const actionState = reactive({})
const tableRef = ref(null)
const selectedRows = ref([])
const batchRunning = ref('')
const assets = ref([])
const page = ref(1)
const perPage = ref(20)
const total = ref(0)

const search = ref({
  keyword: '',
  asset_type: '',
  status: '',
  watermark_status: '',
  chain_status: ''
})

async function loadAssets() {
  loading.value = true
  try {
    const params = {
      page: page.value,
      per_page: perPage.value,
      ...search.value
    }
    const response = await assetApi.getList(params)
    if (response.data.code === 200) {
      assets.value = response.data.data.items
      total.value = response.data.data.total
    }
  } catch (error) {
    console.error('加载资产失败:', error)
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadAssets()
}

function goToUpload() {
  router.push('/assets/upload')
}

function isOwner(row) {
  const userId = userStore.user?.id
  if (userId === undefined || userId === null) return false
  return [row.uploader_id, row.creator_id, row.owner_id].includes(userId)
}

async function submitPublish(row) {
  try {
    const response = await assetApi.publish(row.id)
    if (response.data.code === 200) {
      ElMessage.success('已提交发布，等待管理员审核')
      loadAssets()
    } else {
      ElMessage.error(response.data.message || '提交发布失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '提交发布失败')
  }
}

async function approveAsset(row) {
  try {
    await ElMessageBox.confirm(`确认通过资产「${row.title}」的发布申请？`, '审核确认', {
      confirmButtonText: '通过',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  await handleApprove(row, 'approve')
}

async function rejectAsset(row) {
  let reason = ''
  try {
    const result = await ElMessageBox.prompt('请输入驳回原因（可选）', '驳回资产', {
      confirmButtonText: '确认驳回',
      cancelButtonText: '取消',
      inputPlaceholder: '驳回原因'
    })
    reason = result.value || ''
  } catch {
    return
  }
  await handleApprove(row, 'reject', reason)
}

async function handleApprove(row, action, reason = '') {
  try {
    const payload = { action }
    if (reason) payload.reason = reason
    const response = await assetApi.approve(row.id, payload)
    if (response.data.code === 200) {
      ElMessage.success(action === 'approve' ? '已通过审核' : '已驳回')
      loadAssets()
    } else {
      ElMessage.error(response.data.message || '审核失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '审核失败')
  }
}

function viewDetail(id) {
  router.push(`/assets/${id}`)
}

function handleSelectionChange(rows) {
  selectedRows.value = rows
}

function clearSelection() {
  tableRef.value?.clearSelection()
  selectedRows.value = []
}

async function bulkApprove() {
  if (!pendingSelected.value.length || batchRunning.value) return
  try {
    await ElMessageBox.confirm(
      `将一次通过 ${pendingSelected.value.length} 件待审资产，确定继续？`,
      '批量通过',
      { type: 'warning', confirmButtonText: '全部通过', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  batchRunning.value = 'approve'
  let ok = 0
  let failed = 0
  for (const row of pendingSelected.value) {
    try {
      const response = await assetApi.approve(row.id, { action: 'approve' })
      if (response.data?.code === 200) ok += 1
      else failed += 1
    } catch {
      failed += 1
    }
  }
  batchRunning.value = ''
  ElMessage.success(`批量审核完成：通过 ${ok} 件${failed ? `，失败 ${failed} 件` : ''}`)
  clearSelection()
  loadAssets()
}

async function bulkReject() {
  if (!pendingSelected.value.length || batchRunning.value) return
  let reason = ''
  try {
    const result = await ElMessageBox.prompt(
      `将一次驳回 ${pendingSelected.value.length} 件待审资产，可填写统一原因。`,
      '批量驳回',
      {
        confirmButtonText: '全部驳回',
        cancelButtonText: '取消',
        inputPlaceholder: '驳回原因（可选）'
      }
    )
    reason = result.value || ''
  } catch {
    return
  }
  batchRunning.value = 'reject'
  let ok = 0
  let failed = 0
  for (const row of pendingSelected.value) {
    try {
      const response = await assetApi.approve(row.id, {
        action: 'reject',
        reason
      })
      if (response.data?.code === 200) ok += 1
      else failed += 1
    } catch {
      failed += 1
    }
  }
  batchRunning.value = ''
  ElMessage.success(`批量审核完成：驳回 ${ok} 件${failed ? `，失败 ${failed} 件` : ''}`)
  clearSelection()
  loadAssets()
}

function exportCurrentPage() {
  const headers = [
    '资产编码', '标题', '类型', '格式', '状态', '水印状态', '存证状态',
    '所属园林', '上传者', '浏览', '下载', '创建时间'
  ]
  const rows = assets.value.map(row => [
    row.asset_code,
    row.title,
    row.asset_type,
    row.file_format,
    ASSET_STATUS[row.status]?.label || row.status,
    WATERMARK_STATUS[row.watermark_status]?.label || row.watermark_status,
    CHAIN_STATUS[row.chain_status]?.label || row.chain_status,
    row.garden_name || '',
    row.uploader_name || row.creator_name || '',
    row.view_count || 0,
    row.download_count || 0,
    row.created_at || ''
  ])
  const csv = [headers, ...rows].map(line =>
    line.map(value => `"${String(value ?? '').replace(/"/g, '""')}"`).join(',')
  ).join('\n')
  const blob = new Blob(
    [String.fromCharCode(0xFEFF) + csv],
    { type: 'text/csv;charset=utf-8' }
  )
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `assets-${new Date().toISOString().slice(0, 10)}.csv`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

async function batchWatermark(row) {
  if (actionState[row.id]) return
  try {
    await ElMessageBox.confirm(
      `确定对「${row.title}」嵌入水印？水印会写入资产文件，操作不可撤销。`,
      '确认嵌入水印',
      { type: 'warning', confirmButtonText: '嵌入', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  actionState[row.id] = 'watermark'
  try {
    const response = await watermarkApi.embed(row.id)
    if (response.data.code === 200) {
      ElMessage.success('水印嵌入成功')
      loadAssets()
    } else {
      ElMessage.error(response.data.message || '水印嵌入失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '水印嵌入失败')
  } finally {
    delete actionState[row.id]
  }
}

async function batchChain(row) {
  if (actionState[row.id]) return
  try {
    await ElMessageBox.confirm(
      `确定对「${row.title}」上链存证？存证记录写入后不可撤销。`,
      '确认上链存证',
      { type: 'warning', confirmButtonText: '上链', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  actionState[row.id] = 'chain'
  try {
    const response = await blockchainApi.register(row.id)
    if (response.data.code === 200) {
      ElMessage.success('上链存证成功')
      loadAssets()
    } else {
      ElMessage.error(response.data.message || '上链存证失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '上链存证失败')
  } finally {
    delete actionState[row.id]
  }
}

async function bulkWatermark() {
  if (batchRunning.value) return
  const targets = selectedRows.value.filter(
    row => !['embedded', 'verified'].includes(row.watermark_status)
  )
  if (!targets.length) {
    ElMessage.info('所选资产都已完成水印嵌入')
    return
  }
  try {
    await ElMessageBox.confirm(
      `将对 ${targets.length} 件资产嵌入水印，操作不可撤销。是否继续？`,
      '批量嵌入水印',
      { type: 'warning', confirmButtonText: '开始处理', cancelButtonText: '取消' }
    )
  } catch {
    return
  }

  batchRunning.value = 'watermark'
  let success = 0
  let failed = 0
  for (const row of targets) {
    actionState[row.id] = 'watermark'
    try {
      const response = await watermarkApi.embed(row.id)
      if (response.data?.code === 200) success += 1
      else failed += 1
    } catch {
      failed += 1
    } finally {
      delete actionState[row.id]
    }
  }
  batchRunning.value = ''
  ElMessage[failed ? 'warning' : 'success'](
    `水印处理完成：成功 ${success} 件${failed ? `，失败 ${failed} 件` : ''}`
  )
  clearSelection()
  loadAssets()
}

async function bulkChain() {
  if (batchRunning.value) return
  const targets = selectedRows.value.filter(
    row => ['embedded', 'verified'].includes(row.watermark_status)
      && row.chain_status !== 'confirmed'
  )
  if (!targets.length) {
    ElMessage.info('所选资产中没有可上链的资产（需先完成水印嵌入）')
    return
  }
  try {
    await ElMessageBox.confirm(
      `将对 ${targets.length} 件资产上链存证，存证记录不可撤销。是否继续？`,
      '批量上链存证',
      { type: 'warning', confirmButtonText: '开始处理', cancelButtonText: '取消' }
    )
  } catch {
    return
  }

  batchRunning.value = 'chain'
  let success = 0
  let failed = 0
  for (const row of targets) {
    actionState[row.id] = 'chain'
    try {
      const response = await blockchainApi.register(row.id)
      if (response.data?.code === 200) success += 1
      else failed += 1
    } catch {
      failed += 1
    } finally {
      delete actionState[row.id]
    }
  }
  batchRunning.value = ''
  ElMessage[failed ? 'warning' : 'success'](
    `上链处理完成：成功 ${success} 件${failed ? `，失败 ${failed} 件` : ''}`
  )
  clearSelection()
  loadAssets()
}

function getTypeName(type) {
  const map = { image: '影像', model: '模型', vector: '矢量', document: '文献', video: '视频' }
  return map[type] || type
}

function getWatermarkStatus(status) {
  return WATERMARK_STATUS[status] || { label: status || '-', type: 'info' }
}

function getChainStatus(status) {
  return CHAIN_STATUS[status] || { label: status || '-', type: 'info' }
}

function getAssetStatus(status) {
  return ASSET_STATUS[status] || { label: status || '-', type: 'info' }
}

function formatDate(dateStr) {
  const date = parseBackendDate(dateStr)
  return date ? date.toLocaleDateString('zh-CN') : ''
}

onMounted(() => {
  if (route.query.status && ['draft', 'pending', 'published', 'rejected'].includes(route.query.status)) {
    search.value.status = route.query.status
  }
  loadAssets()
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.admin-assets {
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
}

.batch-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: $spacing-md;
  padding: 10px 14px;
  border: 1px solid rgba(47, 107, 90, 0.25);
  border-radius: $radius-md;
  background: rgba(47, 107, 90, 0.06);

  .batch-count {
    margin-right: 6px;
    font-size: 13px;
    font-weight: 500;
    color: $primary-color;
  }
}

// ========== 筛选行 ==========
.filter-form {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-md;
  margin-bottom: $spacing-lg;

  :deep(.el-form-item) {
    margin: 0;
  }

  :deep(.el-input) {
    width: 220px;
  }

  :deep(.el-select) {
    width: 150px;
  }
}

// 按钮内图标与文字间距
:deep(.el-button > span) {
  gap: 6px;
  align-items: center;
}

.skeleton-row {
  display: flex;
  gap: $spacing-lg;
  padding: 14px 0;
  border-bottom: 1px solid $border-light;
}

.row-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;

  :deep(.el-button + .el-button) {
    margin-left: 0;
  }
}

.owner-hint {
  font-size: 11px;
  color: $text-placeholder;
}

// 台账编码使用等宽字体
:deep(.cell-code) {
  font-family: $font-mono;
  font-size: 12px;
  color: $text-secondary;
  font-variant-numeric: tabular-nums;
}

.asset-title-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.asset-title-text {
  font-weight: 500;
  color: $text-primary;
}

.asset-title-sub {
  font-size: 12px;
  color: $text-secondary;
}

:deep(.el-pagination) {
  margin-top: $spacing-xl;
  justify-content: center;
}

// ========== 响应式 ==========
@media (max-width: 768px) {
  .admin-assets {
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

  .filter-form {
    :deep(.el-form-item) {
      width: 100%;
    }

    :deep(.el-input),
    :deep(.el-select) {
      width: 100%;
    }

    :deep(.el-button) {
      width: 100%;
    }
  }

  :deep(.el-pagination) {
    flex-wrap: wrap;
    row-gap: $spacing-sm;
  }
}
</style>
