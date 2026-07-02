import { fileURLToPath, URL } from 'node:url';

import { PrimeVueResolver } from '@primevue/auto-import-resolver';
import tailwindcss from '@tailwindcss/vite';
import vue from '@vitejs/plugin-vue';
import Components from 'unplugin-vue-components/vite';
import { defineConfig } from 'vite';

function getPackageName(id) {
    const normalizedId = id.replaceAll('\\', '/');
    const parts = normalizedId.split('/node_modules/');
    const packagePath = parts[parts.length - 1];

    if (!packagePath) {
        return null;
    }

    if (packagePath.startsWith('@')) {
        const [scope, name] = packagePath.split('/');
        return `${scope}/${name}`;
    }

    return packagePath.split('/')[0];
}

function normalizeChunkName(name) {
    return name.replaceAll('@', '').replaceAll('/', '-');
}

// https://vitejs.dev/config/
export default defineConfig({
    optimizeDeps: {
        noDiscovery: true
    },
    plugins: [
        vue(),
        tailwindcss(),
        Components({
            resolvers: [PrimeVueResolver()]
        })
    ],
    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./src', import.meta.url))
        }
    },
    build: {
        rollupOptions: {
            output: {
                manualChunks(id) {
                    if (!id.includes('node_modules')) {
                        return undefined;
                    }

                    const normalizedId = id.replaceAll('\\', '/');
                    const packageName = getPackageName(id);

                    if (packageName === 'vue' || packageName === 'vue-router' || packageName === 'vue-devtools-api') {
                        return 'vue-core';
                    }

                    if (packageName === '@primeuix/themes') {
                        return 'primevue-theme';
                    }

                    if (packageName === '@primeuix/styled' || packageName === '@primeuix/utils') {
                        return 'primevue-theme-utils';
                    }

                    if (packageName === 'primevue') {
                        if (
                            normalizedId.includes('/primevue/datatable/') ||
                            normalizedId.includes('/primevue/column/') ||
                            normalizedId.includes('/primevue/chart/')
                        ) {
                            return 'primevue-data';
                        }

                        if (
                            normalizedId.includes('/primevue/dialog/') ||
                            normalizedId.includes('/primevue/confirmdialog/') ||
                            normalizedId.includes('/primevue/toast/') ||
                            normalizedId.includes('/primevue/menu/') ||
                            normalizedId.includes('/primevue/tabs/') ||
                            normalizedId.includes('/primevue/tag/') ||
                            normalizedId.includes('/primevue/message/') ||
                            normalizedId.includes('/primevue/progressspinner/') ||
                            normalizedId.includes('/primevue/tooltip/') ||
                            normalizedId.includes('/primevue/skeleton/')
                        ) {
                            return 'primevue-overlays';
                        }

                        if (
                            normalizedId.includes('/primevue/button/') ||
                            normalizedId.includes('/primevue/inputtext/') ||
                            normalizedId.includes('/primevue/inputnumber/') ||
                            normalizedId.includes('/primevue/textarea/') ||
                            normalizedId.includes('/primevue/select/') ||
                            normalizedId.includes('/primevue/selectbutton/') ||
                            normalizedId.includes('/primevue/toggleswitch/') ||
                            normalizedId.includes('/primevue/password/') ||
                            normalizedId.includes('/primevue/checkbox/') ||
                            normalizedId.includes('/primevue/radiobutton/')
                        ) {
                            return 'primevue-forms';
                        }

                        return 'primevue-core';
                    }

                    if (packageName === 'chart.js') {
                        return 'charts';
                    }

                    if (packageName === 'jspdf') {
                        return 'export-pdf';
                    }

                    if (packageName === 'xlsx') {
                        return 'export-excel';
                    }

                    return packageName ? `vendor-${normalizeChunkName(packageName)}` : 'vendor';
                }
            }
        }
    },
    css: {
        preprocessorOptions: {
            scss: {
                api: 'modern-compiler'
            }
        }
    }
});
