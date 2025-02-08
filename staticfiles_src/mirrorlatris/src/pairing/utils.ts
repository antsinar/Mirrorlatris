import { ref } from 'vue'
import { usePairingStore } from './stores/pairing'
import qrlib from './components/PairingQR'

export const BASE_URL = 'http://127.0.0.1:8000'

export let remainingTTL = ref<number>(1000)
export async function refreshPairing(): Promise<void> {
  const pairingStore = usePairingStore()

  await pairingStore.refreshPairing()
  await qrlib.generateQRCode(pairingStore.state.currentPairing)
  await new Promise((r) => setTimeout(r, 1000))
  remainingTTL.value = await pairingStore.getRemainingTTL()
}

export function handleAvailabilityToggle(event: Event): void {
  const pairingStore = usePairingStore()

  const target = event.target as HTMLInputElement
  pairingStore.setAvailableForPairing(target.checked)
}
