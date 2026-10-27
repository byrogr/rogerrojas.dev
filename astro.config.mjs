import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://rogerrojas.dev',
  integrations: [sitemap()],
  markdown: {
    shikiConfig: { theme: 'github-dark-dimmed' },
  },
  // Always emit processed scripts as files: the CSP (script-src 'self') forbids inline scripts.
  vite: {
    build: { assetsInlineLimit: 0 },
  },
});
