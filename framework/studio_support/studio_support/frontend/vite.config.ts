import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { resolve } from 'node:path';

export default defineConfig({
  plugins: [svelte()],
  build: {
    outDir: resolve(__dirname, '../static'),
    emptyOutDir: false,
    rollupOptions: {
      input: {
        chat: resolve(__dirname, 'src/islands/chat.ts'),
        tools: resolve(__dirname, 'src/islands/tools.ts'),
        workflows: resolve(__dirname, 'src/islands/workflows.ts')
      },
      output: {
        entryFileNames: '[name].js',
        assetFileNames: '[name][extname]'
      }
    }
  }
});
