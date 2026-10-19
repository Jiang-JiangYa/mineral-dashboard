// Run the project virtual environment on Windows, macOS and Linux without shell quoting.
import { existsSync } from 'node:fs'
import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const root = fileURLToPath(new URL('../', import.meta.url))
const executable = path.join(
  root,
  '.venv',
  process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python',
)
if (!existsSync(executable)) {
  console.error('未找到项目 .venv，请先按 README 初始化 Python 环境。')
  process.exit(1)
}
const child = spawn(executable, process.argv.slice(2), {
  cwd: root,
  stdio: 'inherit',
  env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
})
child.on('error', (error) => {
  console.error(`Python 启动失败：${error.message}`)
  process.exitCode = 1
})
child.on('exit', (code, signal) => {
  process.exitCode = code ?? (signal ? 1 : 0)
})
for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => {
    if (!child.killed) child.kill(signal)
  })
}
