<template>
  <div class="downloads-page" :class="{ embedded }">
    <header class="page-head">
      <div>
        <h1 class="page-title">{{ embedded ? '下载台账' : '下载记录' }}</h1>
        <p class="page-subtitle">
          {{
            embedded
              ? '全平台授权资产的下载明细，用于授权履约与审计追溯。'
              : '查看你通过授权下载过的资产，以及对应的授权记录。'
          }}
        </p>
      </div>
      <router-link v-if="embedded" to="/admin" class="page-back-link">返回仪表盘</router-link>
    </header>

    <el-tabs v-if="!embedded && canViewLedger" v-model="activeScope" class="scope-tabs">
      <el-tab-pane label="我的下载" name="mine" />
      <el-tab-pane label="全平台台账" name="all" />
    </el-tabs>

    <section v-if="showSummary" class="summary-grid">
      <div class="summary-card">
        <span class="summary-label">累计下载</span>
        <strong class="summary-value">{{ summary.total ?? '—' }}</strong>
      </div>
      <div class="summary-card">
        <span class="summary-label">今日下载</span>
        <strong class="summary-value">{{ summary.today ?? '—' }}</strong>
      </div>
      <div class="summary-card">
        <span class="summary-label">涉及用户</span>
        <strong class="summary-value">{{ summary.users ?? '—' }}</strong>
      </div>
      <div class="summary-card">
        <span class="summary-label">涉及资产</span>
        <strong class="summary-value">{{ summary.assets ?? '—' }}</strong>
      </div>
    </section>

    <section class="filter-card">
      <el-input
        v-model="filters.keyword"
        placeholder="按资产编码或标题搜索"
        clearable
        class="filter-keyword"
        @keyup.enter="applyFilters"
      >
        <template #prefix
          ><el-icon><Search /></el-icon
        ></template>
      </el-input>
      <el-date-picker
        v-model="filters.dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        value-format="YYYY-MM-DD"
        class="filter-date"
      />
      <el-button type="primary" @click="applyFilters">查询</el-button>
      <el-button @click="resetFilters">重置</el-button>
    </section>

    <el-alert
      v-if="loadError"
      type="error"
      :closable="false"
      show-icon
      title="下载记录加载失败"
      class="load-error"
    >
      <el-button size="small" @click="loadRecords">重试</el-button>
    </el-alert>

    <el-skeleton v-else-if="loading" animated :rows="6" class="loading-block" />

    <template v-else>
      <el-table v-if="records.length" :data="records" stripe class="download-table">
        <el-table-column label="下载时间" width="160">
          <template #default="{ row }">
            <span class="mono">{{ formatDate(row.created_at, 'YYYY-MM-DD HH:mm') }}</span>
          </template>
        </el-table-column>
        <el-table-column label="资产" min-width="260">
          <template #default="{ row }">
            <router-link v-if="row.asset" :to="`/assets/${row.asset.id}`" class="asset-cell">
              <span class="asset-thumb">
                <img
                  v-if="row.asset.thumbnail_url && !failedThumbs[row.id]"
                  :src="row.asset.thumbnail_url"
                  alt=""
                  loading="lazy"
                  @error="markThumbFailed(row.id)"
                />
                <el-icon v-else><Picture /></el-icon>
              </span>
              <span class="asset-text">
                <strong>{{ row.asset.title }}</strong>
                <small class="mono">{{ row.asset.asset_code }}</small>
              </span>
            </router-link>
            <span v-else class="muted">资产已删除</span>
          </template>
        </el-table-column>
        <el-table-column v-if="scope === 'all'" label="下载用户" width="140">
          <template #default="{ row }">
            {{ row.user?.nickname || row.user?.username || '—' }}
          </template>
        </el-table-column>
        <el-table-column label="授权编号" min-width="190">
          <template #default="{ row }">
            <span v-if="row.license" class="mono">{{ row.license.license_code }}</span>
            <span v-else class="muted">{{ row.asset ? '所有者/管理员下载' : '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button
              v-if="row.asset"
              size="small"
              link
              type="primary"
              @click="$router.push(`/assets/${row.asset.id}`)"
            >
              查看资产
            </el-button>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-else description="暂无下载记录">
        <el-button type="primary" @click="$router.push('/assets')">去资产档案看看</el-button>
      </el-empty>

      <el-pagination
        v-if="total > 0"
        v-model:current-page="page"
        v-model:page-size="perPage"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        class="pagination"
        @size-change="loadRecords"
        @current-change="loadRecords"
      />

      <div v-if="records.length" class="mobile-list">
        <article v-for="row in records" :key="`m-${row.id}`" class="mobile-card">
          <header class="mobile-head">
            <span class="mono">{{ formatDate(row.created_at, 'YYYY-MM-DD HH:mm') }}</span>
            <span v-if="row.license" class="mobile-license mono">{{
              row.license.license_code
            }}</span>
          </header>
          <router-link v-if="row.asset" :to="`/assets/${row.asset.id}`" class="mobile-asset">
            {{ row.asset.title }}
            <small class="mono">{{ row.asset.asset_code }}</small>
          </router-link>
          <span v-else class="muted">资产已删除</span>
          <footer class="mobile-foot">
            <span v-if="scope === 'all'"
              >下载人：{{ row.user?.nickname || row.user?.username || '—' }}</span
            >
            <span v-else>{{ row.license ? '授权下载' : '所有者/管理员下载' }}</span>
          </footer>
        </article>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Picture, Search } from '@element-plus/icons-vue'
import { downloadApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'
import { formatDate } from '@/utils'

const route = useRoute()
const userStore = useUserStore()

const ADMIN_ROLES = ['admin', 'asset_admin', 'license_admin', 'adm1', 'adm2']
const embedded = computed(() => route.path.startsWith('/admin'))
const canViewLedger = computed(() => ADMIN_ROLES.includes(userStore.userRole))
const activeScope = ref('mine')
const scope = computed(() => (embedded.value ? 'all' : activeScope.value))
const showSummary = computed(() => scope.value === 'all')

const records = ref([])
const summary = reactive({ total: null, today: null, users: null, assets: null })
const loading = ref(false)
const loadError = ref(false)
const page = ref(1)
const perPage = ref(20)
const total = ref(0)
const filters = reactive({ keyword: '', dateRange: [] })
const failedThumbs = reactive({})

function markThumbFailed(id) {
  failedThumbs[id] = true
}

const appliedFilters = reactive({ keyword: '', start_date: '', end_date: '' })

function buildParams() {
  return {
    page: page.value,
    per_page: perPage.value,
    keyword: appliedFilters.keyword || undefined,
    start_date: appliedFilters.start_date || undefined,
    end_date: appliedFilters.end_date || undefined
  }
}

async function loadRecords() {
  loading.value = true
  loadError.value = false
  try {
    const response =
      scope.value === 'all'
        ? await downloadApi.ledger(buildParams())
        : await downloadApi.mine(buildParams())
    if (response.data?.code === 200) {
      const data = response.data.data || {}
      records.value = data.items || []
      total.value = data.total || 0
      if (scope.value === 'all' && data.summary) {
        Object.assign(summary, data.summary)
      }
    } else {
      loadError.value = true
    }
  } catch {
    loadError.value = true
    records.value = []
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  appliedFilters.keyword = filters.keyword.trim()
  appliedFilters.start_date = filters.dateRange?.[0] || ''
  appliedFilters.end_date = filters.dateRange?.[1] || ''
  page.value = 1
  loadRecords()
}

function resetFilters() {
  filters.keyword = ''
  filters.dateRange = []
  applyFilters()
}

watch(scope, () => {
  page.value = 1
  records.value = []
  loadRecords()
})

onMounted(loadRecords)
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.downloads-page {
  max-width: 1180px;
  margin: 0 auto;
  padding: 28px 24px 60px;

  &.embedded {
    max-width: none;
    padding: 0;
  }
}

.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.page-title {
  margin: 0;
  font-family: $font-display;
  font-size: 26px;
  color: $text-primary;
}

.page-subtitle {
  margin: 6px 0 0;
  font-size: 13px;
  color: $text-secondary;
}

.page-back-link {
  font-size: 13px;
  color: $primary-color;
}

.scope-tabs {
  margin-bottom: 8px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.summary-card {
  padding: 14px 16px;
  border: 1px solid $border-light;
  border-radius: $radius-md;
  background: $bg-card;
}

.summary-label {
  display: block;
  font-size: 12px;
  color: $text-placeholder;
}

.summary-value {
  display: block;
  margin-top: 4px;
  font-family: $font-mono;
  font-size: 24px;
  color: $text-primary;
}

.filter-card {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 14px 16px;
  margin-bottom: 16px;
  border: 1px solid $border-light;
  border-radius: $radius-md;
  background: $bg-card;
}

.filter-keyword {
  width: 260px;
}

.filter-date {
  width: 260px;
}

.load-error {
  margin-bottom: 16px;
}

.loading-block {
  padding: 20px;
  background: $bg-card;
  border: 1px solid $border-light;
  border-radius: $radius-md;
}

.download-table {
  width: 100%;
  background: $bg-card;
  border: 1px solid $border-light;
  border-radius: $radius-md;
}

.asset-cell {
  display: flex;
  align-items: center;
  gap: 10px;
  color: $text-primary;
  text-decoration: none;

  &:hover strong {
    color: $primary-color;
  }
}

.asset-thumb {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  flex: 0 0 40px;
  overflow: hidden;
  border-radius: $radius-sm;
  background: $bg-secondary;
  color: $text-placeholder;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.asset-text {
  display: flex;
  flex-direction: column;
  min-width: 0;

  strong {
    font-size: 13px;
    font-weight: 500;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  small {
    font-size: 11px;
    color: $text-placeholder;
  }
}

.mono {
  font-family: $font-mono;
  font-size: 12px;
}

.muted {
  font-size: 12px;
  color: $text-placeholder;
}

.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}

.mobile-list {
  display: none;
}

@media (max-width: 860px) {
  .downloads-page {
    padding: 20px 16px 40px;

    &.embedded {
      padding: 0;
    }
  }

  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .filter-keyword,
  .filter-date {
    width: 100%;
  }

  .download-table {
    display: none;
  }

  .mobile-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .mobile-card {
    padding: 14px;
    border: 1px solid $border-light;
    border-radius: $radius-md;
    background: $bg-card;
  }

  .mobile-head {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    font-size: 11px;
    color: $text-placeholder;
  }

  .mobile-license {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 50%;
  }

  .mobile-asset {
    display: flex;
    flex-direction: column;
    margin: 8px 0;
    font-size: 14px;
    font-weight: 500;
    color: $text-primary;
    text-decoration: none;

    small {
      margin-top: 2px;
      font-weight: 400;
      color: $text-placeholder;
    }
  }

  .mobile-foot {
    font-size: 12px;
    color: $text-secondary;
  }

  .pagination {
    justify-content: center;
  }
}
</style>
