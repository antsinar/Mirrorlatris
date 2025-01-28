import { fileURLToPath, URL } from 'node:url'
import { dirname, resolve } from 'node:path'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

const config_dir = dirname(fileURLToPath(import.meta.url));

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  build: {
    manifest: "manifest.json",
    outDir: resolve("../../staticfiles/"),
    minify: true,
    emptyOutDir: false,
    rollupOptions: {
      input: {
        pairingApp: resolve(config_dir, "src/pairing/main.ts"),
      }
    },
  },
})
