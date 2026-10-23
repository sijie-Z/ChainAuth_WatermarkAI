/**
 * 内存安全的前端测试入口
 *
 * Vitest 默认会为每个测试文件启动 fork worker；Windows 开发机内存紧张时
 * 多个 worker 同时启动会被系统拒绝，表现为 "Failed to start forks worker"。
 * 这里改为逐个测试文件启动独立 Vitest 进程，跑完即退出。
 *
 * 用法：node scripts/run-tests.mjs
 */
import { spawnSync } from 'node:child_process'
import { readdirSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = fileURLToPath(new URL('..', import.meta.url))
const vitestEntry = join(root, 'node_modules', 'vitest', 'vitest.mjs')

function findTests(dir, result = []) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name)
    const stat = statSync(path)
    if (stat.isDirectory()) {
      findTests(path, result)
    } else if (name.endsWith('.spec.js')) {
      result.push(path)
    }
  }
  return result
}

const files = findTests(join(root, 'src')).sort()
if (files.length === 0) {
  console.error('未找到前端测试文件')
  process.exit(2)
}

console.log(`内存安全测试模式：${files.length} 个文件，逐文件串行执行`)
let failed = []
const started = Date.now()

for (const [index, file] of files.entries()) {
  const name = relative(root, file)
  console.log(`[${index + 1}/${files.length}] ${name}`)
  const result = spawnSync(
    process.execPath,
    [vitestEntry, 'run', name, '--passWithNoTests', '--maxWorkers=1'],
    { cwd: root, stdio: 'inherit', env: { ...process.env, CI: 'true' } }
  )
  if (result.status !== 0) {
    failed.push(name)
    console.error(`  FAIL ${name}（退出码 ${result.status}）`)
  } else {
    console.log(`  PASS ${name}`)
  }
}

const seconds = ((Date.now() - started) / 1000).toFixed(1)
console.log('\n' + '='.repeat(60))
if (failed.length) {
  console.error(`未通过 ${failed.length} 个文件（耗时 ${seconds}s）：`)
  failed.forEach(name => console.error(`  - ${name}`))
  process.exit(1)
}
console.log(`全部通过：${files.length} 个文件，耗时 ${seconds}s`)
