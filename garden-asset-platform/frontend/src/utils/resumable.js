/**
 * 断点续传：完整文件指纹与未完成会话匹配。
 *
 * 浏览器逐块读取文件并计算 SHA-256，不把大文件整体读入 JS 内存。
 * 服务端在合并前用同一算法复核，防止同名同大小文件误认领。
 */
const SAMPLE_SIZE = 64 * 1024
const NATIVE_HASH_LIMIT = 16 * 1024 * 1024

const K = new Uint32Array([
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
  0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
  0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
  0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
  0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
  0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
  0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
  0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
  0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
])

function rotr(value, bits) {
  return (value >>> bits) | (value << (32 - bits))
}

class IncrementalSha256 {
  constructor() {
    this.state = new Uint32Array([
      0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
      0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
    ])
    this.buffer = new Uint8Array(64)
    this.bufferLength = 0
    this.length = 0
  }

  update(chunk) {
    const data = chunk instanceof Uint8Array ? chunk : new Uint8Array(chunk)
    this.length += data.length
    let offset = 0
    if (this.bufferLength) {
      const needed = 64 - this.bufferLength
      const take = Math.min(needed, data.length)
      this.buffer.set(data.subarray(0, take), this.bufferLength)
      this.bufferLength += take
      offset = take
      if (this.bufferLength === 64) {
        this.transform(this.buffer)
        this.bufferLength = 0
      }
    }
    while (offset + 64 <= data.length) {
      this.transform(data.subarray(offset, offset + 64))
      offset += 64
    }
    if (offset < data.length) {
      const rest = data.subarray(offset)
      this.buffer.set(rest, 0)
      this.bufferLength = rest.length
    }
  }

  transform(block) {
    const words = new Uint32Array(64)
    for (let i = 0; i < 16; i += 1) {
      const index = i * 4
      words[i] = (
        (block[index] << 24)
        | (block[index + 1] << 16)
        | (block[index + 2] << 8)
        | block[index + 3]
      ) >>> 0
    }
    for (let i = 16; i < 64; i += 1) {
      const x = words[i - 15]
      const y = words[i - 2]
      const s0 = rotr(x, 7) ^ rotr(x, 18) ^ (x >>> 3)
      const s1 = rotr(y, 17) ^ rotr(y, 19) ^ (y >>> 10)
      words[i] = (words[i - 16] + s0 + words[i - 7] + s1) >>> 0
    }
    let [a, b, c, d, e, f, g, h] = this.state
    for (let i = 0; i < 64; i += 1) {
      const s1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)
      const choice = (e & f) ^ (~e & g)
      const temp1 = (h + s1 + choice + K[i] + words[i]) >>> 0
      const s0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)
      const majority = (a & b) ^ (a & c) ^ (b & c)
      const temp2 = (s0 + majority) >>> 0
      h = g
      g = f
      f = e
      e = (d + temp1) >>> 0
      d = c
      c = b
      b = a
      a = (temp1 + temp2) >>> 0
    }
    const values = [a, b, c, d, e, f, g, h]
    for (let i = 0; i < 8; i += 1) {
      this.state[i] = (this.state[i] + values[i]) >>> 0
    }
  }

  digest() {
    const bitLength = this.length * 8
    const paddingLength = (
      this.bufferLength < 56
        ? 56 - this.bufferLength
        : 64 + 56 - this.bufferLength
    ) + 8
    const padding = new Uint8Array(paddingLength)
    padding[0] = 0x80
    for (let i = 0; i < 8; i += 1) {
      padding[paddingLength - 1 - i] = Math.floor(bitLength / (2 ** (8 * i))) & 0xff
    }
    this.update(padding)
    return Array.from(this.state)
      .map(value => value.toString(16).padStart(8, '0'))
      .join('')
  }
}

function hex(buffer) {
  return Array.from(new Uint8Array(buffer))
    .map(byte => byte.toString(16).padStart(2, '0'))
    .join('')
}

async function sha256Hex(data) {
  const bytes = new Uint8Array(
    data instanceof ArrayBuffer
      ? data
      : data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength)
  )
  if (!globalThis.crypto?.subtle) {
    const hash = new IncrementalSha256()
    hash.update(bytes)
    return hash.digest()
  }
  return hex(await globalThis.crypto.subtle.digest('SHA-256', bytes))
}

export async function computeFilePrefixHash(file) {
  const size = Number(file?.size) || 0
  if (!file || size <= 0) return ''
  return sha256Hex(await file.slice(0, Math.min(size, SAMPLE_SIZE)).arrayBuffer())
}

export async function computeFileFingerprint(file) {
  const size = Number(file?.size) || 0
  if (!file || size <= 0) return ''
  if (size <= NATIVE_HASH_LIMIT) {
    return sha256Hex(await file.arrayBuffer())
  }
  const hash = new IncrementalSha256()
  const chunkSize = 1024 * 1024
  for (let offset = 0; offset < size; offset += chunkSize) {
    const buffer = await file.slice(
      offset, Math.min(size, offset + chunkSize)
    ).arrayBuffer()
    hash.update(new Uint8Array(buffer))
  }
  return hash.digest()
}

export function sessionProgress(session) {
  const expected = Number(session?.expected_size) || 0
  const received = Number(session?.received_size) || 0
  if (expected <= 0) return 0
  return Math.min(100, Math.max(0, Math.round((received / expected) * 100)))
}

export function findResumableSession(sessions, file, fingerprint = '') {
  if (!Array.isArray(sessions) || !file) return null
  const size = Number(file.size)
  const candidates = sessions.filter(session =>
    session
    && session.status === 'uploading'
    && session.filename === file.name
    && Number(session.expected_size) === size
    && (!session.fingerprint || session.fingerprint === fingerprint)
  )
  if (!candidates.length) return null
  // 同名同大小的历史会话可能不止一个，优先取最近更新的
  return candidates
    .slice()
    .sort((left, right) => {
      const leftTime = Date.parse(left.updated_at || '') || 0
      const rightTime = Date.parse(right.updated_at || '') || 0
      return rightTime - leftTime
    })[0]
}
