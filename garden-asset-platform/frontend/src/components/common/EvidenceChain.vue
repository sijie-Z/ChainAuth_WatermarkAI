<template>
  <section class="evidence-chain" :class="{ compact }">
    <header
      v-if="summary && showSummary"
      class="evidence-summary"
      :class="`level-${summary.level}`"
    >
      <div class="summary-icon" aria-hidden="true">
        <el-icon><component :is="summaryIcon" /></el-icon>
      </div>
      <div class="summary-text">
        <div class="summary-title">{{ summary.label }}</div>
        <p class="summary-desc">{{ summary.description }}</p>
        <div class="summary-checks">
          <span class="check-chip" :class="stateClass(summary.watermark)">
            <span class="dot"></span>水印{{ stateLabel(summary.watermark) }}
          </span>
          <span class="check-chip" :class="stateClass(summary.chain)">
            <span class="dot"></span>存证{{ stateLabel(summary.chain) }}
          </span>
          <span class="check-chip" :class="stateClass(summary.certificate)">
            <span class="dot"></span>证书{{ stateLabel(summary.certificate) }}
          </span>
        </div>
      </div>
      <button
        v-if="summary.file_hash"
        type="button"
        class="hash-chip"
        :title="`点击复制完整 SHA-256：${summary.file_hash}`"
        @click="copyText(summary.file_hash, '文件指纹已复制')"
      >
        <span class="hash-label">SHA-256</span>
        <span class="hash-value">{{ shorten(summary.file_hash) }}</span>
        <el-icon><CopyDocument /></el-icon>
      </button>
    </header>

    <ol class="timeline" aria-label="资产证据链">
      <template v-for="item in displayItems" :key="item.key">
        <li v-if="item._divider" class="ledger-divider">
          <span>平台业务台账 · 非链上数据</span>
        </li>
        <li class="timeline-item" :class="`state-${item.state}`">
          <span class="timeline-dot" aria-hidden="true">
            <el-icon><component :is="stateIcon(item.state)" /></el-icon>
          </span>
          <div class="timeline-body">
            <div class="timeline-head">
              <h4 class="timeline-title">{{ item.title }}</h4>
              <time v-if="item.time" class="timeline-time">{{ formatTime(item.time) }}</time>
              <span class="timeline-state">{{ stateLabel(item.state) }}</span>
            </div>
            <p v-if="item.description" class="timeline-desc">{{ item.description }}</p>
            <dl v-if="hasFields(item)" class="timeline-fields">
              <div v-for="(value, label) in item.fields" :key="label" class="field-row">
                <dt>{{ label }}</dt>
                <dd>
                  <span class="field-value" :title="value">{{ shorten(value) }}</span>
                  <button
                    v-if="value && String(value).length > 16"
                    type="button"
                    class="field-copy"
                    :aria-label="`复制${label}`"
                    @click="copyText(value, `${label}已复制`)"
                  >
                    <el-icon><CopyDocument /></el-icon>
                  </button>
                </dd>
              </div>
            </dl>
            <router-link v-if="item.link" :to="item.link" class="timeline-link">
              查看详情
              <el-icon><ArrowRight /></el-icon>
            </router-link>
          </div>
        </li>
      </template>
    </ol>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  ArrowRight,
  CircleCheckFilled,
  Clock,
  CopyDocument,
  Minus,
  WarningFilled
} from '@element-plus/icons-vue'
import { copyToClipboard, formatDate } from '@/utils'

const props = defineProps({
  items: { type: Array, default: () => [] },
  summary: { type: Object, default: null },
  showSummary: { type: Boolean, default: true },
  compact: { type: Boolean, default: false }
})

const displayItems = computed(() => {
  let dividerShown = false
  return (props.items || []).map(item => {
    const showDivider = item.ledger && !dividerShown
    if (showDivider) dividerShown = true
    return { ...item, _divider: showDivider }
  })
})

const summaryIcon = computed(() => {
  const level = props.summary?.level
  if (level === 'complete') return CircleCheckFilled
  if (level === 'partial') return Clock
  return WarningFilled
})

const STATE_LABELS = {
  done: '已完成',
  pending: '处理中',
  warning: '需注意',
  missing: '未完成'
}

function stateLabel(state) {
  return STATE_LABELS[state] || '未知'
}

function stateClass(state) {
  return `state-${state || 'missing'}`
}

function stateIcon(state) {
  if (state === 'done') return CircleCheckFilled
  if (state === 'pending') return Clock
  if (state === 'warning') return WarningFilled
  return Minus
}

function formatTime(value) {
  return formatDate(value, 'YYYY-MM-DD HH:mm')
}

function shorten(value) {
  if (value === null || value === undefined) return ''
  const text = String(value)
  if (text.length <= 30) return text
  return `${text.slice(0, 14)}…${text.slice(-8)}`
}

function hasFields(item) {
  return item.fields && Object.values(item.fields).some(value => value !== '' && value !== null)
}

async function copyText(value, message) {
  const ok = await copyToClipboard(String(value))
  ElMessage[ok ? 'success' : 'error'](ok ? message : '复制失败，请手动选择文本')
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.evidence-chain {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.evidence-summary {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 18px 20px;
  border: 1px solid $border-light;
  border-left: 3px solid $primary-color;
  background: linear-gradient(135deg, rgba(47, 107, 90, 0.06), rgba(252, 253, 251, 0.9));
  border-radius: $radius-lg;

  &.level-partial {
    border-left-color: $warning-color;
    background: linear-gradient(135deg, $warning-bg, rgba(252, 253, 251, 0.9));
  }

  &.level-incomplete {
    border-left-color: $text-placeholder;
    background: linear-gradient(135deg, rgba(138, 148, 141, 0.08), rgba(252, 253, 251, 0.9));
  }
}

.summary-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  flex: 0 0 38px;
  border-radius: 50%;
  background: $success-bg;
  color: $success-color;
  font-size: 20px;

  .level-partial & {
    background: $warning-bg;
    color: $warning-color;
  }

  .level-incomplete & {
    background: rgba(138, 148, 141, 0.12);
    color: $text-secondary;
  }
}

.summary-text {
  flex: 1;
  min-width: 0;
}

.summary-title {
  font-size: 16px;
  font-weight: 600;
  color: $text-primary;
  letter-spacing: 0.02em;
}

.summary-desc {
  margin: 4px 0 10px;
  font-size: 13px;
  line-height: 1.7;
  color: $text-secondary;
}

.summary-checks {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.check-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: $radius-full;
  font-size: 12px;
  color: $text-secondary;
  background: $bg-secondary;

  .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: $text-placeholder;
  }

  &.state-done {
    color: $success-color;
    background: $success-bg;

    .dot {
      background: $success-color;
    }
  }

  &.state-pending {
    color: $warning-color;
    background: $warning-bg;

    .dot {
      background: $warning-color;
    }
  }

  &.state-warning {
    color: $error-color;
    background: $error-bg;

    .dot {
      background: $error-color;
    }
  }
}

.hash-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex: 0 0 auto;
  padding: 6px 10px;
  border: 1px dashed $border-color;
  border-radius: $radius-md;
  background: $bg-card;
  color: $text-secondary;
  font-family: $font-mono;
  font-size: 12px;
  cursor: pointer;
  transition:
    border-color 0.2s,
    color 0.2s;

  &:hover {
    border-color: $primary-light;
    color: $primary-color;
  }

  .hash-label {
    color: $text-placeholder;
    font-size: 11px;
    letter-spacing: 0.06em;
  }
}

.timeline {
  list-style: none;
  margin: 0;
  padding: 0 0 0 8px;
}

.timeline-item {
  position: relative;
  display: flex;
  gap: 14px;
  padding: 0 0 22px 0;

  &::before {
    content: '';
    position: absolute;
    left: 13px;
    top: 28px;
    bottom: 0;
    width: 1px;
    background: $border-light;
  }

  &:last-child::before {
    display: none;
  }
}

.timeline-dot {
  position: relative;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 27px;
  height: 27px;
  flex: 0 0 27px;
  border-radius: 50%;
  border: 1px solid $border-color;
  background: $bg-card;
  color: $text-placeholder;
  font-size: 14px;

  .state-done & {
    border-color: rgba(63, 125, 91, 0.35);
    background: $success-bg;
    color: $success-color;
  }

  .state-pending & {
    border-color: rgba(176, 122, 42, 0.35);
    background: $warning-bg;
    color: $warning-color;
  }

  .state-warning & {
    border-color: rgba(166, 64, 47, 0.35);
    background: $error-bg;
    color: $error-color;
  }
}

.timeline-body {
  flex: 1;
  min-width: 0;
  padding-top: 2px;
}

.timeline-head {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 10px;
}

.timeline-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: $text-primary;
  letter-spacing: 0.02em;
}

.timeline-time {
  font-family: $font-mono;
  font-size: 12px;
  color: $text-placeholder;
}

.timeline-state {
  margin-left: auto;
  font-size: 11px;
  color: $text-placeholder;

  .state-done & {
    color: $success-color;
  }
  .state-pending & {
    color: $warning-color;
  }
  .state-warning & {
    color: $error-color;
  }
}

.timeline-desc {
  margin: 5px 0 0;
  font-size: 13px;
  line-height: 1.65;
  color: $text-secondary;
}

.timeline-fields {
  margin: 10px 0 0;
  padding: 10px 12px;
  border-radius: $radius-md;
  background: $bg-secondary;
  display: grid;
  gap: 6px;
}

.field-row {
  display: flex;
  gap: 12px;
  font-size: 12px;
  line-height: 1.6;

  dt {
    flex: 0 0 88px;
    color: $text-placeholder;
  }

  dd {
    margin: 0;
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 6px;
    color: $text-secondary;
  }
}

.field-value {
  font-family: $font-mono;
  word-break: break-all;
}

.field-copy {
  display: inline-flex;
  padding: 2px;
  border: none;
  background: transparent;
  color: $text-placeholder;
  cursor: pointer;

  &:hover {
    color: $primary-color;
  }
}

.timeline-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
  font-size: 12px;
  color: $primary-color;
  text-decoration: none;

  &:hover {
    text-decoration: underline;
  }
}

.ledger-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 2px 0 18px 40px;
  font-size: 11px;
  letter-spacing: 0.08em;
  color: $text-placeholder;

  &::before,
  &::after {
    content: '';
    flex: 1;
    height: 1px;
    background: $border-light;
  }
}

.evidence-chain.compact {
  .evidence-summary {
    padding: 14px 16px;
  }

  .timeline-item {
    padding-bottom: 18px;
  }
}

@media (max-width: 720px) {
  .evidence-summary {
    flex-wrap: wrap;
  }

  .hash-chip {
    width: 100%;
    justify-content: space-between;
  }

  .field-row {
    flex-direction: column;
    gap: 1px;

    dt {
      flex: none;
    }
  }

  .ledger-divider {
    margin-left: 0;
  }
}
</style>
