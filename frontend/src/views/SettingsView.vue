<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
import AppIcon from '../components/ui/AppIcon.vue'
import { settingsSections } from '../navigation'
</script>

<template>
  <div class="flex min-h-full flex-col">
    <div class="flex gap-1 overflow-x-auto border-b border-line bg-panel px-4 lg:hidden">
      <RouterLink
        v-for="section in settingsSections"
        :key="section.key"
        :to="`/settings/${section.key}`"
        class="flex shrink-0 items-center gap-2 border-b-2 border-transparent px-3 py-2.5 text-sm text-muted"
        active-class="!border-accent !text-fg"
      >
        <AppIcon :name="section.icon" :size="16" />
        {{ section.label }}
      </RouterLink>
    </div>
    <RouterView />
  </div>
</template>
