import api from './index'

// 公开API
export const publicApi = {
  // 首页/目录页会自行降级展示，静默失败避免刷屏
  getStats: () => api.get('/stats', { silent: true }),
  getTags: () => api.get('/tags', { silent: true }),
  verifyEvidencePackage: (formData) => api.post('/evidence/verify-package', formData, {
    timeout: 60000
  })
}

// 认证相关API
export const authApi = {
  login: (data) => api.post('/login', data),
  register: (data) => api.post('/register', data),
  logout: () => api.post('/logout'),
  refresh: () => api.post('/refresh'),
  getUsers: () => api.get('/users'),
  updateUser: (userId, data) => api.put(`/users/${userId}`, data)
}

// 资产相关API
export const assetApi = {
  getList: (params) => api.get('/assets', { params }),
  getDetail: (id) => api.get(`/assets/${id}`),
  getLicenses: (id) => api.get(`/assets/${id}/licenses`),
  restore: (id) => api.post(`/assets/${id}/restore`),
  getRelated: (id) => api.get(`/assets/${id}/related`),
  getTags: (id) => api.get(`/assets/${id}/tags`),
  create: (formData, config) => config
    ? api.post('/assets/upload', formData, config)
    : api.post('/assets/upload', formData),
  update: (id, data) => api.put(`/assets/${id}`, data),
  delete: (id) => api.delete(`/assets/${id}`),
  download: (id, params) => api.get(`/assets/${id}/download`, {
    params,
    responseType: 'blob',
    timeout: 0
  }),
  createDownloadTicket: (id, data) => api.post(`/assets/${id}/download-ticket`, data),
  preview: (id) => api.get(`/assets/${id}/preview`, {
    responseType: 'blob',
    timeout: 0
  }),
  createPreviewTicket: (id) => api.post(`/assets/${id}/preview-ticket`),
  my: (params) => api.get('/assets/my', { params }),
  publish: (id) => api.post(`/assets/${id}/publish`),
  approve: (id, data) => api.post(`/assets/${id}/approve`, data),
  getFavorite: (id) => api.get(`/assets/${id}/favorite`),
  addFavorite: (id) => api.post(`/assets/${id}/favorite`),
  removeFavorite: (id) => api.delete(`/assets/${id}/favorite`),
  getFavorites: (params) => api.get('/favorites', { params }),
  getEvidence: (id) => api.get(`/assets/${id}/evidence`),
  exportEvidencePackage: (id, params) => api.get(
    `/assets/${id}/evidence-package`,
    { params, responseType: 'blob', timeout: 120000 }
  ),
  getComments: (id, params) => api.get(`/assets/${id}/comments`, { params }),
  createComment: (id, data) => api.post(`/assets/${id}/comments`, data),
  updateComment: (id, commentId, data) => api.put(`/assets/${id}/comments/${commentId}`, data),
  deleteComment: (id, commentId) => api.delete(`/assets/${id}/comments/${commentId}`),
  getAnnotations: (id, params) => api.get(`/assets/${id}/annotations`, { params }),
  createAnnotation: (id, data) => api.post(`/assets/${id}/annotations`, data),
  updateAnnotation: (id, annotationId, data) => api.put(
    `/assets/${id}/annotations/${annotationId}`,
    data
  ),
  deleteAnnotation: (id, annotationId) => api.delete(
    `/assets/${id}/annotations/${annotationId}`
  ),
  getVersions: (id) => api.get(`/assets/${id}/versions`),
  uploadVersion: (id, formData, config) => api.post(
    `/assets/${id}/versions`,
    formData,
    { timeout: 0, ...config }
  ),
  downloadVersion: (id, versionId) => api.get(
    `/assets/${id}/versions/${versionId}/download`,
    { responseType: 'blob', timeout: 0 }
  ),
  restoreVersion: (id, versionId) => api.post(`/assets/${id}/versions/${versionId}/restore`),
  getShares: (id) => api.get(`/assets/${id}/shares`),
  createShare: (id, data) => api.post(`/assets/${id}/shares`, data),
  revokeShare: (shareId) => api.delete(`/shares/${shareId}`)
}

// 公开分享（免登录）
export const shareApi = {
  get: (token, params) => api.get(`/shares/${token}`, { params, silent: true, skipAuth: true }),
  download: (token, params) => api.get(`/shares/${token}/download`, {
    params,
    responseType: 'blob',
    timeout: 0,
    silent: true,
    skipAuth: true
  })
}

// 下载记录
export const downloadApi = {
  mine: (params) => api.get('/downloads/my', { params }),
  ledger: (params) => api.get('/downloads', { params }),
  assetSummary: (assetId) => api.get(`/assets/${assetId}/downloads`)
}

// 用户合集
export const collectionApi = {
  getList: (params) => api.get('/collections', { params }),
  getDetail: (id) => api.get(`/collections/${id}`),
  create: (data) => api.post('/collections', data),
  update: (id, data) => api.put(`/collections/${id}`, data),
  remove: (id) => api.delete(`/collections/${id}`),
  addAssets: (id, assetIds) => api.post(`/collections/${id}/assets`, { asset_ids: assetIds }),
  removeAsset: (id, assetId) => api.delete(`/collections/${id}/assets/${assetId}`)
}

// 园林相关API
export const gardenApi = {
  getList: (params) => api.get('/gardens', { params, silent: true }),
  getDetail: (id) => api.get(`/gardens/${id}`),
  create: (data) => api.post('/gardens', data),
  update: (id, data) => api.put(`/gardens/${id}`, data),
  remove: (id) => api.delete(`/gardens/${id}`)
}

// 水印相关API
export const watermarkApi = {
  embed: (assetId, options = {}) => api.post('/watermark/embed', { asset_id: assetId, ...options }),
  extract: (assetId) => api.post('/watermark/extract', { asset_id: assetId }),
  verify: (watermarkId) => api.post('/watermark/verify', { watermark_id: watermarkId }),
  trace: (formData) => api.post('/watermark/trace', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  benchmark: (formData) => api.post('/watermark/benchmark', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000
  }),
  getLogs: () => api.get('/watermark/logs')
}

// 区块链相关API
export const blockchainApi = {
  register: (assetId, options = {}) => api.post(
    '/blockchain/register',
    { asset_id: assetId, ...options }
  ),
  verify: (assetId) => api.get(`/blockchain/verify/${assetId}`),
  verifyByWatermark: (watermarkId) => api.post('/blockchain/verify', { watermark_id: watermarkId }),
  getCertificate: (certificateId) => api.get(`/blockchain/certificate/${certificateId}`),
  getHistory: (assetId) => assetId ? api.get(`/blockchain/history/${assetId}`) : api.get('/blockchain/history'),
  getStatus: () => api.get('/blockchain/status')
}

// 异步任务（水印/存证）
export const taskApi = {
  get: (taskId) => api.get(`/tasks/${taskId}`, { silent: true }),
  list: (params) => api.get('/tasks', { params, silent: true }),
  health: () => api.get('/tasks/health', { silent: true }),
  retry: (taskId) => api.post(`/tasks/${taskId}/retry`),
  cancel: (taskId) => api.post(`/tasks/${taskId}/cancel`)
}

// AI相关API
export const aiApi = {
  analyze: (assetId) => api.post('/ai/analyze', { asset_id: assetId }),
  search: (formData) => api.post('/ai/search', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  infringement: (formData) => api.post('/ai/infringement', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  chat: (question, context) => api.post('/ai/chat', { question, context })
}

// 授权相关API
export const licenseApi = {
  apply: (data) => api.post('/license/apply', data),
  getPending: () => api.get('/license/pending'),
  getApproved: (params) => api.get('/license/approved', { params }),
  approve: (applicationId, data) => api.post(`/license/approve/${applicationId}`, data),
  cancelApplication: (applicationId) => api.post(`/license/applications/${applicationId}/cancel`),
  revoke: (licenseId, data) => api.post(`/license/${licenseId}/revoke`, data || {}),
  renew: (licenseId, data) => api.post(`/license/${licenseId}/renew`, data),
  getContract: (licenseId) => api.get(`/license/${licenseId}/contract`),
  getMyLicenses: (params) => api.get('/license/my', { params }),
  myApplications: (params) => api.get('/license/my-applications', { params }),
  usageReport: (params) => api.get('/license/usage-report', { params })
}

// 站内待办提醒
export const notificationApi = {
  get: () => api.get('/notifications', { silent: true }),
  markRead: (payload) => api.post('/notifications/read', payload, { silent: true }),
  getPreferences: () => api.get('/notifications/preferences'),
  updatePreferences: (data) => api.put('/notifications/preferences', data),
  testEmail: () => api.post('/notifications/test-email'),
  streamUrl: (sinceId) => {
    const base = import.meta.env.VITE_API_BASE_URL || '/api'
    const query = sinceId ? `?since_id=${encodeURIComponent(sinceId)}` : ''
    return `${base}/notifications/stream${query}`
  }
}

// 操作日志
export const logApi = {
  getList: (params) => api.get('/logs', { params }),
  integrity: () => api.get('/logs/integrity')
}

// 疑似侵权线索
export const infringementApi = {
  report: (formData) => api.post('/infringements/report', formData, { timeout: 0 }),
  patrol: (formData) => api.post('/infringements/patrol', formData, { timeout: 0 }),
  mine: (params) => api.get('/infringements/mine', { params }),
  list: (params) => api.get('/infringements', { params }),
  get: (id) => api.get(`/infringements/${id}`),
  review: (id, data) => api.post(`/infringements/${id}/review`, data),
  getFile: (id) => api.get(`/infringements/${id}/file`, {
    responseType: 'blob',
    timeout: 0
  })
}

// 系统能力状态
export const systemApi = {
  getStatus: () => api.get('/system/status'),
  getWebhook: () => api.get('/system/notification-webhook'),
  updateWebhook: (data) => api.put('/system/notification-webhook', data),
  testWebhook: () => api.post('/system/notification-webhook/test')
}

// 用户管理API
export const userApi = {
  getUsers: () => api.get('/users'),
  create: (data) => api.post('/users', data),
  updateUser: (userId, data) => api.put(`/users/${userId}`, data),
  getCurrentUser: () => api.get('/user/current'),
  updateProfile: (data) => api.put('/user/current', data),
  changePassword: (data) => api.post('/user/change-password', data)
}