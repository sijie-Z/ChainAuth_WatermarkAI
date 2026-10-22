<template>
  <div class="settings-page">
    <header class="page-bar">
      <router-link to="/home" class="page-back">
        <el-icon><ArrowLeft /></el-icon>
        返回首页
      </router-link>
      <h1 class="page-title">账号设置</h1>
    </header>

    <div class="settings-container">
      <div class="settings-grid">
        <!-- 个人信息 -->
        <el-card class="settings-card">
          <template #header>
            <div class="card-header">
              <el-icon class="card-icon"><User /></el-icon>
              <span>个人信息</span>
            </div>
          </template>
          <el-form :model="profileForm" label-width="80px" label-position="left">
            <el-form-item label="用户名">
              <el-input v-model="profileForm.username" disabled />
            </el-form-item>
            <el-form-item label="角色">
              <el-tag>{{ roleLabel }}</el-tag>
            </el-form-item>
            <el-form-item label="邮箱">
              <el-input v-model="profileForm.email" placeholder="未设置" />
            </el-form-item>
            <el-form-item label="手机号">
              <el-input v-model="profileForm.phone" placeholder="未设置" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveProfile" :loading="saving">
                保存修改
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 修改密码 -->
        <el-card class="settings-card">
          <template #header>
            <div class="card-header">
              <el-icon class="card-icon"><Lock /></el-icon>
              <span>修改密码</span>
            </div>
          </template>
          <el-form
            ref="passwordFormRef"
            :model="passwordForm"
            :rules="passwordRules"
            label-width="100px"
            label-position="left"
          >
            <el-form-item label="当前密码" prop="currentPassword">
              <el-input
                v-model="passwordForm.currentPassword"
                type="password"
                show-password
                placeholder="请输入当前密码"
              />
            </el-form-item>
            <el-form-item label="新密码" prop="newPassword">
              <el-input
                v-model="passwordForm.newPassword"
                type="password"
                show-password
                placeholder="请输入新密码（至少6位）"
              />
            </el-form-item>
            <el-form-item label="确认密码" prop="confirmPassword">
              <el-input
                v-model="passwordForm.confirmPassword"
                type="password"
                show-password
                placeholder="请再次输入新密码"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="changePassword" :loading="changingPassword">
                更新密码
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 通知设置 -->
        <el-card class="settings-card" v-loading="notificationLoading">
          <template #header>
            <div class="card-header">
              <el-icon class="card-icon"><Bell /></el-icon>
              <span>通知设置</span>
              <el-tag size="small" type="success" effect="plain" class="local-pref-tag">
                服务端偏好
              </el-tag>
            </div>
          </template>
          <p class="setting-note">
            站内通知通过 SSE 实时推送到顶栏铃铛；邮件通知需要服务端配置 SMTP，
            开启后会按下方分组发送到你的账号邮箱。
          </p>

          <el-alert
            v-if="!notificationLoading && !notificationPrefs.mail_configured"
            type="info"
            :closable="false"
            show-icon
            class="notification-alert"
            title="当前部署未配置 SMTP"
            description="邮件开关会保存，但在管理员配置 MAIL_ENABLED / MAIL_HOST 之前不会实际发送。"
          />
          <el-alert
            v-if="!profileForm.email"
            type="warning"
            :closable="false"
            show-icon
            class="notification-alert"
            title="请先在个人信息中填写邮箱"
            description="没有邮箱时无法开启邮件通知。"
          />

          <div class="setting-list">
            <div class="setting-item">
              <div class="setting-info">
                <span class="setting-label">站内实时通知</span>
                <span class="setting-desc">审核、授权、任务结果会实时显示在顶栏铃铛</span>
              </div>
              <el-tag size="small" :type="notificationPrefs.sse_enabled ? 'success' : 'info'">
                {{ notificationPrefs.sse_enabled ? '已启用' : '未启用' }}
              </el-tag>
            </div>
            <div class="setting-item">
              <div class="setting-info">
                <span class="setting-label">邮件通知</span>
                <span class="setting-desc">
                  发送到 {{ notificationPrefs.email || '未设置邮箱' }}
                </span>
              </div>
              <el-switch
                v-model="notificationPrefs.email_enabled"
                :disabled="!profileForm.email"
              />
            </div>
            <div class="setting-item setting-item-block">
              <div class="setting-info">
                <span class="setting-label">邮件通知范围</span>
                <span class="setting-desc">只对勾选的事件分组发送邮件</span>
              </div>
              <el-checkbox-group
                v-model="notificationPrefs.email_groups"
                :disabled="!notificationPrefs.email_enabled"
                class="group-checkboxes"
              >
                <el-checkbox
                  v-for="group in availableGroups"
                  :key="group.key"
                  :label="group.key"
                >
                  {{ group.label }}
                </el-checkbox>
              </el-checkbox-group>
            </div>
          </div>

          <div class="setting-actions">
            <el-button
              :loading="testingEmail"
              :disabled="!notificationPrefs.mail_configured || !profileForm.email"
              @click="sendTestEmail"
            >
              发送测试邮件
            </el-button>
            <el-button type="primary" :loading="notificationSaving" @click="saveNotifications">
              保存通知设置
            </el-button>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { notificationApi, userApi } from '@/api/modules'
import { ElMessage } from 'element-plus'
import { User, Lock, Bell, ArrowLeft } from '@element-plus/icons-vue'

const userStore = useUserStore()
const router = useRouter()

const roleLabel = computed(() => {
  const labels = {
    admin: '超级管理员',
    asset_admin: '资产管理员',
    license_admin: '授权管理员',
    adm1: '一级审批员',
    adm2: '二级审批员',
    user: '普通用户'
  }
  return labels[userStore.userRole] || '用户'
})

const saving = ref(false)
const changingPassword = ref(false)

const profileForm = reactive({
  username: userStore.username || '',
  email: userStore.user?.email || '',
  phone: userStore.user?.phone || ''
})

const passwordFormRef = ref(null)
const passwordForm = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const validateConfirmPassword = (rule, value, callback) => {
  if (value !== passwordForm.newPassword) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const passwordRules = {
  currentPassword: [
    { required: true, message: '请输入当前密码', trigger: 'blur' }
  ],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

// 通知偏好保存在服务端；站内 SSE 默认启用，邮件按分组发送
const notificationLoading = ref(true)
const notificationSaving = ref(false)
const testingEmail = ref(false)
const availableGroups = ref([
  { key: 'asset', label: '资产审核结果' },
  { key: 'license', label: '授权审批、撤销与续期' },
  { key: 'task', label: '水印/存证任务结果' }
])
const notificationPrefs = reactive({
  email_enabled: false,
  email_groups: ['asset', 'license', 'task'],
  email: '',
  mail_configured: false,
  sse_enabled: true
})

async function loadNotificationPrefs() {
  notificationLoading.value = true
  try {
    const response = await notificationApi.getPreferences()
    if (response.data?.code === 200) {
      const data = response.data.data || {}
      notificationPrefs.email_enabled = Boolean(data.email_enabled)
      notificationPrefs.email_groups = data.email_groups || []
      notificationPrefs.email = data.email || ''
      notificationPrefs.mail_configured = Boolean(data.mail_configured)
      notificationPrefs.sse_enabled = data.sse_enabled !== false
      if (Array.isArray(data.available_groups) && data.available_groups.length) {
        availableGroups.value = data.available_groups
      }
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '通知设置加载失败')
  } finally {
    notificationLoading.value = false
  }
}

async function saveNotifications() {
  notificationSaving.value = true
  try {
    const response = await notificationApi.updatePreferences({
      email_enabled: notificationPrefs.email_enabled,
      email_groups: notificationPrefs.email_groups
    })
    if (response.data?.code === 200) {
      ElMessage.success('通知设置已保存')
      const data = response.data.data || {}
      notificationPrefs.email_enabled = Boolean(data.email_enabled)
      notificationPrefs.email_groups = data.email_groups || notificationPrefs.email_groups
    } else {
      ElMessage.error(response.data?.message || '保存失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '保存失败')
  } finally {
    notificationSaving.value = false
  }
}

async function sendTestEmail() {
  testingEmail.value = true
  try {
    const response = await notificationApi.testEmail()
    ElMessage.success(response.data?.message || '测试邮件已发送')
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '测试邮件发送失败')
  } finally {
    testingEmail.value = false
  }
}

async function saveProfile() {
  saving.value = true
  try {
    const data = {
      email: profileForm.email || '',
      phone: profileForm.phone || ''
    }
    const res = await userApi.updateProfile(data)
    if (res.data?.code === 200) {
      userStore.setUser({ ...userStore.user, ...data })
      notificationPrefs.email = data.email || ''
      ElMessage.success('个人信息已更新')
    } else {
      ElMessage.error(res.data?.message || '更新失败')
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '更新失败')
  } finally {
    saving.value = false
  }
}

function changePassword() {
  passwordFormRef.value?.validate(async (valid) => {
    if (!valid) return

    changingPassword.value = true
    try {
      const res = await userApi.changePassword({
        old_password: passwordForm.currentPassword,
        new_password: passwordForm.newPassword
      })
      if (res.data?.code === 200) {
        ElMessage.success('密码已更新，请重新登录')
        passwordForm.currentPassword = ''
        passwordForm.newPassword = ''
        passwordForm.confirmPassword = ''
        userStore.clearAuth()
        router.push('/login')
      } else {
        ElMessage.error(res.data?.message || '修改失败')
      }
    } catch (e) {
      ElMessage.error(e.response?.data?.message || '修改失败')
    } finally {
      changingPassword.value = false
    }
  })
}

onMounted(() => {
  loadNotificationPrefs()
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.settings-page {
  max-width: 800px;
  margin: 0 auto;
  min-height: 100vh;
  background: $bg-primary;
  padding: $spacing-2xl $spacing-3xl;
}

// ========== 页眉 ==========
.page-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: $spacing-md;
  padding-bottom: $spacing-md;
  margin-bottom: $spacing-xl;
  border-bottom: 1px solid $border-light;
}

.page-back {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: $font-size-sm;
  color: $text-secondary;
  transition: color $transition-fast;

  &:hover {
    color: $primary-dark;
  }
}

.page-title {
  font-family: $font-display;
  font-size: 23px;
  font-weight: $font-weight-semibold;
  line-height: $line-height-tight;
  letter-spacing: 0.02em;
  color: $text-primary;
}

.settings-container {
  margin: 0 auto;
}

.settings-grid {
  display: flex;
  flex-direction: column;
  gap: $spacing-xl;
}

.settings-card {
  :deep(.el-card__header) {
    padding: $spacing-lg $spacing-xl;
    border-bottom: 1px solid $border-light;
  }

  :deep(.el-card__body) {
    padding: $spacing-xl;
  }
}

.card-header {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  font-family: $font-display;
  font-size: $font-size-lg;
  font-weight: $font-weight-semibold;
  color: $text-primary;

  .card-icon {
    font-size: 20px;
    color: $primary-color;
  }

  .local-pref-tag {
    margin-left: auto;
  }
}

.setting-note {
  margin: 0 0 14px;
  font-size: 12px;
  line-height: 1.7;
  color: $text-placeholder;
}

.setting-list {
  display: flex;
  flex-direction: column;
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
  border-bottom: 1px solid $border-light;

  &:last-child {
    border-bottom: none;
  }

  &.setting-item-block {
    align-items: flex-start;
    flex-direction: column;
    gap: 12px;
  }
}

.notification-alert {
  margin-bottom: 12px;
}

.group-checkboxes {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
}

.setting-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 16px;
}

.setting-info {
  .setting-label {
    display: block;
    font-size: $font-size-base;
    color: $text-primary;
    font-weight: $font-weight-medium;
    margin-bottom: 4px;
  }

  .setting-desc {
    font-size: $font-size-xs;
    color: $text-placeholder;
  }
}

@media (max-width: $breakpoint-md) {
  .settings-page {
    padding: $spacing-lg;
  }

  .settings-card {
    :deep(.el-form-item) {
      flex-direction: column;
      align-items: flex-start;
    }

    :deep(.el-form-item__label) {
      width: auto !important;
      margin-bottom: 6px;
      text-align: left;
    }

    :deep(.el-form-item__content) {
      width: 100%;
    }
  }
}
</style>
