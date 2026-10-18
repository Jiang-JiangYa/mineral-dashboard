<script setup>
import { ref } from 'vue'
const props = defineProps({ endpoint: { type: String, default: '' } })
const emit = defineEmits(['save'])
const dialog = ref(null)
const input = ref(null)
const draft = ref('')
const error = ref('')
function open() { draft.value = props.endpoint; error.value = ''; dialog.value.showModal() }
function save() {
  const value = draft.value.trim()
  if (value) {
    try {
      const url = new URL(value)
      if (!['https:', 'http:'].includes(url.protocol)) throw new Error()
    } catch { error.value = '请输入有效的 HTTP 或 HTTPS 地址'; input.value?.focus(); return }
  }
  try { localStorage.setItem('mineral-query-endpoint', value) }
  catch { error.value = '浏览器无法保存设置，请检查存储权限。'; return }
  emit('save', value)
  dialog.value.close()
}
defineExpose({ open })
</script>

<template>
  <dialog ref="dialog" id="config" aria-labelledby="config-title">
    <h2 id="config-title">连接问答接口</h2><p>填写支持 POST /query 的服务地址。留空连接本项目后端 /api/query。</p>
    <form class="settings-form" @submit.prevent="save">
      <input ref="input" v-model="draft" placeholder="https://your-api.example/query" aria-label="接口地址" :aria-invalid="!!error" @input="error = ''" />
      <p v-if="error" role="alert" class="settings-error">{{ error }}</p>
      <p>请求：{"question":"…"}，响应：{"answer":"…"}。服务需允许网页跨域访问。</p>
      <div><button type="button" class="outline" @click="dialog.close()">取消</button><button type="submit" id="saveconfig">保存设置</button></div>
    </form>
  </dialog>
</template>
