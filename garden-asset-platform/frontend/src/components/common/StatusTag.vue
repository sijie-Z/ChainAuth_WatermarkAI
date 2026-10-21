<template>
  <span class="status-tag" :class="tone">
    <span class="status-dot" aria-hidden="true"></span>
    {{ statusText }}
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: { type: String, default: 'pending' },
  kind: { type: String, default: 'default' },
  type: { type: String, default: 'default' },
  size: { type: String, default: 'small' },
  effect: { type: String, default: 'light' }
})

const statusConfig = {
  pending: { text: '待处理', tone: 'warning' },
  processing: { text: '处理中', tone: 'info' },
  in_progress: { text: '审批中', tone: 'warning' },
  embedded: { text: '已嵌入', tone: 'success' },
  verified: { text: '已校验', tone: 'success' },
  confirmed: { text: '已确认', tone: 'success' },
  active: { text: '生效中', tone: 'success' },
  approved: { text: '已通过', tone: 'success' },
  adm1_approved: { text: '待二级审批', tone: 'info' },
  adm2_approved: { text: '待复核', tone: 'info' },
  rejected: { text: '已拒绝', tone: 'error' },
  expired: { text: '已过期', tone: 'neutral' },
  failed: { text: '失败', tone: 'error' },
  published: { text: '已发布', tone: 'success' },
  draft: { text: '草稿', tone: 'neutral' },
  archived: { text: '已归档', tone: 'neutral' },
  deleted: { text: '已删除', tone: 'error' },
  cancelled: { text: '已取消', tone: 'neutral' },
  revoked: { text: '已撤销', tone: 'error' },
  none: { text: '未处理', tone: 'neutral' }
}

const NONE_TEXT = {
  watermark: '未嵌入',
  chain: '未存证',
  license: '未生效',
  default: '未处理'
}

const tone = computed(() => statusConfig[props.status]?.tone || 'neutral')
const statusText = computed(() => {
  if (props.status === 'none') {
    return NONE_TEXT[props.kind] || NONE_TEXT.default
  }
  return statusConfig[props.status]?.text || props.status
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.status-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 9px;
  border: 1px solid transparent;
  border-radius: $radius-xs;
  font-size: 12px;
  line-height: 1.6;
  white-space: nowrap;

  .status-dot {
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: currentColor;
  }

  &.success {
    color: $success-color;
    background: $success-bg;
    border-color: rgba(63, 125, 91, 0.25);
  }

  &.warning {
    color: $warning-color;
    background: $warning-bg;
    border-color: rgba(176, 122, 42, 0.28);
  }

  &.error {
    color: $error-color;
    background: $error-bg;
    border-color: rgba(166, 64, 47, 0.28);
  }

  &.info {
    color: $info-color;
    background: $info-bg;
    border-color: rgba(76, 110, 138, 0.25);
  }

  &.neutral {
    color: $text-secondary;
    background: $bg-secondary;
    border-color: $border-color;
  }
}
</style>
