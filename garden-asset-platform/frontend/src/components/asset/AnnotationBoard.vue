<template>
  <section class="annotation-section">
    <header class="section-head">
      <div>
        <h2>图纸与影像标注</h2>
        <p>
          标注坐标绑定当前版本{{ versionNo ? ` v${versionNo}` : '' }}；上传新版本后旧标注保留在历史版本，不会叠加到新文件。
        </p>
      </div>
      <div class="annotation-toolbar">
        <el-checkbox v-model="includeHistory" size="small" @change="loadAnnotations">
          含历史版本
        </el-checkbox>
        <el-select v-model="statusFilter" size="small" style="width: 110px" @change="loadAnnotations">
          <el-option label="全部状态" value="" />
          <el-option label="待处理" value="open" />
          <el-option label="已解决" value="resolved" />
        </el-select>
        <el-button
          :type="annotateMode ? 'danger' : 'primary'"
          plain
          size="small"
          @click="toggleAnnotate"
        >
          {{ annotateMode ? '退出标注' : '开始标注' }}
        </el-button>
      </div>
    </header>

    <div class="annotation-layout">
      <div class="stage-column">
        <div
          ref="stageRef"
          class="annotation-stage"
          :class="{ 'annotate-mode': annotateMode, drawing }"
          @pointerdown="onPointerDown"
          @pointermove="onPointerMove"
          @pointerup="onPointerUp"
          @pointercancel="onPointerUp"
        >
          <img
            :src="imageUrl"
            :alt="`${assetType === 'vector' ? '矢量预览' : '资产影像'}，可添加区域标注`"
            draggable="false"
            @dragstart.prevent
          />
          <div
            v-if="draftBox"
            class="annotation-box draft"
            :style="boxStyle(draftBox)"
          ></div>
          <button
            v-for="(item, index) in boxAnnotations"
            :key="item.id"
            type="button"
            class="annotation-box"
            :class="[`type-${item.annotation_type}`, item.status, { selected: selectedId === item.id }]"
            :style="boxStyle(item)"
            :title="item.title"
            :aria-label="`标注 ${index + 1}：${item.title}`"
            @click.stop="selectAnnotation(item)"
            @pointerdown.stop
          >
            <span class="box-index">{{ index + 1 }}</span>
          </button>
        </div>
        <p v-if="annotateMode" class="draw-hint">
          在图上按住拖动即可框选区域；松开后填写标注说明。
        </p>
        <p v-else class="draw-hint">
          点击“开始标注”后可框选区域；已有标注可点击方框定位。
        </p>
        <p v-if="includeHistory" class="history-hint">
          历史版本标注只在右侧列表中展示，不会叠加到当前版本的图上。
        </p>
      </div>

      <aside class="annotation-list">
        <el-alert
          v-if="loadError"
          type="error"
          :closable="false"
          show-icon
          title="标注加载失败"
          class="annotation-error"
        >
          <el-button size="small" @click="loadAnnotations">重试</el-button>
        </el-alert>

        <el-skeleton v-else-if="loading" animated :rows="4" />

        <div v-else-if="annotations.length === 0" class="annotation-empty">
          <el-icon><EditPen /></el-icon>
          <p>当前筛选下没有标注</p>
          <el-button size="small" type="primary" plain @click="toggleAnnotate">
            开始标注
          </el-button>
        </div>

        <ul v-else class="annotation-items">
          <li
            v-for="(item, index) in annotations"
            :key="item.id"
            class="annotation-entry"
            :class="{ selected: selectedId === item.id, resolved: item.status === 'resolved' }"
            @click="selectAnnotation(item)"
          >
            <div class="entry-head">
              <span class="entry-index">{{ index + 1 }}</span>
              <strong>{{ item.title }}</strong>
              <el-tag v-if="includeHistory && item.version_no" size="small" effect="plain">
                v{{ item.version_no }}
              </el-tag>
              <el-tag size="small" :type="item.status === 'resolved' ? 'success' : 'warning'" effect="plain">
                {{ item.status === 'resolved' ? '已解决' : '待处理' }}
              </el-tag>
            </div>
            <p v-if="item.content" class="entry-content">{{ item.content }}</p>
            <div class="entry-meta">
              <span>{{ typeLabel(item.annotation_type) }}</span>
              <span>{{ item.author_name || '用户' }}</span>
              <span>{{ formatDate(item.created_at, 'YYYY-MM-DD HH:mm') }}</span>
            </div>
            <div class="entry-actions">
              <el-button
                v-if="item.can_resolve"
                link
                size="small"
                type="primary"
                :loading="resolvingId === item.id"
                @click.stop="toggleResolved(item)"
              >
                {{ item.status === 'resolved' ? '重新打开' : '标记解决' }}
              </el-button>
              <el-button
                v-if="item.can_edit"
                link
                size="small"
                @click.stop="openEdit(item)"
              >
                编辑
              </el-button>
              <el-button
                v-if="item.can_delete"
                link
                size="small"
                type="danger"
                :loading="deletingId === item.id"
                @click.stop="removeAnnotation(item)"
              >
                删除
              </el-button>
            </div>
          </li>
        </ul>
      </aside>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑标注' : '新增标注'"
      width="min(520px, 92vw)"
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-position="top">
        <el-form-item label="标注标题" prop="title">
          <el-input v-model="form.title" maxlength="100" show-word-limit placeholder="例如：斗拱缺角、需补充说明的位置" />
        </el-form-item>
        <el-form-item label="类型">
          <el-radio-group v-model="form.annotation_type">
            <el-radio-button value="note">备注</el-radio-button>
            <el-radio-button value="issue">问题</el-radio-button>
            <el-radio-button value="suggestion">建议</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.content" type="textarea" :rows="3" maxlength="2000" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveAnnotation">
          {{ editingId ? '保存修改' : '添加标注' }}
        </el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { EditPen } from '@element-plus/icons-vue'
import { assetApi } from '@/api/modules'
import { formatDate } from '@/utils'

const props = defineProps({
  assetId: { type: String, required: true },
  assetType: { type: String, default: 'image' },
  imageUrl: { type: String, default: '' },
  versionId: { type: Number, default: null },
  versionNo: { type: Number, default: null }
})

const annotations = ref([])
const loading = ref(true)
const loadError = ref(false)
const includeHistory = ref(false)
const statusFilter = ref('')
const annotateMode = ref(false)
const stageRef = ref()
const drawing = ref(false)
const draftBox = ref(null)
const dragStart = ref(null)
const selectedId = ref(null)

const dialogVisible = ref(false)
const editingId = ref(null)
const saving = ref(false)
const formRef = ref()
const form = reactive({
  title: '',
  content: '',
  annotation_type: 'note',
  x: 0,
  y: 0,
  width: 0,
  height: 0
})
const formRules = {
  title: [{ required: true, message: '请输入标注标题', trigger: 'blur' }]
}

const resolvingId = ref(null)
const deletingId = ref(null)

const TYPE_LABELS = {
  note: '备注',
  issue: '问题',
  suggestion: '建议'
}

const boxAnnotations = computed(() => {
  if (!props.versionId) return annotations.value
  return annotations.value.filter(
    item => !item.version_id || item.version_id === props.versionId
  )
})

function typeLabel(type) {
  return TYPE_LABELS[type] || '备注'
}

function boxStyle(box) {
  return {
    left: `${(box.x || 0) * 100}%`,
    top: `${(box.y || 0) * 100}%`,
    width: `${(box.width || 0) * 100}%`,
    height: `${(box.height || 0) * 100}%`
  }
}

async function loadAnnotations() {
  loading.value = true
  loadError.value = false
  try {
    const params = {}
    if (includeHistory.value) {
      params.all = 1
    } else if (props.versionId) {
      params.version_id = props.versionId
    }
    if (statusFilter.value) params.status = statusFilter.value

    const response = await assetApi.getAnnotations(props.assetId, params)
    if (response.data?.code === 200) {
      annotations.value = response.data.data?.items || []
      if (!annotations.value.some(item => item.id === selectedId.value)) {
        selectedId.value = null
      }
    } else {
      loadError.value = true
    }
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
}

function toggleAnnotate() {
  annotateMode.value = !annotateMode.value
  if (!annotateMode.value) {
    draftBox.value = null
    dragStart.value = null
    drawing.value = false
  }
}

function pointFromEvent(event) {
  const rect = stageRef.value?.getBoundingClientRect()
  if (!rect || !rect.width || !rect.height) return null
  return {
    x: Math.min(Math.max((event.clientX - rect.left) / rect.width, 0), 1),
    y: Math.min(Math.max((event.clientY - rect.top) / rect.height, 0), 1)
  }
}

function onPointerDown(event) {
  if (!annotateMode.value || event.button !== 0) return
  const point = pointFromEvent(event)
  if (!point) return
  dragStart.value = point
  draftBox.value = { x: point.x, y: point.y, width: 0, height: 0 }
  drawing.value = true
  try {
    stageRef.value?.setPointerCapture?.(event.pointerId)
  } catch {
    // 某些浏览器/触摸设备不支持指针捕获，不影响拖动
  }
}

function onPointerMove(event) {
  if (!drawing.value || !dragStart.value) return
  const point = pointFromEvent(event)
  if (!point) return
  draftBox.value = {
    x: Math.min(dragStart.value.x, point.x),
    y: Math.min(dragStart.value.y, point.y),
    width: Math.abs(point.x - dragStart.value.x),
    height: Math.abs(point.y - dragStart.value.y)
  }
}

function onPointerUp(event) {
  if (!drawing.value) return
  drawing.value = false
  try {
    stageRef.value?.releasePointerCapture?.(event.pointerId)
  } catch {
    // 指针未被捕获时忽略
  }
  const box = draftBox.value
  dragStart.value = null
  if (!box || box.width < 0.008 || box.height < 0.008) {
    draftBox.value = null
    return
  }
  editingId.value = null
  form.title = ''
  form.content = ''
  form.annotation_type = 'note'
  form.x = Number(box.x.toFixed(5))
  form.y = Number(box.y.toFixed(5))
  form.width = Number(box.width.toFixed(5))
  form.height = Number(box.height.toFixed(5))
  draftBox.value = null
  dialogVisible.value = true
}

function openEdit(item) {
  editingId.value = item.id
  form.title = item.title
  form.content = item.content || ''
  form.annotation_type = item.annotation_type || 'note'
  form.x = item.x
  form.y = item.y
  form.width = item.width
  form.height = item.height
  dialogVisible.value = true
}

async function saveAnnotation() {
  if (saving.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const payload = {
      title: form.title.trim(),
      content: form.content.trim(),
      annotation_type: form.annotation_type
    }
    let response
    if (editingId.value) {
      response = await assetApi.updateAnnotation(props.assetId, editingId.value, payload)
    } else {
      response = await assetApi.createAnnotation(props.assetId, {
        ...payload,
        x: form.x,
        y: form.y,
        width: form.width,
        height: form.height,
        version_id: props.versionId || undefined
      })
    }
    if (response.data?.code === 200) {
      ElMessage.success(editingId.value ? '标注已更新' : '标注已添加')
      dialogVisible.value = false
      selectedId.value = response.data.data?.id || editingId.value
      await loadAnnotations()
    } else {
      ElMessage.error(response.data?.message || '保存失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

function selectAnnotation(item) {
  selectedId.value = item.id
}

async function toggleResolved(item) {
  if (resolvingId.value) return
  resolvingId.value = item.id
  try {
    const nextStatus = item.status === 'resolved' ? 'open' : 'resolved'
    const response = await assetApi.updateAnnotation(props.assetId, item.id, {
      status: nextStatus
    })
    if (response.data?.code === 200) {
      ElMessage.success(nextStatus === 'resolved' ? '已标记为解决' : '已重新打开')
      await loadAnnotations()
    } else {
      ElMessage.error(response.data?.message || '操作失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '操作失败')
  } finally {
    resolvingId.value = null
  }
}

async function removeAnnotation(item) {
  try {
    await ElMessageBox.confirm('删除后无法恢复，确定删除这条标注？', '删除标注', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }
  deletingId.value = item.id
  try {
    const response = await assetApi.deleteAnnotation(props.assetId, item.id)
    if (response.data?.code === 200) {
      ElMessage.success('标注已删除')
      if (selectedId.value === item.id) selectedId.value = null
      await loadAnnotations()
    } else {
      ElMessage.error(response.data?.message || '删除失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '删除失败')
  } finally {
    deletingId.value = null
  }
}

watch(() => props.versionId, () => loadAnnotations())

onMounted(loadAnnotations)
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.annotation-section {
  margin-top: $spacing-3xl;
  padding: $spacing-xl;
  border: 1px solid $border-light;
  border-radius: $radius-lg;
  background: $bg-card;
  box-shadow: $shadow-card;
}

.section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;

  h2 {
    margin: 0;
    font-family: $font-display;
    font-size: 20px;
    color: $text-primary;
  }

  p {
    margin: 4px 0 0;
    font-size: 12px;
    line-height: 1.6;
    color: $text-placeholder;
  }
}

.annotation-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  flex: 0 0 auto;
}

.annotation-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(280px, 0.8fr);
  gap: 18px;
}

.stage-column {
  min-width: 0;
}

.annotation-stage {
  position: relative;
  width: 100%;
  border-radius: $radius-md;
  overflow: hidden;
  background: $ink-band;
  cursor: default;
  touch-action: pan-y;
  user-select: none;

  img {
    display: block;
    width: 100%;
    height: auto;
    pointer-events: none;
  }

  &.annotate-mode {
    cursor: crosshair;
    touch-action: none;

    &::after {
      content: '';
      position: absolute;
      inset: 0;
      border: 2px dashed rgba(166, 64, 47, 0.55);
      pointer-events: none;
    }
  }

  &.drawing {
    cursor: crosshair;
  }
}

.annotation-box {
  position: absolute;
  border: 2px solid $secondary-color;
  background: rgba(76, 110, 138, 0.12);
  border-radius: 2px;
  padding: 0;
  cursor: pointer;
  transition: box-shadow 0.15s, background 0.15s;

  &.type-issue {
    border-color: $accent-color;
    background: rgba(166, 64, 47, 0.12);
  }

  &.type-suggestion {
    border-color: $success-color;
    background: rgba(63, 125, 91, 0.12);
  }

  &.resolved {
    border-style: dashed;
    opacity: 0.55;
  }

  &.selected {
    box-shadow: 0 0 0 2px $bg-card, 0 0 0 4px $accent-color;
    opacity: 1;
  }

  &.draft {
    border: 2px dashed $accent-color;
    background: rgba(166, 64, 47, 0.08);
    pointer-events: none;
  }
}

.box-index {
  position: absolute;
  top: -9px;
  left: -9px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 4px;
  border-radius: $radius-full;
  background: $accent-color;
  color: #fff;
  font-size: 10px;
  font-family: $font-mono;
}

.draw-hint {
  margin: 8px 0 0;
  font-size: 11px;
  color: $text-placeholder;
}

.history-hint {
  margin: 4px 0 0;
  font-size: 11px;
  color: $warning-color;
}

.annotation-list {
  min-width: 0;
  max-height: 520px;
  overflow-y: auto;
}

.annotation-error {
  margin-bottom: 10px;
}

.annotation-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 28px 16px;
  border: 1px dashed $border-color;
  border-radius: $radius-md;
  background: $bg-secondary;
  color: $text-placeholder;
  font-size: 12px;

  .el-icon { font-size: 24px; }

  p { margin: 0; }
}

.annotation-items {
  list-style: none;
  margin: 0;
  padding: 0;
}

.annotation-entry {
  padding: 10px 12px;
  margin-bottom: 8px;
  border: 1px solid $border-light;
  border-left: 3px solid $secondary-color;
  border-radius: $radius-sm;
  background: $bg-card;
  cursor: pointer;

  &.selected {
    border-color: $primary-light;
    box-shadow: $shadow-sm;
  }

  &.resolved {
    opacity: 0.72;
    border-left-color: $success-color;
  }
}

.entry-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;

  strong {
    flex: 1;
    min-width: 0;
    font-size: 13px;
    color: $text-primary;
  }
}

.entry-index {
  font-family: $font-mono;
  font-size: 11px;
  color: $accent-color;
}

.entry-content {
  margin: 5px 0 0;
  font-size: 12px;
  line-height: 1.6;
  color: $text-secondary;
  white-space: pre-wrap;
}

.entry-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 6px;
  font-size: 10px;
  color: $text-placeholder;
}

.entry-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  margin-top: 4px;
}

@media (max-width: 900px) {
  .annotation-layout {
    grid-template-columns: 1fr;
  }

  .annotation-list {
    max-height: none;
  }
}

@media (max-width: 720px) {
  .annotation-section {
    padding: 16px;
  }

  .section-head {
    flex-direction: column;
  }

  .annotation-toolbar {
    width: 100%;
  }
}
</style>
