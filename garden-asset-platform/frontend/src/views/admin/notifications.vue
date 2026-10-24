<template>
  <div class="notifications-page">
    <header class="page-head">
      <div>
        <h1 class="page-title">通知渠道</h1>
        <p class="page-subtitle">站内 SSE、邮件与系统 Webhook 的配置和投递状态</p>
      </div>
      <el-button :loading="loading" @click="loadAll">刷新</el-button>
    </header>

    <section class="channel-grid">
      <div class="channel-card">
        <div class="channel-head">
          <span class="channel-icon"><el-icon><Bell /></el-icon></span>
          <el-tag size="small" :type="status?.notifications?.sse_enabled ? 'success' : 'info'">
            {{ status?.notifications?.sse_enabled ? '已启用' : '未启用' }}
          </el-tag>
        </div>
        <h3>站内实时通知</h3>
        <p>审核、授权、任务结果通过 SSE 推送到顶栏铃铛，无需刷新。</p>
      </div>
      <div class="channel-card">
        <div class="channel-head">
          <span class="channel-icon"><el-icon><Message /></el-icon></span>
          <el-tag size="small" :type="status?.notifications?.mail_configured ? 'success' : 'info'">
            {{ status?.notifications?.mail_configured ? 'SMTP 已配置' : 'SMTP 未配置' }}
          </el-tag>
        </div>
        <h3>邮件通知</h3>
        <p>
          待发 {{ status?.notifications?.deliveries?.pending || 0 }} ·
          已发 {{ status?.notifications?.deliveries?.sent || 0 }} ·
          失败 {{ status?.notifications?.deliveries?.failed || 0 }}
        </p>
      </div>
      <div class="channel-card">
        <div class="channel-head">
          <span class="channel-icon"><el-icon><Connection /></el-icon></span>
          <el-tag size="small" :type="webhookConfig.enabled ? 'success' : 'info'">
            {{ webhookConfig.enabled ? '已启用' : '未启用' }}
          </el-tag>
        </div>
        <h3>Webhook</h3>
        <p>
          待发 {{ webhookDeliveries.pending || 0 }} ·
          已发 {{ webhookDeliveries.sent || 0 }} ·
          失败 {{ webhookDeliveries.failed || 0 }}
        </p>
      </div>
    </section>

    <section class="config-card">
      <header class="card-head">
        <div>
          <h2>系统 Webhook</h2>
          <p>支持通用 JSON 接收端和企业微信群机器人；每个事件会带 HMAC-SHA256 签名。</p>
        </div>
        <el-tag v-if="!webhookConfig.enabled" size="small" type="info">未启用</el-tag>
      </header>

      <el-form label-width="110px" class="webhook-form" v-loading="loading">
        <el-form-item label="启用">
          <el-switch v-model="webhookForm.enabled" />
        </el-form-item>
        <el-form-item label="接收地址">
          <el-input
            v-model="webhookForm.url"
            placeholder="https://example.com/webhook 或企业微信机器人地址"
            maxlength="500"
          />
        </el-form-item>
        <el-form-item label="载荷格式">
          <el-radio-group v-model="webhookForm.format">
            <el-radio-button value="json">通用 JSON</el-radio-button>
            <el-radio-button value="wecom">企业微信群机器人</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="签名密钥">
          <el-input
            v-model="webhookForm.secret"
            type="password"
            show-password
            :placeholder="webhookConfig.secret_set ? '已设置，留空保持不变' : '可选，用于 HMAC-SHA256 签名'"
            maxlength="200"
          />
          <el-checkbox v-if="webhookConfig.secret_set" v-model="clearSecret" class="clear-secret">
            清除已有密钥
          </el-checkbox>
        </el-form-item>
        <el-form-item label="订阅分组">
          <el-checkbox-group v-model="webhookForm.groups">
            <el-checkbox
              v-for="group in groupOptions"
              :key="group.key"
              :label="group.key"
            >
              {{ group.label }}
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="saving" @click="saveConfig">保存配置</el-button>
          <el-button
            :loading="testing"
            :disabled="!webhookConfig.enabled"
            @click="testWebhook"
          >
            发送测试
          </el-button>
        </el-form-item>
      </el-form>

      <el-alert
        v-if="!webhookConfig.allow_private"
        type="info"
        :closable="false"
        show-icon
        class="security-note"
        title="内网地址保护已开启"
        description="Webhook 默认拒绝指向内网/回环地址，避免 SSRF；内部自动化可设置 WEBHOOK_ALLOW_PRIVATE=true。"
      />
    </section>

    <section class="table-card">
      <header class="card-head">
        <h2>最近 Webhook 投递</h2>
        <span>失败会按 1/2/3 分钟退避重试，3 次后标记失败</span>
      </header>
      <el-table :data="recentDeliveries" size="small">
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="事件" min-width="240">
          <template #default="{ row }">
            {{ row.event_title || `事件 #${row.event_id}` }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="deliveryType(row.status)" effect="plain">
              {{ deliveryLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="attempts" label="尝试" width="80" />
        <el-table-column label="错误" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="danger-text">{{ row.error_message || '—' }}</span>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!loading && recentDeliveries.length === 0" class="empty-block">
        <el-empty description="暂无 Webhook 投递记录" :image-size="64" />
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Bell, Connection, Message } from '@element-plus/icons-vue'
import { parseBackendDate } from '@/utils'
import { systemApi } from '@/api/modules'

const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const status = ref(null)
const webhookConfig = ref({})
const webhookDeliveries = ref({})
const recentDeliveries = ref([])
const groupOptions = ref([
  { key: 'asset', label: '资产审核结果' },
  { key: 'license', label: '授权审批与履约' },
  { key: 'task', label: '水印/存证任务' },
  { key: 'infringement', label: '侵权线索' }
])
const clearSecret = ref(false)
const webhookForm = reactive({
  enabled: false,
  url: '',
  format: 'json',
  secret: '',
  groups: ['asset', 'license', 'task', 'infringement']
})

const DELIVERY_LABELS = {
  pending: '待发送',
  sent: '已发送',
  skipped: '已跳过',
  failed: '失败'
}

function deliveryLabel(statusValue) {
  return DELIVERY_LABELS[statusValue] || statusValue
}

function deliveryType(statusValue) {
  return {
    pending: 'warning',
    sent: 'success',
    skipped: 'info',
    failed: 'danger'
  }[statusValue] || 'info'
}

function formatTime(value) {
  const date = parseBackendDate(value)
  return date ? date.toLocaleString('zh-CN') : '—'
}

function applyConfig(config) {
  webhookConfig.value = config || {}
  webhookForm.enabled = Boolean(config?.enabled)
  webhookForm.url = config?.url || ''
  webhookForm.format = config?.format || 'json'
  webhookForm.groups = config?.groups || []
  webhookForm.secret = ''
  clearSecret.value = false
}

async function loadAll() {
  loading.value = true
  try {
    const [statusResponse, webhookResponse] = await Promise.all([
      systemApi.getStatus(),
      systemApi.getWebhook()
    ])
    if (statusResponse.data?.code === 200) {
      status.value = statusResponse.data.data
    }
    if (webhookResponse.data?.code === 200) {
      const data = webhookResponse.data.data || {}
      applyConfig(data.config)
      webhookDeliveries.value = data.deliveries || {}
      recentDeliveries.value = data.recent || []
      if (Array.isArray(data.groups) && data.groups.length) {
        groupOptions.value = data.groups
      }
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '通知渠道加载失败')
  } finally {
    loading.value = false
  }
}

async function saveConfig() {
  saving.value = true
  try {
    const response = await systemApi.updateWebhook({
      enabled: webhookForm.enabled,
      url: webhookForm.url.trim(),
      format: webhookForm.format,
      groups: webhookForm.groups,
      secret: webhookForm.secret,
      clear_secret: clearSecret.value
    })
    if (response.data?.code === 200) {
      ElMessage.success('Webhook 配置已保存')
      applyConfig(response.data.data)
      await loadAll()
    } else {
      ElMessage.error(response.data?.message || '保存失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function testWebhook() {
  testing.value = true
  try {
    const response = await systemApi.testWebhook()
    ElMessage.success(response.data?.message || '测试 Webhook 已发送')
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '测试 Webhook 发送失败')
  } finally {
    testing.value = false
  }
}

onMounted(loadAll)
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.notifications-page {
  min-height: 100%;
  padding: 24px 28px 32px;
}

.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: $spacing-lg;
  margin-bottom: $spacing-xl;

  .page-title {
    margin-bottom: 4px;
    font-family: $font-display;
    font-size: 22px;
    font-weight: 600;
    color: $text-primary;
  }

  .page-subtitle {
    font-size: 13px;
    color: $text-secondary;
  }
}

.channel-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: $spacing-lg;
}

.channel-card {
  padding: 18px;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-lg;

  h3 {
    margin: 12px 0 6px;
    font-family: $font-display;
    font-size: 15px;
    color: $text-primary;
  }

  p {
    margin: 0;
    font-size: 12px;
    line-height: 1.7;
    color: $text-secondary;
  }
}

.channel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.channel-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: $radius-sm;
  background: $bg-secondary;
  color: $primary-dark;
}

.config-card,
.table-card {
  padding: 20px 22px;
  margin-bottom: $spacing-lg;
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
}

.card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;

  h2 {
    margin: 0 0 4px;
    font-family: $font-display;
    font-size: 17px;
    color: $text-primary;
  }

  p,
  span {
    margin: 0;
    font-size: 12px;
    color: $text-placeholder;
  }
}

.webhook-form {
  max-width: 760px;
}

.clear-secret {
  margin-left: 12px;
}

.security-note {
  max-width: 760px;
}

.empty-block {
  padding: 16px 0;
}

.danger-text {
  color: $error-color;
}

@media (max-width: $breakpoint-md) {
  .notifications-page {
    padding: 16px;
  }

  .page-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .channel-grid {
    grid-template-columns: 1fr;
  }
}
</style>
