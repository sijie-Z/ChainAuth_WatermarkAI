<template>
  <div class="favorites-page">
    <header class="page-bar">
      <router-link to="/assets" class="page-back">
        <el-icon><ArrowLeft /></el-icon>
        返回资产档案
      </router-link>
      <h1 class="page-title">我的收藏</h1>
      <span class="page-count">共 {{ total }} 件</span>
    </header>

    <div v-if="loading" class="favorites-grid" aria-busy="true">
      <div v-for="i in 8" :key="`fav-skeleton-${i}`" class="favorite-card favorite-skeleton">
        <div class="favorite-thumb skeleton"></div>
        <div class="favorite-body">
          <div class="skeleton" style="width: 70%; height: 16px"></div>
          <div class="skeleton" style="width: 45%; height: 12px; margin-top: 8px"></div>
        </div>
      </div>
    </div>

    <el-empty v-else-if="loadError" description="收藏列表加载失败">
      <el-button type="primary" @click="loadFavorites">重试</el-button>
    </el-empty>

    <el-empty v-else-if="favorites.length === 0" description="还没有收藏任何资产">
      <el-button type="primary" @click="$router.push('/assets')">去资产档案看看</el-button>
    </el-empty>

    <template v-else>
      <div class="favorites-grid">
        <article
          v-for="item in favorites"
          :key="item.id"
          class="favorite-card"
          role="button"
          tabindex="0"
          @click="openAsset(item.id)"
          @keydown.enter.prevent="openAsset(item.id)"
          @keydown.space.prevent="openAsset(item.id)"
        >
          <div class="favorite-thumb">
            <img :src="getThumbnail(item)" :alt="item.title" loading="lazy" @error="onImageError" />
            <button
              type="button"
              class="favorite-remove"
              title="取消收藏"
              @click.stop="removeFavorite(item)"
            >
              <el-icon><StarFilled /></el-icon>
            </button>
          </div>
          <div class="favorite-body">
            <h2 class="favorite-title">{{ item.title }}</h2>
            <p class="favorite-code mono">{{ item.asset_code }}</p>
            <div class="favorite-meta">
              <span>{{ item.garden_name || '未归类园林' }}</span>
              <span>{{ formatDate(item.created_at) }}</span>
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
          @current-change="handlePageChange"
        />
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, StarFilled } from '@element-plus/icons-vue'
import { assetApi } from '@/api/modules'
import { parseBackendDate } from '@/utils'

const router = useRouter()
const favorites = ref([])
const loading = ref(true)
const loadError = ref(false)
const page = ref(1)
const perPage = ref(12)
const total = ref(0)

async function loadFavorites() {
  loading.value = true
  loadError.value = false
  try {
    const response = await assetApi.getFavorites({ page: page.value, per_page: perPage.value })
    if (response.data?.code === 200) {
      favorites.value = response.data.data?.items || []
      total.value = response.data.data?.total || 0
    } else {
      loadError.value = true
    }
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
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

function openAsset(id) {
  router.push(`/assets/${id}`)
}

async function removeFavorite(item) {
  try {
    await assetApi.removeFavorite(item.id)
    favorites.value = favorites.value.filter(favorite => favorite.id !== item.id)
    total.value = Math.max(total.value - 1, 0)
    ElMessage.success('已取消收藏')

    // 删除的是当前页最后一件时回退一页，避免直接进入“没有收藏”的空状态
    if (favorites.value.length === 0 && page.value > 1) {
      page.value -= 1
      await loadFavorites()
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '取消收藏失败')
  }
}

async function handlePageChange() {
  await loadFavorites()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function formatDate(value) {
  const date = parseBackendDate(value)
  return date ? date.toLocaleDateString('zh-CN') : ''
}

onMounted(loadFavorites)
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.favorites-page {
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
  margin-bottom: $spacing-xl;
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

.favorites-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: $spacing-lg;
}

.favorite-card {
  min-width: 0;
  overflow: hidden;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  box-shadow: $shadow-sm;
  cursor: pointer;
  transition: border-color $transition-fast, box-shadow $transition-fast;

  &:hover {
    border-color: $border-dark;
    box-shadow: $shadow-md;
  }

  &:focus-visible {
    outline: 2px solid $primary-color;
    outline-offset: 2px;
  }
}

.favorite-thumb {
  position: relative;
  height: 180px;
  overflow: hidden;
  background: $bg-secondary;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .skeleton {
    width: 100%;
    height: 100%;
  }
}

.favorite-remove {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 30px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(252, 253, 251, 0.35);
  border-radius: 50%;
  background: rgba(14, 59, 51, 0.62);
  color: #f1c40f;
  cursor: pointer;

  &:hover {
    background: $accent-color;
    color: #fcfdfb;
  }
}

.favorite-body {
  padding: $spacing-md $spacing-lg $spacing-lg;

  .favorite-title {
    font-size: 15px;
    font-weight: 500;
    color: $text-primary;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-bottom: 4px;
  }

  .favorite-code {
    font-size: 11px;
    color: $text-placeholder;
    margin-bottom: 10px;
  }

  .favorite-meta {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    font-size: 11px;
    color: $text-secondary;
  }
}

.favorite-skeleton {
  pointer-events: none;
  min-height: 250px;

  .favorite-body {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
}

.pagination-section {
  display: flex;
  justify-content: center;
  margin-top: $spacing-3xl;
}

@media (max-width: 1200px) {
  .favorites-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .favorites-page {
    padding: $spacing-lg;
  }

  .favorites-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .favorite-thumb {
    height: 140px;
  }
}

@media (max-width: 480px) {
  .favorites-grid {
    grid-template-columns: 1fr;
  }
}
</style>
