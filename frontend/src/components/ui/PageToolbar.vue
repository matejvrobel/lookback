<template>
  <div class="sticky top-0 z-20 flex min-h-12 flex-wrap items-center gap-1 border-b border-line bg-raised px-4 py-1.5">
    <slot />
    <div class="ml-auto flex flex-wrap items-center gap-1">
      <slot name="right" />
    </div>
  </div>
</template>
