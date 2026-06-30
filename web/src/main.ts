import './assets/main.css'

import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import { initBridgeContext } from './request'

const app = createApp(App)
const bridge = (window as Window & { AstrBotPluginPage?: unknown }).AstrBotPluginPage
if (bridge) {
	await initBridgeContext()
}

app.use(router)
app.use(ElementPlus)

app.mount('#app')
