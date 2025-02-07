<script setup lang="ts">
import { ref, onUnmounted } from 'vue'
import { usePairingStore } from '../stores/pairing'
import QRCode from 'qrcode'

const pairingStore = usePairingStore()
const qrCodeUrl = ref<string>('')
const qrCodeImage = ref<string>('')
const isLoading = ref<boolean>(false)
const remainingTTL = ref<number>(1000)
const tokenExists = ref<boolean>(window.location.search.includes('?token'))

const BASE_URL = 'http://127.0.0.1:8000'

async function startPairing(): Promise<void> {
  try {
    isLoading.value = true
    await pairingStore.initiatePairing()
    const currentPairing = pairingStore.state.currentPairing
    qrCodeUrl.value = `${BASE_URL}/pairing/?token=${currentPairing ? currentPairing.token : ''}`
    qrCodeImage.value = await QRCode.toDataURL(qrCodeUrl.value)
  } catch (error) {
    console.error(error)
  } finally {
    isLoading.value = false
    const intervalTaskId = setInterval(async () => {
      remainingTTL.value =
        remainingTTL.value % 10 === 0
          ? await pairingStore.getRemainingTTL()
          : remainingTTL.value - 1
    }, 1000)
  }
}

async function joinPairing(event: Event): Promise<void> {
  try {
    event.preventDefault()
    if (BASE_URL.includes(window.location.host)) {
      await pairingStore.completePairing(window.location.search.split('=')[1])
    }
  } catch (err) {
    console.error(err)
  }
}

async function refreshPairing(): Promise<void> {
  await pairingStore.refreshPairing()
  const currentPairing = pairingStore.state.currentPairing
  qrCodeUrl.value = `${BASE_URL}/pairing/?token=${currentPairing ? currentPairing.token : ''}`
  qrCodeImage.value = await QRCode.toDataURL(qrCodeUrl.value)
  await new Promise(r => setTimeout(r, 1000));
  remainingTTL.value = await pairingStore.getRemainingTTL()
}

function handleAvailabilityToggle(event: Event): void {
  const target = event.target as HTMLInputElement
  pairingStore.setAvailableForPairing(target.checked)
}

async () => {
  while(1){
    if (remainingTTL.value < 2) {
      await refreshPairing()
    }
    await new Promise<void>(r => setTimeout(r, 1000))
  }
}

onUnmounted(() => {
  pairingStore.setAvailableForPairing(false)
})
</script>

<template>
  <div class="pairingInterface">
    <div v-if="tokenExists" class="pairingActions">
      <div class="pairingToggle">
        <label for="pairingToggleSwitch">Available for pairing</label>
        <input
          type="checkbox"
          v-model="pairingStore.state.isAvailableForPairing"
          @change="handleAvailabilityToggle"
          name="pairingToggleSwitch"
          id="pairingToggleSwitch"
        />
      </div>
      <div v-if="pairingStore.state.isAvailableForPairing" class="pairingActions">
        <button v-if="!pairingStore.isPaired" @click="joinPairing">Join</button>
        <div v-if="pairingStore.state.currentPairing">
          <h3>Success</h3>
          <p>{{ pairingStore.state.currentPairing.token }}</p>
          <button @click="refreshPairing">Refresh</button>
        </div>
      </div>
    </div>
    <div v-else>
      <div class="pairingToggle">
        <label for="pairingToggleSwitch">Available for pairing</label>
        <input
          type="checkbox"
          v-model="pairingStore.state.isAvailableForPairing"
          @change="handleAvailabilityToggle"
          name="pairingToggleSwitch"
          id="pairingToggleSwitch"
        />
      </div>
      <div v-if="pairingStore.state.isAvailableForPairing" class="pairingActions">
        <button v-if="!pairingStore.isPaired" @click="startPairing" :disabled="isLoading">
          StartPairing
        </button>
        <div v-if="qrCodeImage" class="qrCode">
          <img :src="qrCodeImage" alt="Pairing QR Code" />
          <p>Scan this QR code with another device to complete pairing</p>
          <p>Or visit: {{ qrCodeUrl }}</p>
        </div>
        <div v-if="pairingStore.isPaired" class="pairingStatus">
          <h1>Pair Initialized successfully</h1>
          <p>Pairing active for {{ remainingTTL }}&nbsp;seconds</p>
          <button @click="refreshPairing">Refresh</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pairingInterface {
  padding: 1rem;
}

.pairingToggle {
  margin-bottom: 1rem;
}

.pairingActions {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.qrCode {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.qrCode img {
  max-width: 10rem;
}

.pairingStatus {
  border: 1px solid #ccc;
  padding: 1rem;
  border-radius: 4px;
}
</style>
