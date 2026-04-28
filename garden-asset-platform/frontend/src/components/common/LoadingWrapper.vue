<template>
  <div class="loading-container" v-loading="loading" :element-loading-text="text">
    <slot></slot>
  </div>
</template>

<script setup>
defineProps({
  loading: { type: Boolean, default: false },
  text: { type: String, default: '加载中...' }
})
</script>

<style scoped>
.loading-container {
  min-height: 100px;
}
</style>