<script setup lang="ts">
import { ref, onUnmounted, watch } from 'vue'
import { usePairingStore } from '../stores/pairing'
import PairingInit from './PairingInit.vue'
import PairingJoin from './PairingJoin.vue'
import { remainingTTL, refreshPairing } from '../utils'

const pairingStore = usePairingStore()
const tokenExists = ref<boolean>(window.location.search.includes('?token'))

watch(remainingTTL, async () => {
    if (remainingTTL.value < 2) {
      await refreshPairing()
    }
})

onUnmounted(() => {
  pairingStore.setAvailableForPairing(false)
})
</script>

<template>
  <div class="pairingInterface">
    <div v-if="tokenExists" class="pairingActions">
      <PairingJoin />
    </div>
    <div v-else class="pairingActions">
      <PairingInit />
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
</style>
