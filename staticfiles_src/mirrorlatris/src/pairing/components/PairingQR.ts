import { ref } from 'vue'
import QRCode from 'qrcode'
import { BASE_URL } from '../utils'
import type { PairingObject } from '../types'

export const qrCodeUrl = ref<string>('')
export const qrCodeImage = ref<string>('')

const qrlib = {
  async generateQRCode(currentPairing: PairingObject | null) {
    qrCodeUrl.value = `${BASE_URL}/pairing/?token=${currentPairing ? currentPairing.token : ''}`
    qrCodeImage.value = await QRCode.toDataURL(qrCodeUrl.value)
  },
}

export default qrlib
