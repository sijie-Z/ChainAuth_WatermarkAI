<template>
  <div class="collection-detail-page">
    <router-link to="/collections" class="back-link">
      <el-icon><ArrowLeft /></el-icon>
      返回我的合集
    </router-link>

    <el-skeleton v-if="loading" animated :rows="8" class="loading-block" />

    <el-result
      v-else-if="loadError"
      icon="error"
      title="合集加载失败"
      sub-title="合集可能已被删除，或你没有查看权限"
    >
      <template #extra>
        <el-button type="primary" @click="loadCollection">重试</el-button>
        <el-button @click="$router.push('/collections')">返回合集列表</el-button>
      </template>
    </el-result>

    <template v-else-if="collection">
      <header class="collection-head">
        <div class="head-main">
          <div class="head-kicker">
            <el-tag size="small" :type="collection.is_public ? 'success' : 'info'" effect="plain">
              {{ collection.is_public ? '公开合集' : '私有合集' }}
            </el-tag>
            <span>{{ collection.asset_count }} 件资产</span>
            <span>更新于 {{ formatDate(collection.updated_at) }}</span>
          </div>
          <h1 class="collection-title">{{ collection.name }}</h1>
          <p class="collection-desc">{{ collection.description || '暂无说明' }}</p>
        </div>
        <div v-if="collection.is_owner" class="head-actions">
          <el-button @click="openEdit">
            <el-icon><Edit /></el-icon>
            编辑
          </el-button>
          <el-button type="primary" @click="openAdd">
            <el-icon><Plus /></el-icon>
            添加资产
          </el-button>
        </div>
      </header>

      <el-empty v-if="assets.length === 0" description="合集里还没有资产">
        <el-button v-if="collection.is_owner" type="primary" @click="openAdd">添加资产</el-button>
        <el-button v-else @click="$router.push('/assets')">去资产档案看看</el-button>
      </el-empty>

      <div v-else class="asset-grid">
        <article v-for="asset in assets" :key="asset.id" class="asset-card">
          <router-link :to="`/assets/${asset.id}`" class="asset-link">
            <div class="asset-thumb">
              <img
                v-if="!failedThumbs[asset.id]"
                :src="`/api/assets/${asset.id}/thumbnail?size=card&v=${asset.current_version_no || 1}`"
                :alt="asset.title"
                loading="lazy"
                @error="markThumbFailed(asset.id)"
              />
              <div v-else class="thumb-fallback"><el-icon><Picture /></el-icon></div>
            </div>
            <div class="asset-body">
              <h2>{{ asset.title }}</h2>
              <p class="mono">{{ asset.asset_code }}</p>
              <p class="asset-meta">
                {{ asset.garden_name || '未归类' }}
                <span v-if="asset.file_format">· {{ asset.file_format }}</span>
              </p>
            </div>
          </router-link>
          <el-button
            v-if="collection.is_owner"
            class="remove-btn"
            size="small"
            text
            type="danger"
            :loading="removingId === asset.id"
            @click="removeAsset(asset)"
          >
            移出合集
          </el-button>
        </article>
      </div>
    </template>

    <!-- 添加资产 -->
    <el-dialog v-model="addVisible" title="添加资产" width="min(720px, 94vw)">
      <div class="add-search">
        <el-input
          v-model="keyword"
          placeholder="按标题或编码搜索已发布资产"
          clearable
          @keyup.enter="searchAssets"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button type="primary" :loading="searching" @click="searchAssets">搜索</el-button>
      </div>

      <el-skeleton v-if="searching" animated :rows="4" />
      <el-empty v-else-if="candidates.length === 0" description="没有可添加的资产" :image-size="60" />
      <el-checkbox-group v-else v-model="selectedIds" class="asset-choices">
        <label v-for="asset in candidates" :key="asset.id" class="asset-choice">
          <el-checkbox :value="asset.id" />
          <span class="choice-thumb">
            <img
              v-if="!failedThumbs[asset.id]"
              :src="`/api/assets/${asset.id}/thumbnail?size=card`"
              alt=""
              loading="lazy"
              @error="markThumbFailed(asset.id)"
            />
          </span>
          <span class="choice-text">
            <strong>{{ asset.title }}</strong>
            <small class="mono">{{ asset.asset_code }}</small>
          </span>
        </label>
      </el-checkbox-group>

      <template #footer>
        <span class="selected-count">已选 {{ selectedIds.length }} 件</span>
        <el-button @click="addVisible = false">取消</el-button>
        <el-button type="primary" :loading="adding" :disabled="selectedIds.length === 0" @click="addSelected">
          加入合集
        </el-button>
      </template>
    </el-dialog>

    <!-- 编辑合集 -->
    <el-dialog v-model="editVisible" title="编辑合集" width="min(520px, 92vw)" :close-on-click-modal="false">
      <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-position="top">
        <el-form-item label="合集名称" prop="name">
          <el-input v-model="editForm.name" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="editForm.description" type="textarea" :rows="4" maxlength="500" show-word-limit />
        </el-form-item>
        <el-form-item label="可见性">
          <el-switch v-model="editForm.is_public" active-text="公开" inactive-text="仅自己可见" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Edit, Picture, Plus, Search } from '@element-plus/icons-vue'
import { assetApi, collectionApi } from '@/api/modules'
import { formatDate } from '@/utils'

const route = useRoute()
const collection = ref(null)
const assets = ref([])
const loading = ref(true)
const loadError = ref(false)
const failedThumbs = reactive({})
const removingId = ref('')

const addVisible = ref(false)
const keyword = ref('')
const candidates = ref([])
const selectedIds = ref([])
const searching = ref(false)
const adding = ref(false)

const editVisible = ref(false)
const saving = ref(false)
const editFormRef = ref()
const editForm = reactive({ name: '', description: '', is_public: false })
const editRules = {
  name: [{ required: true, message: '请输入合集名称', trigger: 'blur' }]
}

const existingIds = computed(() => new Set(assets.value.map(asset => asset.id)))

function markThumbFailed(id) {
  failedThumbs[id] = true
}

async function loadCollection() {
  loading.value = true
  loadError.value = false
  try {
    const response = await collectionApi.getDetail(route.params.id)
    if (response.data?.code === 200) {
      collection.value = response.data.data
      assets.value = response.data.data.assets || []
    } else {
      loadError.value = true
    }
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
}

async function searchAssets() {
  if (searching.value) return
  searching.value = true
  try {
    const response = await assetApi.getList({
      keyword: keyword.value.trim() || undefined,
      per_page: 12,
      page: 1
    })
    if (response.data?.code === 200) {
      candidates.value = (response.data.data.items || []).filter(
        asset => !existingIds.value.has(asset.id)
      )
    }
  } catch {
    ElMessage.error('资产搜索失败')
  } finally {
    searching.value = false
  }
}

function openAdd() {
  addVisible.value = true
  selectedIds.value = []
  keyword.value = ''
  candidates.value = []
  searchAssets()
}

async function addSelected() {
  if (adding.value || selectedIds.value.length === 0) return
  adding.value = true
  try {
    const response = await collectionApi.addAssets(collection.value.id, selectedIds.value)
    if (response.data?.code === 200) {
      ElMessage.success(response.data.message || '已加入合集')
      addVisible.value = false
      await loadCollection()
    } else {
      ElMessage.error(response.data?.message || '添加失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '添加失败')
  } finally {
    adding.value = false
  }
}

async function removeAsset(asset) {
  try {
    await ElMessageBox.confirm(
      `将「${asset.title}」移出合集？资产本身不会被删除。`,
      '移出合集',
      { type: 'warning', confirmButtonText: '移出', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  removingId.value = asset.id
  try {
    const response = await collectionApi.removeAsset(collection.value.id, asset.id)
    if (response.data?.code === 200) {
      ElMessage.success('已移出合集')
      await loadCollection()
    } else {
      ElMessage.error(response.data?.message || '操作失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '操作失败')
  } finally {
    removingId.value = ''
  }
}

function openEdit() {
  editForm.name = collection.value.name
  editForm.description = collection.value.description || ''
  editForm.is_public = Boolean(collection.value.is_public)
  editVisible.value = true
}

async function saveEdit() {
  if (saving.value) return
  const valid = await editFormRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const response = await collectionApi.update(collection.value.id, {
      name: editForm.name.trim(),
      description: editForm.description.trim(),
      is_public: editForm.is_public
    })
    if (response.data?.code === 200) {
      ElMessage.success('合集已更新')
      editVisible.value = false
      await loadCollection()
    } else {
      ElMessage.error(response.data?.message || '保存失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(loadCollection)
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.collection-detail-page {
  max-width: 1180px;
  margin: 0 auto;
  padding: 24px 24px 60px;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 18px;
  font-size: 13px;
  color: $text-secondary;
  text-decoration: none;

  &:hover { color: $primary-color; }
}

.loading-block {
  background: $bg-card;
  border: 1px solid $border-light;
  border-radius: $radius-lg;
  padding: 24px;
}

.collection-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding-bottom: 20px;
  margin-bottom: 24px;
  border-bottom: 1px solid $border-color;
}

.head-kicker {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 12px;
  color: $text-placeholder;
}

.collection-title {
  margin: 8px 0 0;
  font-family: $font-display;
  font-size: 30px;
  color: $text-primary;
}

.collection-desc {
  margin: 8px 0 0;
  max-width: 720px;
  font-size: 14px;
  line-height: 1.8;
  color: $text-secondary;
  white-space: pre-wrap;
}

.head-actions {
  display: flex;
  gap: 10px;
  flex: 0 0 auto;
}

.asset-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.asset-card {
  position: relative;
  overflow: hidden;
  border: 1px solid $border-light;
  border-radius: $radius-md;
  background: $bg-card;
  transition: border-color 0.2s, box-shadow 0.2s;

  &:hover {
    border-color: $primary-light;
    box-shadow: $shadow-card;
  }
}

.asset-link {
  display: block;
  color: $text-primary;
  text-decoration: none;
}

.asset-thumb {
  aspect-ratio: 4 / 3;
  background: $bg-secondary;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.thumb-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: $text-placeholder;
  font-size: 28px;
}

.asset-body {
  padding: 12px 14px;

  h2 {
    margin: 0;
    font-size: 14px;
    font-weight: 500;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.mono {
  margin: 4px 0 0;
  font-family: $font-mono;
  font-size: 11px;
  color: $text-placeholder;
}

.asset-meta {
  margin: 4px 0 0;
  font-size: 11px;
  color: $text-secondary;
}

.remove-btn {
  position: absolute;
  right: 8px;
  bottom: 8px;
  background: rgba(252, 253, 251, 0.92);
}

.add-search {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}

.asset-choices {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  max-height: 380px;
  overflow-y: auto;
}

.asset-choice {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  border: 1px solid $border-light;
  border-radius: $radius-md;
  cursor: pointer;

  &:hover {
    border-color: $primary-light;
    background: $bg-hover;
  }
}

.choice-thumb {
  width: 48px;
  height: 36px;
  flex: 0 0 48px;
  overflow: hidden;
  border-radius: $radius-xs;
  background: $bg-secondary;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.choice-text {
  display: flex;
  flex-direction: column;
  min-width: 0;

  strong {
    font-size: 13px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  small {
    font-family: $font-mono;
    font-size: 11px;
    color: $text-placeholder;
  }
}

.selected-count {
  margin-right: 12px;
  font-size: 12px;
  color: $text-placeholder;
}

@media (max-width: 980px) {
  .asset-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .collection-detail-page {
    padding: 18px 16px 40px;
  }

  .collection-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .asset-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .asset-choices {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 480px) {
  .asset-grid {
    grid-template-columns: 1fr;
  }
}
</style>
