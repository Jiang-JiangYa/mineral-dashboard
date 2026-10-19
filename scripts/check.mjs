// Keep checks sequential and stop immediately on a failed step.
import { spawnSync } from 'node:child_process'

const npmCli = process.env.npm_execpath
if (!npmCli) {
  console.error('请通过 npm run check 执行工程检查。')
  process.exit(1)
}
for (const target of [
  'lint',
  'format:check',
  'lint:backend',
  'format:backend:check',
  'test',
  'test:backend',
  'build',
]) {
  const result = spawnSync(process.execPath, [npmCli, 'run', target], { stdio: 'inherit' })
  if (result.error) console.error(result.error.message)
  if (result.status !== 0) process.exit(result.status ?? 1)
}
