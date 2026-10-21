<template>
  <div class="collections-page">
    <header class="page-head">
      <div>
        <h1 class="page-title">我的合集</h1>
        <p class="page-subtitle">把同一主题的园林影像、图纸或模型组织成自己的策展单元。</p>
      </div>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>
        新建合集
      </el-button>
    </header>

    <el-alert
      v-if="loadError"
      type="error"
      :closable="false"
      show-icon
      title="合集加载失败"
      class="load-error"
    >
      <el-button size="small" @click="loadCollections">重试</el-button>
    </el-alert>

    <el-skeleton v-else-if="loading" animated :rows="6" class="loading-block" />

    <el-empty v-else-if="collections.length === 0" description="还没有合集">
      <p class="empty-hint">可以先新建一个合集，再从资产详情把作品加入进来。</p>
      <el-button type="primary" @click="openCreate">新建合集</el-button>
    </el-empty>

    <div v-else class="collection-grid">
      <article
        v-for="collection in collections"
        :key="collection.id"
        class="collection-card"
        @click="$router.push(`/collections/${collection.id}`)"
      >
        <div class="collection-cover">
          <img
            v-if="collection.cover_url && !failedCovers[collection.id]"
            :src="collection.cover_url"
            alt=""
            loading="lazy"
            @error="markCoverFailed(collection.id)"
          />
          <div v-else class="cover-fallback">
            <el-icon><Collection /></el-icon>
          </div>
          <span class="collection-count">{{ collection.asset_count }} 件</span>
          <el-tag
            class="collection-visibility"
            size="small"
            effect="dark"
            :type="collection.is_public ? 'success' : 'info'"
          >
            {{ collection.is_public ? '公开' : '私有' }}
          </el-tag>
        </div>
        <div class="collection-body">
          <div class="collection-title-row">
            <h2 class="collection-name">{{ collection.name }}</h2>
            <el-dropdown
              v-if="collection.is_owner"
              trigger="click"
              @command="command => handleCommand(command, collection)"
              @click.stop
            >
              <button type="button" class="collection-more" aria-label="合集操作" @click.stop>
                <el-icon><MoreFilled /></el-icon>
              </button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="edit">编辑</el-dropdown-item>
                  <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
          <p class="collection-desc">{{ collection.description || '暂无说明' }}</p>
          <footer class="collection-foot">
            <span>{{ collection.owner_name }}</span>
            <span>{{ formatDate(collection.updated_at) }}</span>
          </footer>
        </div>
      </article>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑合集' : '新建合集'"
      width="min(520px, 92vw)"
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="合集名称" prop="name">
          <el-input v-model="form.name" maxlength="100" show-word-limit placeholder="如：拙政园水景" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="4"
            maxlength="500"
            show-word-limit
            placeholder="记录这个合集的策展主题或使用场景"
          />
        </el-form-item>
        <el-form-item label="可见性">
          <el-switch v-model="form.is_public" active-text="公开" inactive-text="仅自己可见" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveCollection">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Collection, MoreFilled, Plus } from '@element-plus/icons-vue'
import { collectionApi } from '@/api/modules'
import { formatDate } from '@/utils'

const collections = ref([])
const loading = ref(true)
const loadError = ref(false)
const dialogVisible = ref(false)
const editingId = ref(null)
const saving = ref(false)
const formRef = ref()
const failedCovers = reactive({})

const form = reactive({
  name: '',
  description: '',
  is_public: false
})

const rules = {
  name: [{ required: true, message: '请输入合集名称', trigger: 'blur' }]
}

function markCoverFailed(id) {
  failedCovers[id] = true
}

async function loadCollections() {
  loading.value = true
  loadError.value = false
  try {
    const response = await collectionApi.getList()
    if (response.data?.code === 200) {
      collections.value = response.data.data || []
    } else {
      loadError.value = true
    }
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  form.name = ''
  form.description = ''
  form.is_public = false
  dialogVisible.value = true
}

function openEdit(collection) {
  editingId.value = collection.id
  form.name = collection.name
  form.description = collection.description || ''
  form.is_public = Boolean(collection.is_public)
  dialogVisible.value = true
}

async function saveCollection() {
  if (saving.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const payload = {
      name: form.name.trim(),
      description: form.description.trim(),
      is_public: form.is_public
    }
    const response = editingId.value
      ? await collectionApi.update(editingId.value, payload)
      : await collectionApi.create(payload)
    if (response.data?.code === 200) {
      ElMessage.success(editingId.value ? '合集已更新' : '合集已创建')
      dialogVisible.value = false
      await loadCollections()
    } else {
      ElMessage.error(response.data?.message || '保存失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleCommand(command, collection) {
  if (command === 'edit') {
    openEdit(collection)
    return
  }
  if (command === 'delete') {
    try {
      await ElMessageBox.confirm(
        `确定删除「${collection.name}」？合集内的资产不会被删除。`,
        '删除合集',
        { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
      )
    } catch {
      return
    }
    try {
      const response = await collectionApi.remove(collection.id)
      if (response.data?.code === 200) {
        ElMessage.success('合集已删除')
        await loadCollections()
      } else {
        ElMessage.error(response.data?.message || '删除失败')
      }
    } catch (error) {
      ElMessage.error(error.response?.data?.message || '删除失败')
    }
  }
}

onMounted(loadCollections)
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.collections-page {
  max-width: 1180px;
  margin: 0 auto;
  padding: 28px 24px 60px;
}

.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 22px;
}

.page-title {
  margin: 0;
  font-family: $font-display;
  font-size: 28px;
  color: $text-primary;
}

.page-subtitle {
  margin: 6px 0 0;
  font-size: 13px;
  color: $text-secondary;
}

.load-error,
.loading-block {
  margin-bottom: 16px;
}

.empty-hint {
  margin: 0 0 12px;
  font-size: 13px;
  color: $text-placeholder;
}

.collection-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.collection-card {
  overflow: hidden;
  border: 1px solid $border-light;
  border-radius: $radius-lg;
  background: $bg-card;
  box-shadow: $shadow-card;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s, transform 0.2s;

  &:hover {
    border-color: $primary-light;
    box-shadow: $shadow-card-hover;
    transform: translateY(-2px);
  }
}

.collection-cover {
  position: relative;
  aspect-ratio: 16 / 10;
  background: $bg-secondary;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.cover-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: $text-placeholder;
  font-size: 34px;
}

.collection-count {
  position: absolute;
  left: 10px;
  bottom: 10px;
  padding: 2px 8px;
  border-radius: $radius-full;
  background: rgba(23, 32, 28, 0.68);
  color: #f7f4ec;
  font-size: 11px;
}

.collection-visibility {
  position: absolute;
  top: 10px;
  right: 10px;
}

.collection-body {
  padding: 14px 16px 16px;
}

.collection-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.collection-name {
  margin: 0;
  font-family: $font-display;
  font-size: 17px;
  color: $text-primary;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.collection-more {
  display: inline-flex;
  padding: 4px;
  border: none;
  background: transparent;
  color: $text-placeholder;
  cursor: pointer;

  &:hover { color: $primary-color; }
}

.collection-desc {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 38px;
  margin: 6px 0 10px;
  font-size: 12px;
  line-height: 1.6;
  color: $text-secondary;
}

.collection-foot {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 11px;
  color: $text-placeholder;
}

@media (max-width: 980px) {
  .collection-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .collections-page {
    padding: 20px 16px 40px;
  }

  .page-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .collection-grid {
    grid-template-columns: 1fr;
  }
}
</style>
