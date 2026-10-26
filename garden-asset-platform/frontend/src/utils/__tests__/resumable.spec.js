import { describe, it, expect, vi, beforeAll } from 'vitest'
import { webcrypto } from 'node:crypto'
import { computeFileFingerprint, findResumableSession, sessionProgress } from '@/utils/resumable'

beforeAll(() => {
  if (!globalThis.crypto?.subtle) vi.stubGlobal('crypto', webcrypto)
})

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

  it('does not match a different file fingerprint', () => {
    const other = session({ fingerprint: 'a'.repeat(64) })
    const same = session({ upload_id: 'c'.repeat(32), fingerprint: 'b'.repeat(64) })
    expect(findResumableSession([other], file, 'b'.repeat(64))).toBeNull()
    expect(findResumableSession([other, same], file, 'b'.repeat(64))?.upload_id)
      .toBe(same.upload_id)
  })
})

describe('computeFileFingerprint', () => {
  it('falls back to incremental SHA-256 without SubtleCrypto', async () => {
    const original = globalThis.crypto
    try {
      vi.stubGlobal('crypto', undefined)
      const file = new File(['abc'], 'abc.txt')
      expect(await computeFileFingerprint(file)).toBe(
        'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
      )
    } finally {
      vi.stubGlobal('crypto', original)
    }
  })
  it('is stable for identical bytes and changes with content', async () => {
    const first = new File([new Uint8Array(200000).fill(7)], 'a.jpg')
    const same = new File([new Uint8Array(200000).fill(7)], 'renamed.jpg')
    const different = new File([new Uint8Array(200000).fill(8)], 'a.jpg')
    const hash = await computeFileFingerprint(first)
    expect(hash).toMatch(/^[0-9a-f]{64}$/)
    expect(await computeFileFingerprint(same)).toBe(hash)
    expect(await computeFileFingerprint(different)).not.toBe(hash)
    expect(await computeFileFingerprint(new File([], 'empty.jpg'))).toBe('')
  })
})
