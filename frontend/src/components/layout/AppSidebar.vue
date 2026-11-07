<script setup lang="ts">
import { RouterLink, useRoute } from 'vue-router'
import { mainNavigation } from '../../navigation'
import AppIcon from '../ui/AppIcon.vue'

defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: [] }>()
const route = useRoute()

const isActive = (path: string) => route.path === path || route.path.startsWith(`${path}/`)
</script>

<template>
  <div v-if="open" class="fixed inset-x-0 top-14 bottom-0 z-30 bg-black/50 lg:hidden" @click="emit('close')" />
  <nav
    class="fixed top-14 bottom-0 left-0 z-40 w-56 shrink-0 overflow-y-auto bg-panel transition-transform lg:static lg:z-auto lg:translate-x-0"
    :class="open ? 'translate-x-0' : '-translate-x-full'"
  >
    <ul class="py-2">
      <li v-for="item in mainNavigation" :key="item.to">
        <RouterLink
          :to="item.to"
          class="flex items-center gap-3 border-l-4 px-5 py-3 text-sm transition-colors hover:bg-hover"
          :class="isActive(item.to) ? 'border-accent bg-raised text-accent' : 'border-transparent text-fg'"
          @click="emit('close')"
        >
          <AppIcon :name="item.icon" />
          {{ item.label }}
        </RouterLink>
        <ul v-if="item.children && isActive(item.to)" class="bg-raised pb-1">
          <li v-for="child in item.children" :key="child.to">
            <RouterLink
              :to="child.to"
              class="block py-2 pr-5 pl-14 text-sm transition-colors hover:text-fg"
              :class="isActive(child.to) ? 'text-accent' : 'text-muted'"
              @click="emit('close')"
            >
              {{ child.label }}
            </RouterLink>
          </li>
        </ul>
      </li>
    </ul>
  </nav>
</template>
