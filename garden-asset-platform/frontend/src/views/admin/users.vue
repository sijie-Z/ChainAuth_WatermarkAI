<template>
  <div class="admin-users">
    <header class="page-head">
      <div class="page-heading">
        <h1 class="page-title">用户管理</h1>
        <p class="page-subtitle">管理后台账号、角色与访问状态</p>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon>
          添加用户
        </el-button>
      </div>
    </header>

    <div class="content-card">
      <el-table :data="users" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="80" class-name="cell-code" />
        <el-table-column prop="username" label="用户名" width="150" />
        <el-table-column prop="email" label="邮箱" min-width="200" />
        <el-table-column prop="role" label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="getRoleType(row.role)" size="small">
              {{ getRoleName(row.role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'danger'" size="small">
              {{ row.status === 'active' ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="140">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="toggleStatus(row)">
              {{ row.status === 'active' ? '禁用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 创建/编辑对话框 -->
    <el-dialog v-model="dialog.visible" :title="dialog.title" width="min(420px, 92vw)">
      <el-form ref="formRef" :model="dialog.form" :rules="dialog.rules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="dialog.form.username" :disabled="dialog.isEdit" />
        </el-form-item>
        <el-form-item v-if="!dialog.isEdit" label="密码" prop="password">
          <el-input v-model="dialog.form.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="dialog.form.email" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="dialog.form.role">
            <el-option label="普通用户" value="user" />
            <el-option label="资产管理员" value="asset_admin" />
            <el-option label="授权管理员" value="license_admin" />
            <el-option label="一级审批员" value="adm1" />
            <el-option label="二级审批员" value="adm2" />
            <el-option label="超级管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="dialog.form.status">
            <el-radio label="active">正常</el-radio>
            <el-radio label="inactive">禁用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="dialog.loading" @click="doSubmit">
          {{ dialog.isEdit ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { userApi } from '@/api/modules'

const loading = ref(false)
const users = ref([])
const formRef = ref()

const dialog = ref({
  visible: false,
  title: '',
  isEdit: false,
  userId: null,
  loading: false,
  form: {
    username: '',
    password: '',
    email: '',
    role: 'user',
    status: 'active'
  },
  rules: {
    username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
    password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
    email: [{ required: true, type: 'email', message: '请输入正确邮箱', trigger: 'blur' }],
    role: [{ required: true, message: '请选择角色', trigger: 'change' }]
  }
})

async function loadUsers() {
  loading.value = true
  try {
    const response = await userApi.getUsers()
    if (response.data.code === 200) {
      users.value = response.data.data
    }
  } catch (error) {
    ElMessage.error('加载用户失败')
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  dialog.value = {
    visible: true,
    title: '添加用户',
    isEdit: false,
    userId: null,
    loading: false,
    form: {
      username: '',
      password: '',
      email: '',
      role: 'user',
      status: 'active'
    },
    rules: dialog.value.rules
  }
}

function openEditDialog(row) {
  dialog.value = {
    visible: true,
    title: '编辑用户',
    isEdit: true,
    userId: row.id,
    loading: false,
    form: {
      username: row.username,
      password: '',
      email: row.email,
      role: row.role,
      status: row.status
    },
    rules: dialog.value.rules
  }
}

async function doSubmit() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  dialog.value.loading = true
  try {
    const form = dialog.value.form
    if (dialog.value.isEdit) {
      // 编辑时不提交空密码
      const payload = {
        email: form.email,
        role: form.role,
        status: form.status
      }
      if (form.password) {
        payload.password = form.password
      }
      const response = await userApi.updateUser(dialog.value.userId, payload)
      if (response.data?.code !== 200) {
        ElMessage.error(response.data?.message || '用户更新失败')
        return
      }
      ElMessage.success('用户更新成功')
    } else {
      // 管理员创建用户：POST /api/users，角色/状态随请求提交
      const response = await userApi.create({
        username: form.username,
        password: form.password,
        email: form.email,
        role: form.role,
        status: form.status
      })
      if (response.data?.code !== 200) {
        ElMessage.error(response.data?.message || '用户创建失败')
        return
      }
      ElMessage.success('用户创建成功')
    }
    dialog.value.visible = false
    loadUsers()
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '操作失败')
  } finally {
    dialog.value.loading = false
  }
}

async function toggleStatus(row) {
  const action = row.status === 'active' ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(`确定${action}该用户？`, '提示', { type: 'warning' })
    const newStatus = row.status === 'active' ? 'inactive' : 'active'
    const response = await userApi.updateUser(row.id, { status: newStatus })
    if (response.data.code === 200) {
      ElMessage.success(`${action}成功`)
      loadUsers()
    }
  } catch {
    // cancelled
  }
}

function getRoleName(role) {
  const map = {
    user: '普通用户',
    asset_admin: '资产管理员',
    license_admin: '授权管理员',
    adm1: '一级审批员',
    adm2: '二级审批员',
    admin: '超级管理员'
  }
  return map[role] || role || '-'
}

function getRoleType(role) {
  const map = {
    user: 'info',
    asset_admin: 'warning',
    license_admin: 'success',
    adm1: 'warning',
    adm2: 'warning',
    admin: 'danger'
  }
  return map[role] || ''
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

onMounted(() => {
  loadUsers()
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.admin-users {
  min-height: 100%;
  padding: 24px 28px 32px;
}

// ========== 页面头部 ==========
.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: $spacing-lg;
  margin-bottom: $spacing-xl;

  .page-title {
    font-family: $font-display;
    font-size: 22px;
    font-weight: $font-weight-semibold;
    line-height: $line-height-tight;
    color: $text-primary;
    letter-spacing: 0.01em;
  }

  .page-subtitle {
    margin-top: 6px;
    font-size: 13px;
    color: $text-secondary;
  }
}

.page-actions {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  flex-shrink: 0;
}

// ========== 内容卡片 ==========
.content-card {
  background: $bg-card;
  border: 1px solid $border-color;
  border-radius: $radius-lg;
  box-shadow: $shadow-sm;
  padding: $spacing-xl;
}

// 按钮内图标与文字间距
:deep(.el-button > span) {
  gap: 6px;
  align-items: center;
}

// 台账编码使用等宽字体
:deep(.cell-code) {
  font-family: $font-mono;
  font-size: 12px;
  color: $text-secondary;
  font-variant-numeric: tabular-nums;
}

// ========== 响应式 ==========
@media (max-width: 768px) {
  .admin-users {
    padding: 16px;
  }

  .page-head {
    flex-direction: column;
    align-items: flex-start;
    gap: $spacing-md;
  }

  .content-card {
    padding: 16px;
  }
}
</style>
