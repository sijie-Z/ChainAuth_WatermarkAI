/**
 * 断点续传会话匹配
 *
 * 服务端保留未完成会话；浏览器无法在刷新后继续读取用户磁盘上的文件，
 * 因此用户重新选择同名同大小文件时，用文件元数据认领旧会话。
 */

export function sessionProgress(session) {
  const expected = Number(session?.expected_size) || 0
  const received = Number(session?.received_size) || 0
  if (expected <= 0) return 0
  return Math.min(100, Math.max(0, Math.round((received / expected) * 100)))
}

export function findResumableSession(sessions, file) {
  if (!Array.isArray(sessions) || !file) return null
  const size = Number(file.size)
  const candidates = sessions.filter(session =>
    session
    && session.status === 'uploading'
    && session.filename === file.name
    && Number(session.expected_size) === size
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
