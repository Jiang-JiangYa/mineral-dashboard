<script setup>
import { navigation } from '../data/navigation.js'
defineProps({ active: { type: String, required: true } })
defineEmits(['navigate', 'settings'])
</script>

<template>
  <aside>
    <a class="brand" href="#" @click.prevent="$emit('navigate', 'overview')">◈ <span>矿观<small>MINERAL INTELLIGENCE</small></span></a>
    <div class="workspace">全球矿业情报工作空间 <span>⌄</span></div>
    <small class="nav-label">工作台</small>
    <nav aria-label="工作台导航">
      <button v-for="item in navigation" :key="item.id" :class="{ active: active === item.id }" :aria-current="active === item.id ? 'page' : undefined" @click="$emit('navigate', item.id)">{{ item.icon }}　{{ item.label }}</button>
    </nav>
    <div class="sidebottom">
      <div class="health">●　本地工作台 <span>V0.3</span></div>
      <button @click="$emit('settings')">⚙　接口设置</button>
      <div class="profile"><b>YJ</b><span>我的工作空间<small>矿业研究员</small></span></div>
    </div>
  </aside>
</template>
