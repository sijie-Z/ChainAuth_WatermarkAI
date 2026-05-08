import api from './index'

// 公开API
export const publicApi = {
  getStats: () => api.get('/stats')
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
  create: (formData) => api.post('/assets/upload', formData),
  update: (id, data) => api.put(`/assets/${id}`, data),
  delete: (id) => api.delete(`/assets/${id}`),
  download: (id) => api.get(`/assets/${id}/download`, { responseType: 'blob' })
}

// 园林相关API
export const gardenApi = {
  getList: () => api.get('/gardens'),
  getDetail: (id) => api.get(`/gardens/${id}`)
}

// 水印相关API
export const watermarkApi = {
  embed: (assetId, options = {}) => api.post('/watermark/embed', { asset_id: assetId, ...options }),
  extract: (assetId) => api.post('/watermark/extract', { asset_id: assetId }),
  verify: (watermarkId) => api.post('/watermark/verify', { watermark_id: watermarkId }),
  trace: (formData) => api.post('/watermark/trace', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  getLogs: () => api.get('/watermark/logs')
}

// 区块链相关API
export const blockchainApi = {
  register: (assetId) => api.post('/blockchain/register', { asset_id: assetId }),
  verify: (assetId) => api.get(`/blockchain/verify/${assetId}`),
  verifyByWatermark: (watermarkId) => api.post('/blockchain/verify', { watermark_id: watermarkId }),
  getCertificate: (certificateId) => api.get(`/blockchain/certificate/${certificateId}`),
  getHistory: (assetId) => assetId ? api.get(`/blockchain/history/${assetId}`) : api.get('/blockchain/history'),
  getStatus: () => api.get('/blockchain/status')
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
  getMyLicenses: (params) => api.get('/license/my', { params })
}

// 用户管理API
export const userApi = {
  getUsers: () => api.get('/users'),
  updateUser: (userId, data) => api.put(`/users/${userId}`, data),
  getCurrentUser: () => api.get('/user/current'),
  updateProfile: (data) => api.put('/user/current', data),
  changePassword: (data) => api.post('/user/change-password', data)
}