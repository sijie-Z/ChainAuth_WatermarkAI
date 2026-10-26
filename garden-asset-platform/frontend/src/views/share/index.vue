<template>
  <div class="share-page">
    <header class="share-topbar">
      <router-link to="/home" class="share-brand">
        <span class="share-mark">园</span>
        <span class="share-brand-text">
          <strong>苏州园林数字资产</strong>
          <small>公开分享与溯源核验</small>
        </span>
      </router-link>
      <router-link to="/home" class="share-home-link">
        进入平台
        <el-icon><ArrowRight /></el-icon>
      </router-link>
    </header>

    <main class="share-main">
      <el-skeleton v-if="loading" animated class="share-skeleton">
        <template #template>
          <el-skeleton-item variant="rect" style="height: 120px; border-radius: 8px" />
          <el-skeleton-item
            variant="rect"
            style="height: 320px; margin-top: 20px; border-radius: 8px"
          />
          <el-skeleton-item
            variant="rect"
            style="height: 420px; margin-top: 20px; border-radius: 8px"
          />
        </template>
      </el-skeleton>

      <section v-else-if="requiresCode" class="gate-card">
        <div class="gate-icon">
          <el-icon><Lock /></el-icon>
        </div>
        <h1>该分享需要访问码</h1>
        <p>请输入分享者提供的访问码后查看资产与证据链。</p>
        <form class="gate-form" @submit.prevent="loadShare">
          <el-input
            v-model="accessCode"
            placeholder="访问码"
            maxlength="32"
            show-password
            autofocus
            @keyup.enter="loadShare"
          />
          <el-button type="primary" :loading="loading" native-type="submit">查看分享</el-button>
        </form>
        <p v-if="errorMessage" class="gate-error">{{ errorMessage }}</p>
      </section>

      <section v-else-if="errorMessage" class="error-card">
        <el-icon class="error-icon"><Link /></el-icon>
        <h1>{{ errorTitle }}</h1>
        <p>{{ errorMessage }}</p>
        <el-button type="primary" plain @click="$router.push('/home')">返回平台首页</el-button>
      </section>

      <template v-else-if="asset">
        <section class="share-hero">
          <div class="share-cover">
            <img
              :src="thumbnailUrl"
              :alt="asset.title"
              @error="thumbnailFailed = true"
              v-if="!thumbnailFailed"
            />
            <div v-else class="cover-fallback">
              <el-icon><Picture /></el-icon>
              <span>暂无预览图</span>
            </div>
          </div>
          <div class="share-info">
            <div class="share-kicker">
              <span class="kicker-label">资产分享</span>
              <span class="kicker-code">{{ asset.asset_code }}</span>
            </div>
            <h1 class="share-title">{{ asset.title }}</h1>
            <p class="share-meta">
              <span v-if="asset.garden_name">{{ asset.garden_name }}</span>
              <span v-if="asset.file_format">{{ asset.file_format }}</span>
              <span v-if="asset.file_size">{{ formatFileSize(asset.file_size) }}</span>
              <span v-if="asset.created_at">{{ formatDate(asset.created_at) }} 登记</span>
            </p>
            <p v-if="asset.description" class="share-desc">{{ asset.description }}</p>
            <div v-if="asset.tags?.length" class="share-tags">
              <el-tag v-for="tag in asset.tags" :key="tag" size="small" effect="plain">{{
                tag
              }}</el-tag>
            </div>
            <div class="share-actions">
              <el-button
                v-if="asset.share.allow_download"
                type="primary"
                :loading="downloading"
                :disabled="asset.share.download_remaining === 0"
                @click="downloadAsset"
              >
                <el-icon><Download /></el-icon>
                {{ asset.share.download_remaining === 0 ? '下载次数已用完' : '下载文件' }}
              </el-button>
              <el-button @click="copyShareLink">
                <el-icon><CopyDocument /></el-icon>
                复制分享链接
              </el-button>
            </div>
            <p class="share-limits">
              <template v-if="asset.share.allow_download">
                下载 {{ asset.share.download_count }} 次<template v-if="asset.share.max_downloads">
                  / 上限 {{ asset.share.max_downloads }} 次</template
                >
              </template>
              <template v-else>分享者未开放下载，仅可在线查看</template>
              <span class="dot-sep">·</span>
              <template v-if="asset.share.expires_at"
                >{{ formatDate(asset.share.expires_at) }} 到期</template
              >
              <template v-else>长期有效</template>
            </p>
          </div>
        </section>

        <section class="share-section">
          <div class="section-heading">
            <div>
              <h2>溯源证据链</h2>
              <p>上传、水印、链上存证与证书按时间排列；缺失环节会如实标注。</p>
            </div>
            <router-link
              v-if="asset.certificate_id"
              :to="`/certificate/${asset.certificate_id}`"
              class="section-link"
            >
              查看存证证书
              <el-icon><ArrowRight /></el-icon>
            </router-link>
          </div>
          <EvidenceChain :items="evidence.items" :summary="evidence.summary" />
        </section>

        <footer class="share-footer">
          <p>
            本页由苏州园林数字资产平台生成，用于说明该文件与平台登记记录一致；
            存证结论不构成权属的最终判定。
          </p>
          <p v-if="asset.owner_name">权利人：{{ asset.owner_name }}</p>
        </footer>
      </template>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowRight, CopyDocument, Download, Link, Lock, Picture } from '@element-plus/icons-vue'
import { shareApi } from '@/api/modules'
import { startShareDownload } from '@/utils/download'
import { copyToClipboard, formatDate, formatFileSize } from '@/utils'
import EvidenceChain from '@/components/common/EvidenceChain.vue'

const route = useRoute()
const token = computed(() => route.params.token)

const loading = ref(false)
const downloading = ref(false)
const requiresCode = ref(false)
const accessCode = ref('')
const errorMessage = ref('')
const errorTitle = ref('分享链接不可用')
const asset = ref(null)
const evidence = ref({ items: [], summary: null })
const thumbnailFailed = ref(false)

const thumbnailUrl = computed(() => {
  if (!asset.value) return ''
  return `${asset.value.thumbnail_url}${asset.value.thumbnail_url.includes('?') ? '&' : '?'}v=share`
})

function parseError(error) {
  const response = error?.response
  if (!response) {
    return { status: 0, message: '网络连接失败，请稍后重试' }
  }
  const data = response.data || {}
  if (data instanceof Blob) {
    return { status: response.status, message: '请求失败，请稍后重试' }
  }
  return {
    status: response.status,
    message: data.message || '请求失败，请稍后重试'
  }
}

async function loadShare() {
  if (loading.value) return
  if (requiresCode.value && !accessCode.value.trim()) {
    errorMessage.value = '请输入访问码'
    return
  }

  loading.value = true
  errorMessage.value = ''
  try {
    const params = accessCode.value.trim() ? { code: accessCode.value.trim() } : {}
    const response = await shareApi.get(token.value, params)
    if (response.data?.code === 200) {
      asset.value = response.data.data.asset
      evidence.value = response.data.data.evidence || { items: [], summary: null }
      requiresCode.value = false
      errorTitle.value = ''
      document.title = `${asset.value.title} - 资产分享 - 苏州园林数字资产平台`
    } else {
      errorMessage.value = response.data?.message || '分享链接不可用'
    }
  } catch (error) {
    const parsed = parseError(error)
    if (parsed.status === 401) {
      requiresCode.value = true
      errorMessage.value = accessCode.value ? '访问码不正确，请重新输入' : ''
      errorTitle.value = '该分享需要访问码'
      return
    }
    errorTitle.value = parsed.status === 410 ? '分享链接已失效' : '分享链接不可用'
    errorMessage.value = parsed.message
  } finally {
    loading.value = false
  }
}

async function downloadAsset() {
  if (downloading.value) return
  downloading.value = true
  try {
    await startShareDownload(token.value, accessCode.value.trim())
    if (asset.value?.share) {
      asset.value.share.download_count += 1
      if (asset.value.share.download_remaining !== null) {
        asset.value.share.download_remaining = Math.max(asset.value.share.download_remaining - 1, 0)
      }
    }
    ElMessage.success('已发起下载，请在浏览器下载列表中查看')
  } catch (error) {
    const parsed = parseError(error)
    ElMessage.error(parsed.message)
  } finally {
    downloading.value = false
  }
}

async function copyShareLink() {
  const ok = await copyToClipboard(window.location.href)
  ElMessage[ok ? 'success' : 'error'](ok ? '分享链接已复制' : '复制失败，请手动复制地址栏')
}

onMounted(loadShare)
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.share-page {
  min-height: 100vh;
  background-color: $bg-primary;
  background-image:
    radial-gradient(circle at 8% 0%, rgba(47, 107, 90, 0.06), transparent 38%),
    radial-gradient(circle at 92% 18%, rgba(76, 110, 138, 0.05), transparent 36%);
}

.share-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 1080px;
  margin: 0 auto;
  padding: 22px 28px;
}

.share-brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
}

.share-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 4px;
  background: $primary-color;
  color: #f7f4ec;
  font-family: $font-display;
  font-size: 20px;
}

.share-brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.3;

  strong {
    font-size: 15px;
    color: $text-primary;
    letter-spacing: 0.04em;
  }

  small {
    font-size: 11px;
    color: $text-placeholder;
    letter-spacing: 0.12em;
  }
}

.share-home-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: $text-secondary;
  text-decoration: none;

  &:hover {
    color: $primary-color;
  }
}

.share-main {
  max-width: 1080px;
  margin: 0 auto;
  padding: 12px 28px 60px;
}

.share-skeleton {
  display: block;
}

.gate-card,
.error-card {
  max-width: 460px;
  margin: 10vh auto 0;
  padding: 36px 32px;
  text-align: center;
  background: $bg-card;
  border: 1px solid $border-light;
  border-radius: $radius-lg;
  box-shadow: $shadow-card;

  h1 {
    margin: 16px 0 8px;
    font-family: $font-display;
    font-size: 22px;
    color: $text-primary;
  }

  p {
    margin: 0 0 20px;
    font-size: 13px;
    line-height: 1.7;
    color: $text-secondary;
  }
}

.gate-icon,
.error-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: $bg-secondary;
  color: $primary-color;
  font-size: 24px;
}

.gate-form {
  display: flex;
  gap: 10px;

  :deep(.el-input) {
    flex: 1;
  }
}

.gate-error {
  margin: 12px 0 0;
  color: $error-color;
  font-size: 12px;
}

.share-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr);
  gap: 32px;
  padding: 26px;
  background: $bg-card;
  border: 1px solid $border-light;
  border-radius: $radius-lg;
  box-shadow: $shadow-card;
}

.share-cover {
  min-height: 320px;
  border-radius: $radius-md;
  overflow: hidden;
  background: $bg-secondary;

  img {
    width: 100%;
    height: 100%;
    max-height: 460px;
    object-fit: cover;
    display: block;
  }
}

.cover-fallback {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 100%;
  min-height: 320px;
  color: $text-placeholder;
  font-size: 13px;

  .el-icon {
    font-size: 32px;
  }
}

.share-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.share-kicker {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.kicker-label {
  padding: 2px 8px;
  border: 1px solid rgba(166, 64, 47, 0.3);
  border-radius: $radius-sm;
  color: $accent-color;
  font-size: 11px;
  letter-spacing: 0.14em;
}

.kicker-code {
  font-family: $font-mono;
  font-size: 12px;
  color: $text-placeholder;
}

.share-title {
  margin: 0;
  font-family: $font-display;
  font-size: 28px;
  line-height: 1.35;
  color: $text-primary;
  letter-spacing: 0.02em;
}

.share-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 12px;
  margin: 12px 0 0;
  font-size: 12px;
  color: $text-secondary;

  span + span::before {
    content: '·';
    margin-right: 12px;
    color: $border-dark;
  }
}

.share-desc {
  margin: 16px 0 0;
  font-size: 14px;
  line-height: 1.8;
  color: $text-secondary;
  white-space: pre-wrap;
}

.share-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 14px;
}

.share-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: auto;
  padding-top: 24px;
}

.share-limits {
  margin: 12px 0 0;
  font-size: 12px;
  color: $text-placeholder;

  .dot-sep {
    margin: 0 6px;
  }
}

.share-section {
  margin-top: 26px;
  padding: 28px 30px;
  background: $bg-card;
  border: 1px solid $border-light;
  border-radius: $radius-lg;
  box-shadow: $shadow-card;
}

.section-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
  margin-bottom: 22px;

  h2 {
    margin: 0;
    font-family: $font-display;
    font-size: 20px;
    color: $text-primary;
  }

  p {
    margin: 6px 0 0;
    font-size: 12px;
    color: $text-secondary;
  }
}

.section-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex: 0 0 auto;
  font-size: 13px;
  color: $primary-color;
  text-decoration: none;

  &:hover {
    text-decoration: underline;
  }
}

.share-footer {
  margin-top: 24px;
  padding: 0 6px;
  font-size: 12px;
  line-height: 1.8;
  color: $text-placeholder;

  p {
    margin: 4px 0;
  }
}

@media (max-width: 860px) {
  .share-hero {
    grid-template-columns: 1fr;
    gap: 20px;
    padding: 18px;
  }

  .share-cover,
  .cover-fallback {
    min-height: 220px;
  }

  .share-title {
    font-size: 23px;
  }

  .share-section {
    padding: 20px 18px;
  }

  .section-heading {
    flex-direction: column;
    gap: 10px;
  }
}

@media (max-width: 560px) {
  .share-topbar,
  .share-main {
    padding-left: 16px;
    padding-right: 16px;
  }

  .share-brand-text small {
    display: none;
  }

  .gate-form {
    flex-direction: column;
  }

  .share-actions :deep(.el-button) {
    width: 100%;
    margin-left: 0;
  }
}
</style>
