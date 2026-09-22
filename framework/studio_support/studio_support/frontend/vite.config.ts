import { defineConfig, type Plugin } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { resolve } from 'node:path';

/**
 * The islands are mounted into server-rendered Jinja pages that only load a
 * single `<script type="module" src="...">` per page. Vite extracts Svelte
 * component `<style>` blocks into CSS assets but has no HTML host to link them
 * from, so without this step the component-scoped styles would never reach the
 * page. This plugin folds every chunk's extracted CSS back into that chunk as a
 * tiny runtime `<style>` injection, keeping the mount contract unchanged.
 */
function studioCssInjectedByJs(): Plugin {
  const decode = (source: string | Uint8Array) =>
    typeof source === 'string' ? source : new TextDecoder().decode(source);

  return {
    name: 'studio-css-injected-by-js',
    apply: 'build',
    enforce: 'post',
    generateBundle(_options, bundle) {
      const cssByFile = new Map<string, string>();
      for (const [fileName, output] of Object.entries(bundle)) {
        if (output.type === 'asset' && fileName.endsWith('.css')) {
          cssByFile.set(fileName, decode(output.source));
        }
      }
      if (cssByFile.size === 0) return;

      for (const [fileName, output] of Object.entries(bundle)) {
        if (output.type !== 'chunk') continue;
        const importedCss = (output as { viteMetadata?: { importedCss?: Set<string> } }).viteMetadata?.importedCss;
        if (!importedCss || importedCss.size === 0) continue;

        const css = [...importedCss]
          .map((name) => cssByFile.get(name) ?? '')
          .filter(Boolean)
          .join('\n');
        if (!css) continue;

        const label = output.name ?? fileName.replace(/\.js$/, '');
        const injection =
          `(function(){if(typeof document==="undefined")return;try{` +
          `var s=document.createElement("style");` +
          `s.setAttribute("data-studio-island",${JSON.stringify(label)});` +
          `s.textContent=${JSON.stringify(css)};` +
          `document.head.appendChild(s);}catch(e){}})();`;
        output.code = `${injection}\n${output.code}`;
      }

      for (const fileName of cssByFile.keys()) {
        delete bundle[fileName];
      }
    }
  };
}

export default defineConfig({
  plugins: [svelte(), studioCssInjectedByJs()],
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
