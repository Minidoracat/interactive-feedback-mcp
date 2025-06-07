import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'

// Import global styles
import './assets/styles/main.scss'
import './assets/styles/components.scss'

// Create Vue application
const app = createApp(App)

// Install Pinia for state management
const pinia = createPinia()
app.use(pinia)

// Mount the application
app.mount('#app')

// Development helpers
if (import.meta.env.DEV) {
  console.log('🎯 MCP Feedback Enhanced Frontend')
  console.log('📦 Vue.js 3 + Vite + Pinia')
  console.log('🔧 Development mode enabled')
}
