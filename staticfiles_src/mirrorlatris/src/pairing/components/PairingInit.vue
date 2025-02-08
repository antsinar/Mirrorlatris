<script setup lang="ts">
import { usePairingStore } from '../stores/pairing'
import { ref } from 'vue'
import qrlib from './PairingQR'
import { remainingTTL, handleAvailabilityToggle, refreshPairing } from '../utils'
import { qrCodeImage, qrCodeUrl } from './PairingQR'

const pairingStore = usePairingStore()
const isLoading = ref<boolean>(false)

async function startPairing(): Promise<void> {
  try {
    isLoading.value = true
    await pairingStore.initiatePairing()
    await qrlib.generateQRCode(pairingStore.state.currentPairing)
  } catch (error) {
    console.error(error)
  } finally {
    isLoading.value = false
    setInterval(async () => {
      remainingTTL.value = 
      (remainingTTL.value % 10 === 0)
      ? await pairingStore.getRemainingTTL() 
      : remainingTTL.value - 1
    }, 1000)
  }
}
</script>

<template>
  <div class="">
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
</template>

<style scoped>
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
