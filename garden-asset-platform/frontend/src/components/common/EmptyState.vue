<template>
  <div class="empty-state">
    <el-empty :description="description" :image-size="imageSize">
      <template v-if="showAction">
        <slot name="action">
          <el-button type="primary" @click="$emit('action')">{{ actionText }}</el-button>
        </slot>
      </template>
    </el-empty>
  </div>
</template>

<script setup>
defineProps({
  description: { type: String, default: '暂无数据' },
  imageSize: { type: Number, default: 160 },
  showAction: { type: Boolean, default: false },
  actionText: { type: String, default: '立即添加' }
})

defineEmits(['action'])
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.empty-state {
  padding: $spacing-2xl 0;
  text-align: center;
}
</style>
