<template>
  <div class="my-assets-page">
    <header class="page-bar">
      <router-link to="/assets" class="page-back">
        <el-icon><ArrowLeft /></el-icon>
        返回资产档案
      </router-link>
      <h1 class="page-title">我的资产</h1>
      <span class="page-count">共 {{ total }} 件</span>
      <el-button type="primary" class="page-action" @click="$router.push('/assets/upload')">
        <el-icon><Upload /></el-icon>
        上传资产
      </el-button>
    </header>

    <div class="status-tabs">
      <el-radio-group v-model="status" @change="handleFilter">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="draft">草稿</el-radio-button>
        <el-radio-button value="pending">待审核</el-radio-button>
        <el-radio-button value="published">已发布</el-radio-button>
        <el-radio-button value="rejected">已驳回</el-radio-button>
        <el-radio-button value="deleted">回收站</el-radio-button>
      </el-radio-group>
    </div>

    <div v-if="loading" class="assets-grid">
      <div v-for="i in 8" :key="`my-skeleton-${i}`" class="my-card my-skeleton">
        <div class="my-thumb skeleton"></div>
        <div class="my-body">
          <div class="skeleton" style="width: 70%; height: 16px"></div>
          <div class="skeleton" style="width: 45%; height: 12px; margin-top: 8px"></div>
        </div>
      </div>
    </div>

    <el-empty v-else-if="loadError" description="资产加载失败">
      <el-button type="primary" @click="loadAssets">重试</el-button>
    </el-empty>

    <el-empty v-else-if="assets.length === 0" :description="emptyDescription">
      <el-button v-if="status !== 'deleted'" type="primary" @click="$router.push('/assets/upload')">上传第一件资产</el-button>
    </el-empty>

    <template v-else>
      <div class="assets-grid">
        <article v-for="item in assets" :key="item.id" class="my-card" :class="{ 'is-deleted': item.status === 'deleted' }">
          <div
            class="my-thumb"
            :role="item.status === 'deleted' ? undefined : 'button'"
            :tabindex="item.status === 'deleted' ? undefined : 0"
            :aria-label="item.status === 'deleted' ? undefined : `查看资产 ${item.title}`"
            @click="openAsset(item)"
            @keydown.enter.prevent="openAsset(item)"
            @keydown.space.prevent="openAsset(item)"
          >
            <div v-if="item.status === 'deleted'" class="deleted-thumb">
              <el-icon :size="34"><Delete /></el-icon>
              <span>已移入回收站</span>
            </div>
            <img v-else :src="getThumbnail(item)" :alt="item.title" loading="lazy" @error="onImageError" />
            <StatusTag :status="item.status" kind="asset" class="my-status" />
          </div>
          <div class="my-body">
            <h2
              class="my-title"
              :role="item.status === 'deleted' ? undefined : 'button'"
              :tabindex="item.status === 'deleted' ? undefined : 0"
              @click="openAsset(item)"
              @keydown.enter.prevent="openAsset(item)"
              @keydown.space.prevent="openAsset(item)"
            >{{ item.title }}</h2>
            <p class="my-code mono">{{ item.asset_code }}</p>
            <p v-if="item.status === 'rejected' && item.reject_reason" class="reject-reason">
              驳回原因：{{ item.reject_reason }}
            </p>
            <div class="my-meta">
              <span>{{ item.status === 'deleted' ? `删除于 ${formatDate(item.deleted_at)}` : formatDate(item.created_at) }}</span>
              <span v-if="item.status !== 'deleted'">{{ item.view_count || 0 }} 次浏览</span>
              <span v-else>删除前：{{ previousStatusText(item.previous_status) }}</span>
            </div>
            <div class="my-actions">
              <el-button v-if="item.status !== 'deleted'" size="small" link type="primary" @click="openAsset(item.id)">查看</el-button>
              <el-button
                v-if="item.status === 'deleted'"
                size="small"
                link
                type="warning"
                :loading="restoringId === item.id"
                @click="restoreAsset(item)"
              >恢复</el-button>
              <el-button
                v-if="['draft', 'rejected'].includes(item.status)"
                size="small"
                link
                type="success"
                :loading="publishingId === item.id"
                :disabled="['image', 'vector'].includes(item.asset_type) && !['embedded', 'verified'].includes(item.watermark_status)"
                :title="['image', 'vector'].includes(item.asset_type) && !['embedded', 'verified'].includes(item.watermark_status) ? '请先在资产详情完成水印嵌入' : '提交发布'"
                @click="submitPublish(item)"
              >
                {{ item.status === 'rejected' ? '重新提交' : '提交发布' }}
              </el-button>
              <el-button
                v-if="['draft', 'rejected'].includes(item.status)"
                size="small"
                link
                type="danger"
                :loading="deletingId === item.id"
                @click="removeAsset(item)"
              >
                删除
              </el-button>
            </div>
          </div>
        </article>
      </div>

      <div class="pagination-section">
        <el-pagination
          v-model:current-page="page"
          :page-size="perPage"
          :total="total"
          layout="total, prev, pager, next"
          background
          @current-change="loadAssets"
        />
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Delete, Upload } from '@element-plus/icons-vue'
import { assetApi } from '@/api/modules'
import { parseBackendDate } from '@/utils'

const router = useRouter()
const assets = ref([])
const loading = ref(true)
const loadError = ref(false)
const page = ref(1)
const perPage = ref(12)
const total = ref(0)
const status = ref('')
const publishingId = ref('')
const deletingId = ref('')
const restoringId = ref('')
let assetsRequestSeq = 0

const emptyDescription = computed(() => {
  if (status.value === 'deleted') return '回收站是空的'
  return status.value ? '该状态下暂无资产' : '还没有上传过资产'
})

async function loadAssets() {
  const requestId = ++assetsRequestSeq
  loading.value = true
  loadError.value = false
  try {
    const response = await assetApi.my({
      page: page.value,
      per_page: perPage.value,
      status: status.value || undefined
    })
    if (requestId !== assetsRequestSeq) return
    if (response.data?.code === 200) {
      assets.value = response.data.data?.items || []
      total.value = response.data.data?.total || 0
    } else {
      loadError.value = true
    }
  } catch {
    if (requestId === assetsRequestSeq) loadError.value = true
  } finally {
    if (requestId === assetsRequestSeq) loading.value = false
  }
}

function handleFilter() {
  page.value = 1
  loadAssets()
}

function openAsset(item) {
  if (item?.status === 'deleted') return
  const id = typeof item === 'string' ? item : item?.id
  if (id) router.push(`/assets/${id}`)
}

function getThumbnail(item) {
  return `/api/assets/${item.id}/thumbnail?size=card&v=${item.current_version_no || 1}`
}

function onImageError(event) {
  const img = event?.target
  if (!img || img.dataset.fallbackApplied) return
  img.dataset.fallbackApplied = '1'
  img.src = `data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="300"%3E%3Crect fill="%232f6b5a" width="400" height="300"/%3E%3Ctext x="200" y="160" text-anchor="middle" fill="white" font-size="28"%3E%E5%9B%AD%E6%9E%97%3C/text%3E%3C/svg%3E`
}

async function submitPublish(item) {
  publishingId.value = item.id
  try {
    const response = await assetApi.publish(item.id)
    if (response.data?.code === 200) {
      ElMessage.success('已提交发布，等待管理员审核')
      loadAssets()
    } else {
      ElMessage.error(response.data?.message || '提交发布失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '提交发布失败')
  } finally {
    publishingId.value = ''
  }
}

async function removeAsset(item) {
  try {
    await ElMessageBox.confirm(
      `确定删除《${item.title}》？资产会移入回收站，有效授权将被撤销；你可以在“回收站”中恢复为草稿。`,
      '删除资产',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  deletingId.value = item.id
  try {
    const response = await assetApi.delete(item.id)
    if (response.data?.code === 200) {
      ElMessage.success('资产已移入回收站，可在“回收站”中恢复')
      if (assets.value.length === 1 && page.value > 1) {
        page.value -= 1
      }
      loadAssets()
    } else {
      ElMessage.error(response.data?.message || '删除失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '删除失败')
  } finally {
    deletingId.value = ''
  }
}

async function restoreAsset(item) {
  try {
    await ElMessageBox.confirm(
      `恢复《${item.title}》后会回到草稿状态，原授权不会自动恢复，需要重新水印/存证并提交发布。`,
      '恢复资产',
      { type: 'warning', confirmButtonText: '恢复', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  restoringId.value = item.id
  try {
    const response = await assetApi.restore(item.id)
    if (response.data?.code === 200) {
      ElMessage.success('资产已恢复为草稿，请重新水印/存证并提交发布')
      if (assets.value.length === 1 && page.value > 1) {
        page.value -= 1
      }
      loadAssets()
    } else {
      ElMessage.error(response.data?.message || '恢复失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '恢复失败')
  } finally {
    restoringId.value = ''
  }
}

function formatDate(value) {
  const date = parseBackendDate(value)
  return date ? date.toLocaleDateString('zh-CN') : '-'
}

function previousStatusText(value) {
  return { draft: '草稿', pending: '待审核', published: '已发布', rejected: '已驳回' }[value] || '未记录'
}

onMounted(loadAssets)
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.my-assets-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: $spacing-2xl $spacing-3xl $spacing-4xl;
  min-height: 100vh;
  background: $bg-primary;
}

.page-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: $spacing-md;
  padding-bottom: $spacing-md;
  margin-bottom: $spacing-lg;
  border-bottom: 1px solid $border-light;
}

.page-back {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: $font-size-sm;
  color: $text-secondary;

  &:hover {
    color: $primary-dark;
  }
}

.page-title {
  font-family: $font-display;
  font-size: 23px;
  font-weight: 600;
  color: $text-primary;
}

.page-count {
  margin-left: auto;
  font-size: 12px;
  color: $text-placeholder;
}

.page-action {
  margin-left: 8px;
}

.status-tabs {
  margin-bottom: $spacing-lg;
}

.assets-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: $spacing-lg;
}

.my-card {
  min-width: 0;
  overflow: hidden;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  box-shadow: $shadow-sm;

  &.my-skeleton {
    pointer-events: none;
  }
}

.my-thumb {
  position: relative;
  height: 168px;
  overflow: hidden;
  background: $bg-secondary;
  cursor: pointer;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .skeleton {
    width: 100%;
    height: 100%;
  }

  .deleted-thumb {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
    width: 100%;
    height: 100%;
    color: $text-placeholder;
    font-size: 12px;
    background:
      repeating-linear-gradient(
        -45deg,
        $bg-secondary,
        $bg-secondary 10px,
        $bg-primary 10px,
        $bg-primary 20px
      );
  }
}

.my-card.is-deleted {
  .my-thumb,
  .my-title {
    cursor: default;
  }

  .my-title {
    color: $text-secondary;
  }
}

.my-status {
  position: absolute;
  top: 10px;
  left: 10px;
  background: rgba(252, 253, 251, 0.92);
}

.my-body {
  padding: $spacing-md $spacing-lg $spacing-lg;

  .my-title {
    font-size: 15px;
    font-weight: 500;
    color: $text-primary;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    cursor: pointer;
    margin-bottom: 4px;
  }

  .my-code {
    font-size: 11px;
    color: $text-placeholder;
    margin-bottom: 8px;
  }

  .reject-reason {
    padding: 6px 8px;
    margin-bottom: 8px;
    background: $error-bg;
    border-radius: $radius-xs;
    font-size: 11px;
    line-height: 1.6;
    color: $error-color;
  }

  .my-meta {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    font-size: 11px;
    color: $text-secondary;
    margin-bottom: 8px;
  }

  .my-actions {
    display: flex;
    align-items: center;
    gap: 2px;
    border-top: 1px solid $border-light;
    padding-top: 8px;

    :deep(.el-button) {
      margin-left: 0;
    }
  }
}

.pagination-section {
  display: flex;
  justify-content: center;
  margin-top: $spacing-3xl;
}

@media (max-width: 1200px) {
  .assets-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .my-assets-page {
    padding: $spacing-lg;
  }

  .status-tabs {
    margin-bottom: $spacing-md;

    :deep(.el-radio-button__inner) {
      padding: 8px 9px;
      font-size: 12px;
    }
  }

  .assets-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .my-thumb {
    height: 140px;
  }

  .page-count {
    display: none;
  }
}

@media (max-width: 480px) {
  .assets-grid {
    grid-template-columns: 1fr;
  }
}
</style>
