/**
 * 通知提示工具
 */
import { ElMessage, ElNotification, ElMessageBox } from 'element-plus'

/**
 * 成功消息
 */
export function successMessage(message) {
  ElMessage.success({
    message,
    duration: 3000
  })
}

/**
 * 错误消息
 */
export function errorMessage(message) {
  ElMessage.error({
    message,
    duration: 5000
  })
}

/**
 * 警告消息
 */
export function warningMessage(message) {
  ElMessage.warning({
    message,
    duration: 4000
  })
}

/**
 * 信息消息
 */
export function infoMessage(message) {
  ElMessage.info({
    message,
    duration: 3000
  })
}

/**
 * 成功通知
 */
export function successNotify(title, message) {
  ElNotification({
    title,
    message,
    type: 'success',
    duration: 4500
  })
}

/**
 * 错误通知
 */
export function errorNotify(title, message) {
  ElNotification({
    title,
    message,
    type: 'error',
    duration: 0 // 不自动关闭
  })
}

/**
 * 确认对话框
 */
export function confirmDialog(message, title = '提示') {
  return ElMessageBox.confirm(message, title, {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  })
}

/**
 * 删除确认对话框
 */
export function confirmDelete(message = '确定要删除吗？此操作不可恢复') {
  return ElMessageBox.confirm(message, '删除确认', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'error',
    confirmButtonClass: 'el-button--danger'
  })
}

/**
 * 输入对话框
 */
export function promptDialog(message, title = '请输入') {
  return ElMessageBox.prompt(message, title, {
    confirmButtonText: '确定',
    cancelButtonText: '取消'
  })
}