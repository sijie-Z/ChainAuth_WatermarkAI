<template>
  <div class="settings-page">
    <div class="settings-container">
      <h1 class="page-title">账号设置</h1>

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
        <el-card class="settings-card">
          <template #header>
            <div class="card-header">
              <el-icon class="card-icon"><Bell /></el-icon>
              <span>通知设置</span>
            </div>
          </template>
          <div class="setting-list">
            <div class="setting-item">
              <div class="setting-info">
                <span class="setting-label">授权审批通知</span>
                <span class="setting-desc">当授权申请状态变更时通知</span>
              </div>
              <el-switch v-model="notifications.license" />
            </div>
            <div class="setting-item">
              <div class="setting-info">
                <span class="setting-label">资产更新通知</span>
                <span class="setting-desc">当资产信息发生变更时通知</span>
              </div>
              <el-switch v-model="notifications.asset" />
            </div>
            <div class="setting-item">
              <div class="setting-info">
                <span class="setting-label">系统公告</span>
                <span class="setting-desc">接收平台系统公告和维护通知</span>
              </div>
              <el-switch v-model="notifications.system" />
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, reactive } from 'vue'
import { useUserStore } from '@/stores/user'
import { userApi } from '@/api/modules'
import { ElMessage } from 'element-plus'
import { User, Lock, Bell } from '@element-plus/icons-vue'

const userStore = useUserStore()

const roleLabel = computed(() => {
  const labels = {
    admin: '超级管理员',
    adm1: '资产管理员',
    adm2: '授权管理员',
    adm3: '审核员',
    user: '普通用户'
  }
  return labels[userStore.userRole] || '用户'
})

const saving = ref(false)
const changingPassword = ref(false)

const profileForm = reactive({
  username: userStore.username || '',
  email: '',
  phone: ''
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

const notifications = reactive({
  license: true,
  asset: true,
  system: false
})

async function saveProfile() {
  saving.value = true
  try {
    const data = {}
    if (profileForm.email) data.email = profileForm.email
    if (profileForm.phone) data.phone = profileForm.phone
    const res = await userApi.updateProfile(data)
    if (res.data?.code === 200) {
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
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.settings-page {
  min-height: 100vh;
  background: $bg-primary;
  padding: 32px;
}

.settings-container {
  max-width: 800px;
  margin: 0 auto;
}

.page-title {
  font-size: $font-size-3xl;
  font-weight: $font-weight-bold;
  color: $text-primary;
  margin: 0 0 24px;
}

.settings-grid {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.settings-card {
  border-radius: $radius-xl;
  box-shadow: $shadow-card;

  :deep(.el-card__header) {
    padding: 20px 24px;
    border-bottom: 1px solid $border-light;
  }

  :deep(.el-card__body) {
    padding: 24px;
  }
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: $font-size-lg;
  font-weight: $font-weight-semibold;

  .card-icon {
    font-size: 20px;
    color: $primary-color;
  }
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

@media (max-width: $breakpoint-sm) {
  .settings-page {
    padding: 16px;
  }

  .page-title {
    font-size: $font-size-2xl;
  }
}
</style>
