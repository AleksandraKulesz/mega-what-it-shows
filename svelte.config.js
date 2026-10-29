import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';
import { mdsvex } from 'mdsvex';
import { fileURLToPath } from 'node:url';

const runbook = fileURLToPath(new URL('./src/lib/layouts/runbook.svelte', import.meta.url));

/** @type {import('@sveltejs/kit').Config} */
export default {
  extensions: ['.svelte', '.svx'],
  preprocess: [
    mdsvex({
      extensions: ['.svx'],
      layout: { runbook },
    }),
    vitePreprocess(),
  ],
  kit: {
    adapter: adapter({ pages: 'build', assets: 'build', fallback: undefined, strict: false }),
    alias: { '#lib': 'src/lib' },
    inlineStyleThreshold: Infinity,
    prerender: { handleHttpError: 'warn', handleMissingId: 'warn' },
  },
};
