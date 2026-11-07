import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  build: {
    chunkSizeWarningLimit: 700,
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8765',
    },
  },
})
