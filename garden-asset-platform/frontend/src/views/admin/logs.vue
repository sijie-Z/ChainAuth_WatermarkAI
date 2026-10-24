<template>
  <div class="admin-logs">
    <header class="page-head">
      <div>
        <h1 class="page-title">操作日志</h1>
        <p class="page-subtitle">上传、水印、存证、授权与用户管理的审计记录</p>
      </div>
      <div class="page-actions">
        <el-button :loading="integrityLoading" @click="checkIntegrity">校验日志完整性</el-button>
        <el-button :loading="loading" @click="loadLogs">刷新</el-button>
      </div>
    </header>

    <section
      v-if="integrity"
      class="integrity-card"
      :class="integrity.status"
      aria-live="polite"
    >
      <el-icon class="integrity-icon">
        <CircleCheck v-if="integrity.status === 'ok'" />
        <WarningFilled v-else />
      </el-icon>
      <div class="integrity-copy">
        <strong>{{ integrity.label }}</strong>
        <p>
          共 {{ integrity.total }} 条 · 已签名 {{ integrity.signed }} · 有效 {{ integrity.valid }} ·
          异常 {{ integrity.invalid }} · 未签名 {{ integrity.unsigned }}
        </p>
        <p v-if="integrity.samples?.length" class="integrity-samples">
          异常日志：
          <span v-for="sample in integrity.samples" :key="sample.id">
            #{{ sample.id }} {{ actionName(sample.action) }}
          </span>
        </p>
        <p v-if="integrity.status === 'unsigned'" class="integrity-hint">
          历史日志尚未签名，可由管理员运行 <code>flask audit rebuild --yes</code> 补签。
        </p>
      </div>
      <span class="integrity-time">{{ formatTime(integrity.generated_at) }}</span>
    </section>

    <section class="filter-card">
      <el-input
        v-model="filters.keyword"
        placeholder="搜索操作描述"
        clearable
        style="width: 220px"
        @keyup.enter="handleSearch"
      />
      <el-select v-model="filters.module" placeholder="全部模块" clearable style="width: 140px">
        <el-option label="资产" value="asset" />
        <el-option label="水印" value="watermark" />
        <el-option label="存证" value="blockchain" />
        <el-option label="授权" value="license" />
        <el-option label="侵权线索" value="infringement" />
        <el-option label="认证" value="auth" />
        <el-option label="用户" value="user" />
      </el-select>
      <el-select v-model="filters.status" placeholder="全部结果" clearable style="width: 120px">
        <el-option label="成功" value="success" />
        <el-option label="失败" value="failed" />
      </el-select>
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        value-format="YYYY-MM-DD"
        style="width: 260px"
      />
      <el-button type="primary" @click="handleSearch">查询</el-button>
      <el-button @click="resetFilters">重置</el-button>
    </section>

    <section class="table-card">
      <el-table v-loading="loading" :data="logs" stripe row-key="id">
        <el-table-column prop="created_at" label="时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="user_name" label="操作人" width="110">
          <template #default="{ row }">
            {{ row.user_name || '系统' }}
            <span v-if="row.user_role" class="role-hint">{{ roleName(row.user_role) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="module" label="模块" width="100">
          <template #default="{ row }">{{ moduleName(row.module) }}</template>
        </el-table-column>
        <el-table-column prop="action" label="动作" width="120">
          <template #default="{ row }">{{ actionName(row.action) }}</template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="260" show-overflow-tooltip />
        <el-table-column prop="status" label="结果" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 'success' ? 'success' : 'danger'">
              {{ row.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="签名" width="86">
          <template #default="{ row }">
            <el-tag size="small" :type="row.signed ? 'success' : 'info'" effect="plain">
              {{ row.signed ? '已签名' : '未签名' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="ip_address" label="IP" width="130" />
      </el-table>

      <div v-if="!loading && logs.length === 0" class="empty-logs">
        <el-empty description="没有匹配的操作记录" :image-size="72" />
      </div>

      <div class="pagination-section">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="perPage"
          :total="total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          background
          @size-change="loadLogs"
          @current-change="loadLogs"
        />
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { parseBackendDate } from '@/utils'
import { ElMessage } from 'element-plus'
import { CircleCheck, WarningFilled } from '@element-plus/icons-vue'
import { logApi } from '@/api/modules'

const logs = ref([])
const loading = ref(false)
const page = ref(1)
const perPage = ref(20)
const total = ref(0)
const dateRange = ref([])
const integrity = ref(null)
const integrityLoading = ref(false)

const filters = reactive({
  keyword: '',
  module: '',
  status: '',
  action: ''
})

const MODULE_NAMES = {
  asset: '资产',
  watermark: '水印',
  blockchain: '存证',
  license: '授权',
  infringement: '侵权线索',
  auth: '认证',
  user: '用户'
}

const ACTION_NAMES = {
  login: '登录',
  logout: '退出',
  upload: '上传',
  update: '更新',
  delete: '删除',
  download: '下载',
  embed: '嵌入水印',
  watermark_embed: '嵌入水印',
  extract: '提取水印',
  register: '上链',
  approve: '审批',
  reject: '驳回',
  license_apply: '提交申请',
  license_cancel: '撤回申请',
  infringement_report: '提交侵权线索',
  infringement_start: '受理侵权线索',
  infringement_confirm: '确认侵权',
  infringement_reject: '驳回线索',
  export_evidence_package: '导出证据包',
  upload_version: '上传新版本',
  restore_version: '恢复历史版本'
}

const ROLE_NAMES = {
  admin: '管理员',
  asset_admin: '资产管理员',
  license_admin: '授权管理员',
  adm1: '一级审批',
  adm2: '二级审批',
  user: '用户'
}

function moduleName(value) {
  return MODULE_NAMES[value] || value || '-'
}

function actionName(value) {
  return ACTION_NAMES[value] || value || '-'
}

function roleName(value) {
  return ROLE_NAMES[value] || value
}

function formatTime(value) {
  const date = parseBackendDate(value)
  return date ? date.toLocaleString('zh-CN') : '-'
}

function handleSearch() {
  page.value = 1
  loadLogs()
}

function resetFilters() {
  filters.keyword = ''
  filters.module = ''
  filters.status = ''
  dateRange.value = []
  page.value = 1
  loadLogs()
}

async function loadLogs() {
  loading.value = true
  try {
    const params = {
      page: page.value,
      per_page: perPage.value,
      keyword: filters.keyword || undefined,
      module: filters.module || undefined,
      status: filters.status || undefined
    }
    if (Array.isArray(dateRange.value) && dateRange.value.length === 2) {
      params.date_from = `${dateRange.value[0]}T00:00:00`
      params.date_to = `${dateRange.value[1]}T23:59:59`
    }
    const response = await logApi.getList(params)
    if (response.data?.code === 200) {
      logs.value = response.data.data?.items || []
      total.value = response.data.data?.total || 0
    } else {
      ElMessage.error(response.data?.message || '日志加载失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '日志加载失败')
  } finally {
    loading.value = false
  }
}

async function checkIntegrity() {
  if (integrityLoading.value) return
  integrityLoading.value = true
  try {
    const response = await logApi.integrity()
    if (response.data?.code === 200) {
      integrity.value = response.data.data
      const status = integrity.value.status
      if (status === 'ok') {
        ElMessage.success('全部日志签名有效')
      } else if (status === 'invalid') {
        ElMessage.error(integrity.value.label)
      } else {
        ElMessage.warning(integrity.value.label)
      }
    } else {
      ElMessage.error(response.data?.message || '日志完整性校验失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '日志完整性校验失败')
  } finally {
    integrityLoading.value = false
  }
}

onMounted(loadLogs)
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.admin-logs {
  min-height: 100%;
  padding: 24px 28px 32px;
}

.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: $spacing-lg;
  margin-bottom: $spacing-xl;

  .page-title {
    font-family: $font-display;
    font-size: 22px;
    font-weight: 600;
    color: $text-primary;
    margin-bottom: 4px;
  }

  .page-subtitle {
    font-size: 13px;
    color: $text-secondary;
  }
}

.page-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.integrity-card {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  margin-bottom: $spacing-lg;
  padding: 16px 18px;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-md;

  &.ok {
    border-color: $primary-color;

    .integrity-icon { color: $primary-color; }
  }

  &.invalid {
    border-color: $accent-color;

    .integrity-icon { color: $accent-color; }
  }

  &.unsigned {
    border-color: $border-dark;

    .integrity-icon { color: $accent-color; }
  }

  &.unavailable {
    .integrity-icon { color: $text-placeholder; }
  }
}

.integrity-icon {
  flex-shrink: 0;
  margin-top: 2px;
  font-size: 24px;
}

.integrity-copy {
  min-width: 0;
  flex: 1;

  strong {
    display: block;
    margin-bottom: 4px;
    font-family: $font-display;
    font-size: 15px;
    color: $text-primary;
  }

  p {
    margin: 2px 0;
    font-size: 12px;
    line-height: 1.6;
    color: $text-secondary;
  }

  code {
    padding: 1px 4px;
    background: $bg-secondary;
    border-radius: 2px;
    font-family: $font-mono;
    font-size: 11px;
  }
}

.integrity-samples {
  span + span {
    margin-left: 10px;
  }
}

.integrity-time {
  flex-shrink: 0;
  font-family: $font-mono;
  font-size: 10px;
  color: $text-placeholder;
}

.filter-card {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  padding: 16px;
  margin-bottom: $spacing-lg;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-md;
}

.table-card {
  padding: 16px;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  box-shadow: $shadow-sm;
}

.role-hint {
  display: block;
  font-size: 10px;
  color: $text-placeholder;
}

.empty-logs {
  padding: 32px 0;
}

.pagination-section {
  display: flex;
  justify-content: center;
  margin-top: $spacing-xl;
}

@media (max-width: 768px) {
  .admin-logs {
    padding: 16px;
  }

  .page-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .filter-card {
    :deep(.el-input),
    :deep(.el-select),
    :deep(.el-date-editor) {
      width: 100% !important;
    }
  }
}
</style>
