<template>
  <section class="comment-section">
    <header class="section-head">
      <div>
        <h2>讨论</h2>
        <p>{{ total }} 条评论 · 围绕这件资产的著录、授权与使用交流</p>
      </div>
    </header>

    <div class="comment-composer">
      <div v-if="replyTo" class="reply-banner">
        正在回复 <strong>{{ replyTo.author_name }}</strong>
        <el-button link type="primary" size="small" @click="cancelReply">取消</el-button>
      </div>
      <el-input
        ref="composerRef"
        v-model="content"
        type="textarea"
        :rows="3"
        maxlength="2000"
        show-word-limit
        :placeholder="replyTo ? `回复 ${replyTo.author_name}…` : '写下你的问题、补充或使用说明…'"
        :disabled="submitting"
      />
      <div class="composer-actions">
        <span class="composer-hint">评论会公开显示给能查看该资产的用户</span>
        <el-button
          type="primary"
          :loading="submitting"
          :disabled="!content.trim()"
          @click="submitComment"
        >
          {{ replyTo ? '发送回复' : '发表评论' }}
        </el-button>
      </div>
    </div>

    <el-alert
      v-if="loadError"
      type="error"
      :closable="false"
      show-icon
      title="评论加载失败"
      class="comment-error"
    >
      <el-button size="small" @click="loadComments(true)">重试</el-button>
    </el-alert>

    <el-skeleton v-else-if="loading" animated :rows="4" class="comment-loading" />

    <div v-else-if="comments.length === 0" class="comment-empty">
      还没有评论。可以留下第一条著录补充或使用问题。
    </div>

    <ul v-else class="comment-list">
      <li
        v-for="comment in comments"
        :key="comment.id"
        class="comment-item"
        :class="{ 'is-reply': comment.parent_id, deleted: comment.is_deleted }"
      >
        <div class="comment-avatar" aria-hidden="true">{{ initial(comment.author_name) }}</div>
        <div class="comment-body">
          <div class="comment-head">
            <strong>{{ comment.author_name || '用户' }}</strong>
            <el-tag v-if="comment.author_role !== 'user'" size="small" effect="plain">
              {{ roleLabel(comment.author_role) }}
            </el-tag>
            <span v-if="comment.reply_to_name" class="reply-to">回复 {{ comment.reply_to_name }}</span>
            <time class="comment-time">{{ formatDate(comment.created_at, 'YYYY-MM-DD HH:mm') }}</time>
          </div>

          <template v-if="editingId === comment.id">
            <el-input v-model="editContent" type="textarea" :rows="3" maxlength="2000" show-word-limit />
            <div class="comment-actions">
              <el-button size="small" type="primary" :loading="savingEdit" @click="saveEdit(comment)">
                保存
              </el-button>
              <el-button size="small" @click="cancelEdit">取消</el-button>
            </div>
          </template>
          <template v-else>
            <p class="comment-content">{{ comment.content }}</p>
            <div class="comment-actions">
              <el-button link size="small" @click="startReply(comment)">回复</el-button>
              <el-button
                v-if="comment.is_own"
                link
                size="small"
                @click="startEdit(comment)"
              >
                编辑
              </el-button>
              <el-button
                v-if="comment.can_delete"
                link
                size="small"
                type="danger"
                :loading="deletingId === comment.id"
                @click="removeComment(comment)"
              >
                删除
              </el-button>
              <span v-if="comment.updated_at && comment.updated_at !== comment.created_at" class="edited-tag">
                已编辑
              </span>
            </div>
          </template>
        </div>
      </li>
    </ul>

    <div v-if="comments.length < total" class="load-more">
      <el-button :loading="loadingMore" @click="loadMore">加载更多评论</el-button>
    </div>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { assetApi } from '@/api/modules'
import { formatDate } from '@/utils'

const props = defineProps({
  assetId: { type: String, required: true }
})

const comments = ref([])
const total = ref(0)
const page = ref(1)
const perPage = 20
const loading = ref(true)
const loadingMore = ref(false)
const loadError = ref(false)
const content = ref('')
const composerRef = ref()
const submitting = ref(false)
const replyTo = ref(null)
const editingId = ref(null)
const editContent = ref('')
const savingEdit = ref(false)
const deletingId = ref(null)

const ROLE_LABELS = {
  admin: '管理员',
  asset_admin: '资产管理员',
  license_admin: '授权管理员',
  adm1: '一级审批员',
  adm2: '二级审批员'
}

function roleLabel(role) {
  return ROLE_LABELS[role] || '用户'
}

function initial(name) {
  return (name || '用').charAt(0).toUpperCase()
}

async function loadComments(reset = false) {
  if (reset) {
    page.value = 1
    comments.value = []
    loading.value = true
  }
  loadError.value = false
  try {
    const response = await assetApi.getComments(props.assetId, {
      page: page.value,
      per_page: perPage
    })
    if (response.data?.code === 200) {
      const data = response.data.data
      comments.value = reset ? (data.items || []) : comments.value.concat(data.items || [])
      total.value = data.total || 0
    } else {
      loadError.value = true
    }
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

async function loadMore() {
  if (loadingMore.value) return
  loadingMore.value = true
  page.value += 1
  await loadComments(false)
}

async function submitComment() {
  const text = content.value.trim()
  if (!text || submitting.value) return
  submitting.value = true
  try {
    const response = await assetApi.createComment(props.assetId, {
      content: text,
      parent_id: replyTo.value?.id || undefined
    })
    if (response.data?.code === 200) {
      content.value = ''
      replyTo.value = null
      ElMessage.success('评论已发表')
      await loadComments(true)
    } else {
      ElMessage.error(response.data?.message || '评论失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '评论失败')
  } finally {
    submitting.value = false
  }
}

function startReply(comment) {
  replyTo.value = comment
  content.value = ''
  composerRef.value?.focus()
}

function cancelReply() {
  replyTo.value = null
}

function startEdit(comment) {
  editingId.value = comment.id
  editContent.value = comment.content
}

function cancelEdit() {
  editingId.value = null
  editContent.value = ''
}

async function saveEdit(comment) {
  const text = editContent.value.trim()
  if (!text || savingEdit.value) return
  savingEdit.value = true
  try {
    const response = await assetApi.updateComment(props.assetId, comment.id, { content: text })
    if (response.data?.code === 200) {
      comment.content = text
      comment.updated_at = response.data.data?.updated_at || comment.updated_at
      ElMessage.success('评论已更新')
      cancelEdit()
    } else {
      ElMessage.error(response.data?.message || '更新失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '更新失败')
  } finally {
    savingEdit.value = false
  }
}

async function removeComment(comment) {
  try {
    await ElMessageBox.confirm('删除后无法恢复，确定删除这条评论？', '删除评论', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }
  deletingId.value = comment.id
  try {
    const response = await assetApi.deleteComment(props.assetId, comment.id)
    if (response.data?.code === 200) {
      ElMessage.success('评论已删除')
      await loadComments(true)
    } else {
      ElMessage.error(response.data?.message || '删除失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '删除失败')
  } finally {
    deletingId.value = null
  }
}

onMounted(() => loadComments(true))
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.comment-section {
  margin-top: $spacing-3xl;
  padding: $spacing-xl;
  border: 1px solid $border-light;
  border-radius: $radius-lg;
  background: $bg-card;
  box-shadow: $shadow-card;
}

.section-head {
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
    color: $text-placeholder;
  }
}

.comment-composer {
  padding: 14px 16px;
  margin-bottom: 18px;
  border: 1px solid $border-light;
  border-radius: $radius-md;
  background: $bg-secondary;
}

.reply-banner {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  font-size: 12px;
  color: $text-secondary;

  strong { color: $primary-color; }
}

.composer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 10px;
}

.composer-hint {
  font-size: 11px;
  color: $text-placeholder;
}

.comment-error,
.comment-loading {
  margin-bottom: 12px;
}

.comment-empty {
  padding: 26px 18px;
  text-align: center;
  border: 1px dashed $border-color;
  border-radius: $radius-md;
  background: $bg-secondary;
  font-size: 13px;
  color: $text-secondary;
}

.comment-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.comment-item {
  display: flex;
  gap: 12px;
  padding: 14px 0;
  border-bottom: 1px solid $border-light;

  &:last-child { border-bottom: none; }

  &.is-reply {
    margin-left: 42px;
    padding-left: 14px;
    border-left: 2px solid $border-light;
  }
}

.comment-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  flex: 0 0 34px;
  border-radius: 50%;
  background: rgba(47, 107, 90, 0.1);
  color: $primary-color;
  font-size: 13px;
  font-weight: 600;
}

.comment-body {
  flex: 1;
  min-width: 0;
}

.comment-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.comment-head strong {
  font-size: 13px;
  color: $text-primary;
}

.reply-to {
  font-size: 11px;
  color: $text-placeholder;
}

.comment-time {
  margin-left: auto;
  font-size: 11px;
  color: $text-placeholder;
}

.comment-content {
  margin: 6px 0 0;
  font-size: 13px;
  line-height: 1.8;
  color: $text-secondary;
  white-space: pre-wrap;
  word-break: break-word;
}

.comment-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 4px;
}

.edited-tag {
  font-size: 10px;
  color: $text-placeholder;
}

.load-more {
  display: flex;
  justify-content: center;
  margin-top: 14px;
}

@media (max-width: 720px) {
  .comment-section {
    padding: 16px;
  }

  .comment-item.is-reply {
    margin-left: 16px;
  }

  .composer-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .composer-hint {
    order: 2;
  }
}
</style>
