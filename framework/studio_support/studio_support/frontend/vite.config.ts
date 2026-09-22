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
        workflows: resolve(__dirname, 'src/islands/workflows.ts'),
        memory: resolve(__dirname, 'src/islands/memory.ts'),
        rag: resolve(__dirname, 'src/islands/rag.ts'),
        evals: resolve(__dirname, 'src/islands/evals.ts'),
        storage: resolve(__dirname, 'src/islands/storage.ts'),
        observe: resolve(__dirname, 'src/islands/observe.ts'),
        deploy: resolve(__dirname, 'src/islands/deploy.ts'),
        auth: resolve(__dirname, 'src/islands/auth.ts'),
        workspace: resolve(__dirname, 'src/islands/workspace.ts'),
        browser: resolve(__dirname, 'src/islands/browser.ts'),
        voice: resolve(__dirname, 'src/islands/voice.ts'),
        pubsub: resolve(__dirname, 'src/islands/pubsub.ts')
      },
      output: {
        entryFileNames: '[name].js',
        assetFileNames: '[name][extname]'
      }
    }
  }
});
