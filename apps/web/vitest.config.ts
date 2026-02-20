import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

export default defineConfig({
    plugins: [react()],
    test: {
        environment: 'jsdom',
        setupFiles: ['./vitest.setup.ts'],
        globals: true,
        include: ['src/**/*.test.ts?(x)'],
        exclude: ['tests/example.spec.ts', 'tests/browse.spec.ts'], // Playwright tests
    },
    resolve: {
        alias: {
            '@': resolve(__dirname, './src'),
        },
    },
})
