"""
前端常量与类型定义
"""

// TypeScript 类型定义 (参考)
// 用户角色
export type UserRole = 'user' | 'asset_admin' | 'license_admin' | 'adm1' | 'adm2' | 'admin'

// 资产类型
export type AssetType = 'image' | 'model' | 'vector' | 'document' | 'video'

// 水印状态
export type WatermarkStatus = 'pending' | 'processing' | 'embedded' | 'failed'

// 存证状态
export type ChainStatus = 'pending' | 'processing' | 'confirmed' | 'failed'

// 授权状态
export type LicenseStatus = 'pending' | 'approved' | 'rejected' | 'active' | 'expired' | 'revoked'

// 授权类型
export type LicenseType = 'personal' | 'academic' | 'commercial' | 'display' | 'derivative'

// API响应结构
interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

// 分页数据
interface PaginatedData<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  pages: number
}

// 用户信息
interface User {
  id: number
  username: string
  email: string
  role: UserRole
  status: string
  created_at: string
}

// 资产信息
interface Asset {
  id: string
  asset_code: string
  title: string
  description?: string
  asset_type: AssetType
  file_format: string
  file_size: number
  watermark_status: WatermarkStatus
  watermark_id?: string
  chain_status: ChainStatus
  certificate_id?: string
  created_at: string
}

// 授权申请
interface LicenseApplication {
  id: number
  application_code: string
  asset_id: string
  asset_title?: string
  license_type: LicenseType
  purpose: string
  status: LicenseStatus
  created_at: string
}

// 存证证书
interface Certificate {
  certificate_id: string
  asset_id: string
  tx_hash: string
  block_number: number
  confirmed_at: string
  verified: boolean
}

// 溯源结果
interface TraceResult {
  verified: boolean
  asset_id?: string
  asset_code?: string
  title?: string
  watermark_id?: string
  certificate_id?: string
  tx_hash?: string
  nc_value?: number
}