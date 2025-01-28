import '@/assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PairingApp from '@/pairing/PairingApp.vue'

const pairingApp = createApp(PairingApp)

pairingApp.use(createPinia())

pairingApp.mount('#pairingApp')
