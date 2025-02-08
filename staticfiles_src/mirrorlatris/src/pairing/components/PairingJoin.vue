<script setup lang="ts">
import { BASE_URL, handleAvailabilityToggle, refreshPairing } from '../utils'
import { usePairingStore } from '../stores/pairing'

const pairingStore = usePairingStore()

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
      <button v-if="!pairingStore.isPaired" @click="joinPairing">Join</button>
      <div v-if="pairingStore.state.currentPairing">
        <h3>Success</h3>
        <p>{{ pairingStore.state.currentPairing.token }}</p>
        <button @click="refreshPairing">Refresh</button>
      </div>
    </div>
  </div>
</template>

<style scoped></style>
