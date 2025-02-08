import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { v4 as uuidv4 } from 'uuid'

import { BASE_URL } from "@/pairing/utils"
import type { PairingState, PairingObject, PairingComplete, Device } from '@/pairing/types.ts'

const DEVICE_ID_KEY = 'deviceId'
const PAIR_TOKEN_KEY = 'pairtoken'

export const usePairingStore = defineStore('pairing', () => {
  const state = ref<PairingState>({
    isAvailableForPairing: false,
    currentPairing: null,
    deviceId: localStorage.getItem(DEVICE_ID_KEY) || generateDeviceId(),
    pairingTimer: 1000,
  })

  const isPaired = computed(() => {
    return state.value.currentPairing !== null
  })

  async function getRemainingTTL(): Promise<number> {
    const token: string = localStorage.getItem(PAIR_TOKEN_KEY) || ''
    const response = await fetch(`${BASE_URL}/pairing/remaining/?token=${token}`)
    if (!response.ok) {
      return -1
    }
    const obj = (await response.json()) as PairingObject
    return obj.ttl
  }

  async function initiatePairing(): Promise<void> {
    try {
      let headers = new Headers()
      headers.append('Content-Type', 'application/json')
      const csrfToken = getCookie('csrftoken')
      csrfToken ? headers.append('X-CSRFToken', csrfToken) : headers.append('X-CSRFToken', '')

      const response = await fetch(`${BASE_URL}/pairing/initialize/`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({
          deviceId: state.value.deviceId,
        }),
      })
      if (!response.ok) {
        throw new Error(`Pair Creation Failed ${response.statusText}`)
      }

      const pairingObject: PairingObject = await response.json()
      state.value.currentPairing = pairingObject
      localStorage.setItem(PAIR_TOKEN_KEY, pairingObject.token)
    } catch (error: any) {
      console.error(error)
    }
  }

  async function completePairing(token: string): Promise<void> {
    try {
      let headers = new Headers()
      headers.append('Content-Type', 'application/json')
      const csrfToken = getCookie('csrftoken')
      csrfToken ? headers.append('X-CSRFToken', csrfToken) : headers.append('X-CSRFToken', '')

      const device = {
        deviceId: state.value.deviceId,
        available: true,
      } as Device

      const pairingComplete = {
        token: token,
        device: device,
      } as PairingComplete

      const response = await fetch(`${BASE_URL}/pairing/complete/`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(pairingComplete),
      })
      if (!response.ok) {
        throw new Error(`Pairing Failed ${response.statusText}`)
      }
      const pairingObject = (await response.json()) as PairingObject
      state.value.currentPairing = pairingObject
      localStorage.setItem(PAIR_TOKEN_KEY, token)
    } catch (error: any) {
      console.error(error)
    }
  }

  async function refreshPairing(): Promise<void> {
    if (!state.value.currentPairing) {
      return
    }
    const device = {
      deviceId: state.value.deviceId,
      available: true,
    } as Device

    const pairingComplete = {
      token: state.value.currentPairing.token,
      device: device,
    } as PairingComplete
    try {
      let headers = new Headers()
      headers.append('Content-Type', 'application/json')
      const csrfToken = getCookie('csrftoken')
      csrfToken ? headers.append('X-CSRFToken', csrfToken) : headers.append('X-CSRFToken', '')

      const response = await fetch(`${BASE_URL}/pairing/refresh/`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(pairingComplete),
      })

      if (!response.ok) {
        throw new Error('Failed to refresh pairing')
      }

      const pairingObject: PairingObject = await response.json()
      state.value.currentPairing = pairingObject
      localStorage.setItem(PAIR_TOKEN_KEY, pairingObject.token)
    } catch (error) {
      console.error(`Pairing refresh failed: ${error}`)
      state.value.currentPairing = null
    }
  }

  function generateDeviceId(): string {
    const deviceId = uuidv4().toString()
    localStorage.setItem(DEVICE_ID_KEY, deviceId)
    return deviceId
  }

  function setAvailableForPairing(available: boolean): void {
    state.value.isAvailableForPairing = available
    if (!available && state.value.currentPairing) {
      state.value.currentPairing = null
    }
  }

  function getCookie(name: string): string | null {
    let cookieValue: string | null = null
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';')
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim()
        if (cookie.substring(0, name.length + 1) === name + '=') {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1))
          break
        }
      }
    }
    return cookieValue
  }

  return {
    state,
    isPaired,
    getRemainingTTL,
    initiatePairing,
    completePairing,
    refreshPairing,
    setAvailableForPairing,
  }
})
