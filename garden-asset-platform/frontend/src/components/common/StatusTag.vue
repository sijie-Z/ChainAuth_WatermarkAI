<template>
  <div class="status-tag" :class="`status-${status}`">
    <el-tag :type="tagType" size="small">
      <el-icon v-if="showIcon"><component :is="statusIcon" /></el-icon>
      {{ statusText }}
    </el-tag>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { CircleCheck, CircleClose, Loading, Clock } from '@element-plus/icons-vue'

const props = defineProps({
  status: { type: String, default: 'pending' },
  type: { type: String, default: 'default' } // asset, watermark, license, blockchain
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
  failed: { text: '失败', tag: 'danger', icon: CircleClose }
}

const tagType = computed(() => statusConfig[props.status]?.tag || 'info')
const statusText = computed(() => statusConfig[props.status]?.text || props.status)
const statusIcon = computed(() => statusConfig[props.status]?.icon || Clock)
const showIcon = computed(() => props.type !== 'default')
</script>

<style scoped>
.status-tag {
  display: inline-flex;
}
</style>