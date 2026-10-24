<template>
  <el-config-provider :locale="zhCn" size="default">
    <SiteHeader v-if="showSiteHeader" />
    <ErrorBoundary>
      <router-view v-slot="{ Component, route }">
        <component
          :is="Component"
          :key="route.matched[0]?.path === '/admin' ? '/admin' : route.path"
        />
      </router-view>
    </ErrorBoundary>
    <CommandPalette />
  </el-config-provider>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import { useUserStore } from '@/stores/user'
import SiteHeader from '@/components/common/SiteHeader.vue'
import CommandPalette from '@/components/common/CommandPalette.vue'

const route = useRoute()
const userStore = useUserStore()

const showSiteHeader = computed(() =>
  route.matched.some(record => record.meta.siteHeader)
)

onMounted(() => {
  userStore.initStore()
})
</script>

<style lang="scss">
#app {
  width: 100%;
  min-height: 100vh;
  background: #f4f6f3;
}

img {
  max-width: 100%;
  height: auto;
  vertical-align: middle;
}

// 工具类
.text-center { text-align: center; }
.text-left { text-align: left; }
.text-right { text-align: right; }

.flex { display: flex; }
.flex-1 { flex: 1; }
.items-center { align-items: center; }
.justify-center { justify-content: center; }
.justify-between { justify-content: space-between; }
.gap-1 { gap: 4px; }
.gap-2 { gap: 8px; }
.gap-3 { gap: 12px; }
.gap-4 { gap: 16px; }

@media print {
  .site-header {
    display: none !important;
  }
}

.mt-1 { margin-top: 4px; }
.mt-2 { margin-top: 8px; }
.mt-3 { margin-top: 12px; }
.mt-4 { margin-top: 16px; }
.mb-1 { margin-bottom: 4px; }
.mb-2 { margin-bottom: 8px; }
.mb-3 { margin-bottom: 12px; }
.mb-4 { margin-bottom: 16px; }

.p-1 { padding: 4px; }
.p-2 { padding: 8px; }
.p-3 { padding: 12px; }
.p-4 { padding: 16px; }

.w-full { width: 100%; }
.h-full { height: 100%; }
</style>
