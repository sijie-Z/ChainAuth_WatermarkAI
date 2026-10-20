import { describe, it, expect } from 'vitest'
import router from '@/router'

const ADMIN_ROLES = ['admin', 'asset_admin', 'license_admin', 'adm1', 'adm2']

function routeByName(name) {
  return router.getRoutes().find(route => route.name === name)
}

describe('router role configuration', () => {
  it('uses the unified admin role set for the admin layout', () => {
    expect(routeByName('AdminLayout').meta.roles).toEqual(ADMIN_ROLES)
  })

  it('does not reference retired roles', () => {
    const roles = router.getRoutes().flatMap(route => route.meta.roles || [])

    expect(roles).not.toContain('adm3')
    expect(roles).not.toContain('super_admin')
  })

  it('provides the asset upload, 403 and 404 routes', () => {
    expect(routeByName('AssetUpload').path).toBe('/assets/upload')
    expect(routeByName('Forbidden').path).toBe('/403')
    expect(routeByName('NotFound').path).toBe('/:pathMatch(.*)*')
  })

  it('keeps the admin management pages under the admin layout', () => {
    const adminAssets = routeByName('AdminAssets')

    expect(adminAssets.path).toBe('/admin/assets')
    expect(adminAssets.meta.title).toBe('资产管理')
  })
})
