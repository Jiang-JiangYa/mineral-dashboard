<script setup>
import { sources } from '../data/demo.js'
defineEmits(['navigate'])
</script>

<template>
  <section class="panel sources">
    <div class="panelhead"><h2>三源采集管线</h2><button @click="$emit('navigate', 'pipeline')">查看管线 ↗</button></div>
    <div class="sourcegrid"><article v-for="source in sources" :key="source.name"><div class="sourceicon">{{ source.icon }}</div><div><h3>{{ source.name }} <span :class="{ amber: source.status === '待授权' }">{{ source.status }}</span></h3><p>{{ source.providers }}</p><small>{{ source.description }}</small></div></article></div>
  </section>
</template>
