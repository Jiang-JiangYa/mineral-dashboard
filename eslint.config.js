import js from '@eslint/js'
import vue from 'eslint-plugin-vue'
import globals from 'globals'

export default [
  {
    ignores: [
      'dist/**',
      'node_modules/**',
      '.cache/**',
      '.venv/**',
      'data/**',
      'data-*/**',
      '.sites-*/**',
    ],
  },
  js.configs.recommended,
  ...vue.configs['flat/essential'],
  {
    files: ['src/**/*.{js,vue}', 'tests/**/*.js'],
    languageOptions: { globals: globals.browser },
  },
  {
    files: ['*.{js,mjs}', 'scripts/**/*.mjs'],
    languageOptions: { globals: globals.node },
  },
]
