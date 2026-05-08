<template>
  <el-tag :type="tagType" :size="size" :effect="effect">
    <el-icon v-if="showIcon" class="tag-icon"><component :is="statusIcon" /></el-icon>
    {{ statusText }}
  </el-tag>
</template>

<script setup>
import { computed } from 'vue'
import { CircleCheck, CircleClose, Loading, Clock, Warning } from '@element-plus/icons-vue'

const props = defineProps({
  status: { type: String, default: 'pending' },
  type: { type: String, default: 'default' },
  size: { type: String, default: 'small' },
  effect: { type: String, default: 'light' }
})

const statusConfig = {
  pending: { text: '待处理', tag: 'warning', icon: Clock },
  processing: { text: '处理中', tag: 'info', icon: Loading },
  embedded: { text: '已嵌入', tag: 'success', icon: CircleCheck },
  confirmed: { text: '已确认', tag: 'success', icon: CircleCheck },
  active: { text: '生效中', tag: 'success', icon: CircleCheck },
  approved: { text: '已通过', tag: 'success', icon: CircleCheck },
  rejected: { text: '已拒绝', tag: 'danger', icon: CircleClose },
  expired: { text: '已过期', tag: 'info', icon: Clock },
  failed: { text: '失败', tag: 'danger', icon: CircleClose },
  published: { text: '已发布', tag: 'success', icon: CircleCheck },
  draft: { text: '草稿', tag: 'info', icon: Warning },
  revoked: { text: '已撤销', tag: 'danger', icon: CircleClose }
}

const tagType = computed(() => statusConfig[props.status]?.tag || 'info')
const statusText = computed(() => statusConfig[props.status]?.text || props.status)
const statusIcon = computed(() => statusConfig[props.status]?.icon || Clock)
const showIcon = computed(() => props.type !== 'default')
</script>

<style scoped>
.tag-icon {
  margin-right: 4px;
  vertical-align: middle;
}
</style>
