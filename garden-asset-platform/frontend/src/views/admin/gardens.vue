<template>
  <div class="gardens-page">
    <header class="page-head">
      <div>
        <h1 class="page-title">园林档案</h1>
        <p class="page-subtitle">
          维护园林名称、历史、坐标与文保信息；档案会用于资产归属与首页展示。
        </p>
      </div>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>
        新建园林
      </el-button>
    </header>

    <el-alert
      v-if="loadError"
      type="error"
      :closable="false"
      show-icon
      title="园林档案加载失败"
      class="load-error"
    >
      <el-button size="small" @click="loadGardens">重试</el-button>
    </el-alert>

    <el-skeleton v-else-if="loading" animated :rows="6" class="skeleton-card" />

    <template v-else>
      <div class="garden-table-wrap">
        <el-table :data="gardens" stripe row-key="id" class="garden-table">
          <el-table-column label="园林" min-width="240">
            <template #default="{ row }">
              <div class="garden-cell">
                <span class="garden-cover">
                  <img
                    v-if="row.cover_image && !failedCovers[row.id]"
                    :src="row.cover_image"
                    alt=""
                    loading="lazy"
                    @error="markCoverFailed(row.id)"
                  />
                  <el-icon v-else><Picture /></el-icon>
                </span>
                <div class="garden-text">
                  <strong>{{ row.name }}</strong>
                  <small v-if="row.name_en">{{ row.name_en }}</small>
                  <small class="mono">{{ row.code }}</small>
                </div>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="地址" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">{{ row.location || '—' }}</template>
          </el-table-column>
          <el-table-column label="面积（公顷）" width="110">
            <template #default="{ row }">{{ row.area_size ?? '—' }}</template>
          </el-table-column>
          <el-table-column label="建造年份" width="100">
            <template #default="{ row }">{{ row.build_year ?? '—' }}</template>
          </el-table-column>
          <el-table-column label="文保级别" min-width="120">
            <template #default="{ row }">{{ row.heritage_level || '—' }}</template>
          </el-table-column>
          <el-table-column label="已发布资产" width="100">
            <template #default="{ row }">{{ row.asset_count ?? 0 }}</template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
                {{ row.status === 'active' ? '开放' : '归档' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150">
            <template #default="{ row }">
              <el-button size="small" link type="primary" @click="openEdit(row)">编辑</el-button>
              <el-button
                size="small"
                link
                type="danger"
                :loading="deletingId === row.id"
                @click="removeGarden(row)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </template>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑园林档案' : '新建园林档案'"
      width="min(720px, 94vw)"
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <div class="form-grid">
          <el-form-item label="园林编码" prop="code">
            <el-input
              v-model="form.code"
              maxlength="10"
              placeholder="如 ZZY，2-10 位大写字母或数字"
            />
          </el-form-item>
          <el-form-item label="园林名称" prop="name">
            <el-input v-model="form.name" maxlength="100" placeholder="如 拙政园" />
          </el-form-item>
          <el-form-item label="英文名称">
            <el-input v-model="form.name_en" maxlength="100" />
          </el-form-item>
          <el-form-item label="文保级别">
            <el-input v-model="form.heritage_level" maxlength="50" placeholder="如 世界文化遗产" />
          </el-form-item>
          <el-form-item label="地址">
            <el-input v-model="form.location" maxlength="200" />
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="form.status" style="width: 100%">
              <el-option label="开放" value="active" />
              <el-option label="归档" value="archived" />
            </el-select>
          </el-form-item>
          <el-form-item label="面积（公顷）">
            <el-input-number
              v-model="form.area_size"
              :min="0"
              :precision="2"
              :step="0.1"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="建造年份">
            <el-input-number
              v-model="form.build_year"
              :min="0"
              :max="2100"
              :controls="false"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="列入文保年份">
            <el-input-number
              v-model="form.heritage_year"
              :min="0"
              :max="2100"
              :controls="false"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="经度">
            <el-input-number
              v-model="form.longitude"
              :min="-180"
              :max="180"
              :precision="6"
              :controls="false"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="纬度">
            <el-input-number
              v-model="form.latitude"
              :min="-90"
              :max="90"
              :precision="6"
              :controls="false"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="封面图地址">
            <el-input
              v-model="form.cover_image"
              maxlength="500"
              placeholder="/api/assets/.../thumbnail?size=card"
            />
          </el-form-item>
        </div>
        <el-form-item label="简介">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            maxlength="2000"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="历史沿革">
          <el-input
            v-model="form.history"
            type="textarea"
            :rows="4"
            maxlength="4000"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveGarden">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Picture, Plus } from '@element-plus/icons-vue'
import { gardenApi } from '@/api/modules'

const gardens = ref([])
const loading = ref(false)
const loadError = ref(false)
const dialogVisible = ref(false)
const editingId = ref(null)
const saving = ref(false)
const deletingId = ref(null)
const formRef = ref()
const failedCovers = reactive({})

const emptyForm = () => ({
  code: '',
  name: '',
  name_en: '',
  description: '',
  history: '',
  location: '',
  longitude: null,
  latitude: null,
  area_size: null,
  build_year: null,
  heritage_level: '',
  heritage_year: null,
  cover_image: '',
  status: 'active'
})

const form = reactive(emptyForm())

const rules = {
  code: [
    { required: true, message: '请输入园林编码', trigger: 'blur' },
    { pattern: /^[A-Za-z0-9]{2,10}$/, message: '编码需为 2-10 位字母或数字', trigger: 'blur' }
  ],
  name: [{ required: true, message: '请输入园林名称', trigger: 'blur' }]
}

function markCoverFailed(id) {
  failedCovers[id] = true
}

async function loadGardens() {
  loading.value = true
  loadError.value = false
  try {
    const response = await gardenApi.getList({ status: 'all' })
    if (response.data?.code === 200) {
      gardens.value = response.data.data || []
    } else {
      loadError.value = true
    }
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
}

function resetForm() {
  Object.assign(form, emptyForm())
}

function openCreate() {
  editingId.value = null
  resetForm()
  dialogVisible.value = true
}

function openEdit(row) {
  editingId.value = row.id
  Object.assign(form, emptyForm(), {
    code: row.code || '',
    name: row.name || '',
    name_en: row.name_en || '',
    description: row.description || '',
    history: row.history || '',
    location: row.location || '',
    longitude: row.longitude,
    latitude: row.latitude,
    area_size: row.area_size,
    build_year: row.build_year,
    heritage_level: row.heritage_level || '',
    heritage_year: row.heritage_year,
    cover_image: row.cover_image || '',
    status: row.status || 'active'
  })
  dialogVisible.value = true
}

function payload() {
  return {
    code: form.code.trim().toUpperCase(),
    name: form.name.trim(),
    name_en: form.name_en.trim(),
    description: form.description,
    history: form.history,
    location: form.location.trim(),
    longitude: form.longitude,
    latitude: form.latitude,
    area_size: form.area_size,
    build_year: form.build_year,
    heritage_level: form.heritage_level.trim(),
    heritage_year: form.heritage_year,
    cover_image: form.cover_image.trim(),
    status: form.status
  }
}

async function saveGarden() {
  if (saving.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const response = editingId.value
      ? await gardenApi.update(editingId.value, payload())
      : await gardenApi.create(payload())
    if (response.data?.code === 200) {
      ElMessage.success(editingId.value ? '园林档案已更新' : '园林档案已创建')
      dialogVisible.value = false
      await loadGardens()
    } else {
      ElMessage.error(response.data?.message || '保存失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function removeGarden(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除「${row.name}」？该操作不可恢复；园林下仍有资产时会被拒绝。`,
      '删除园林档案',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }

  deletingId.value = row.id
  try {
    const response = await gardenApi.remove(row.id)
    if (response.data?.code === 200) {
      ElMessage.success('园林档案已删除')
      await loadGardens()
    } else {
      ElMessage.error(response.data?.message || '删除失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '删除失败')
  } finally {
    deletingId.value = null
  }
}

onMounted(loadGardens)
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.gardens-page {
  padding: 0;
}

.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
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

.load-error {
  margin-bottom: 16px;
}

.skeleton-card {
  padding: 24px;
  background: $bg-card;
  border: 1px solid $border-light;
  border-radius: $radius-md;
}

.garden-table-wrap {
  background: $bg-card;
  border: 1px solid $border-light;
  border-radius: $radius-md;
  overflow: hidden;
}

.garden-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.garden-cover {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 40px;
  flex: 0 0 52px;
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

.garden-text {
  display: flex;
  flex-direction: column;
  min-width: 0;

  strong {
    font-size: 13px;
    font-weight: 600;
    color: $text-primary;
  }

  small {
    font-size: 11px;
    color: $text-placeholder;
  }
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
}

@media (max-width: 720px) {
  .page-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
