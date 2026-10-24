import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base './' lets the built site work from any folder (GitHub Pages, Netlify, Vercel)
export default defineConfig({
  plugins: [react()],
  base: './',
  build: {
    rollupOptions: {
      output: {
        // libraries in their own files, so browsers cache them between app updates
        manualChunks: { charts: ['recharts'], react: ['react', 'react-dom', 'react-router-dom'] },
      },
    },
  },
})
