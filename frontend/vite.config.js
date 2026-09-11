// Vite replaces create-react-app (unmaintained). Notes:
//  - components are .js files containing JSX, so esbuild is told to treat
//    src/**/*.js as JSX (both for dev pre-bundling and the build);
//  - the dev server keeps CRA's port and proxies /api to the Flask backend so
//    the session cookie stays first-party (see api.js);
//  - the build lands in build/ - the path nginx serves in production.
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
    plugins: [react()],
    esbuild: {
        loader: 'jsx',
        include: /src\/.*\.jsx?$/,
        exclude: [],
    },
    optimizeDeps: {
        esbuildOptions: { loader: { '.js': 'jsx' } },
    },
    server: {
        port: 3000,
        strictPort: true,
        proxy: {
            '/api': { target: 'http://localhost:5000', changeOrigin: false },
        },
    },
    build: {
        outDir: 'build',
        emptyOutDir: true,
        sourcemap: false,
    },
});
