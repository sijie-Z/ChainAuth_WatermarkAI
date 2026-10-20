/**
 * 前端常量定义
 */

// 资产类型
export const ASSET_TYPES = [
  { value: 'image', label: '影像', color: '#2f6b5a' },
  { value: 'model', label: '三维模型', color: '#3f7d5b' },
  { value: 'vector', label: '矢量数据', color: '#b07a2a' },
  { value: 'document', label: '文献', color: '#5b675f' },
  { value: 'video', label: '视频', color: '#a6402f' }
]

// 授权类型
export const LICENSE_TYPES = [
  { value: 'personal', label: '个人使用', color: '#2f6b5a' },
  { value: 'academic', label: '学术研究', color: '#3f7d5b' },
  { value: 'commercial', label: '商业使用', color: '#b07a2a' },
  { value: 'display', label: '展览展示', color: '#5b675f' },
  { value: 'derivative', label: '衍生创作', color: '#a6402f' }
]

// 使用期限
export const VALID_PERIODS = [
  { value: '1m', label: '1个月' },
  { value: '3m', label: '3个月' },
  { value: '6m', label: '6个月' },
  { value: '1y', label: '1年' },
  { value: 'permanent', label: '永久' }
]

// 角色类型
export const ROLES = [
  { value: 'user', label: '普通用户' },
  { value: 'asset_admin', label: '资产管理员' },
  { value: 'license_admin', label: '授权管理员' },
  { value: 'adm1', label: '一级审批员' },
  { value: 'adm2', label: '二级审批员' },
  { value: 'admin', label: '超级管理员' }
]

// 状态映射
export const STATUS_MAP = {
  pending: { label: '待处理', type: 'warning' },
  processing: { label: '处理中', type: 'info' },
  embedded: { label: '已嵌入', type: 'success' },
  confirmed: { label: '已确认', type: 'success' },
  active: { label: '生效中', type: 'success' },
  approved: { label: '已通过', type: 'success' },
  rejected: { label: '已拒绝', type: 'danger' },
  expired: { label: '已过期', type: 'info' },
  failed: { label: '失败', type: 'danger' }
}

// 水印算法
export const WATERMARK_ALGORITHMS = [
  { value: 'dct', label: 'DCT域水印' },
  { value: 'lsb', label: 'LSB水印' },
  { value: 'vector', label: '矢量水印' }
]

// API基础路径
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

// 应用信息
export const APP_INFO = {
  title: '苏州园林数字资产平台',
  description: '基于数字水印和AI推理的苏州园林数字资产安全分发与溯源系统',
  copyright: '© 2026 苏州园林数字资产平台团队'
}