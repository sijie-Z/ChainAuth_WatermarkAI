import { describe, it, expect } from 'vitest'
import { findResumableSession, sessionProgress } from '@/utils/resumable'

function session(overrides = {}) {
  return {
    upload_id: 'a'.repeat(32),
    filename: 'garden.jpg',
    expected_size: 100,
    received_size: 40,
    status: 'uploading',
    updated_at: '2026-10-25T10:00:00',
    ...overrides
  }
}

describe('sessionProgress', () => {
  it('computes rounded percentage', () => {
    expect(sessionProgress(session())).toBe(40)
    expect(sessionProgress(session({ received_size: 0 }))).toBe(0)
    expect(sessionProgress(session({ received_size: 100 }))).toBe(100)
  })

  it('tolerates missing or zero sizes', () => {
    expect(sessionProgress(null)).toBe(0)
    expect(sessionProgress(session({ expected_size: 0 }))).toBe(0)
    expect(sessionProgress(session({ received_size: 150 }))).toBe(100)
  })
})

describe('findResumableSession', () => {
  const file = { name: 'garden.jpg', size: 100, lastModified: 1 }

  it('matches by file name and size', () => {
    const match = session()
    expect(findResumableSession([match], file)?.upload_id).toBe(match.upload_id)
  })

  it('ignores sessions for other files, sizes or statuses', () => {
    expect(findResumableSession([session({ filename: 'other.jpg' })], file)).toBeNull()
    expect(findResumableSession([session({ expected_size: 200 })], file)).toBeNull()
    expect(findResumableSession([session({ status: 'completed' })], file)).toBeNull()
  })

  it('prefers the most recently updated candidate', () => {
    const older = session({ upload_id: 'b'.repeat(32), updated_at: '2026-10-24T10:00:00' })
    const newer = session({ upload_id: 'c'.repeat(32), updated_at: '2026-10-25T10:00:00' })
    expect(findResumableSession([older, newer], file)?.upload_id).toBe(newer.upload_id)
  })

  it('returns null for empty input', () => {
    expect(findResumableSession(null, file)).toBeNull()
    expect(findResumableSession([], null)).toBeNull()
  })
})
