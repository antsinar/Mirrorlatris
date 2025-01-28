import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { v4 as uuidv4 } from 'uuid'

import type { PairingState, PairingObject, PairingComplete, Device } from '@/pairing/types.ts'

const BASE_URL = 'http://127.0.0.1:8000'
const DEVICE_ID_KEY = 'deviceId'
const PAIR_TOKEN_KEY = 'pairtoken'

export const usePairingStore = defineStore('pairing', () => {
  const state = ref<PairingState>({
    isAvailableForPairing: false,
    currentPairing: null,
    deviceId: localStorage.getItem(DEVICE_ID_KEY) || generateDeviceId(),
    pairingTimer: -1,
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
      await getCookie('csrftoken').then((token: string | null) => {
        token ? headers.append('X-CSRFToken', token) : undefined
      })

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
      startPairingTimer(pairingObject.ttl)
    } catch (error: any) {
      console.error(error)
    }
  }

  async function completePairing(): Promise<void> {
    try {
      let headers = new Headers()
      headers.append('Content-Type', 'application/json')
      await getCookie('csrftoken').then((token: string | null) => {
        token ? headers.append('X-CSRFToken', token) : undefined
      })

      const device = {
        deviceId: state.value.deviceId,
        available: true,
      } as Device

      const pairingComplete = {
        token: localStorage.getItem(PAIR_TOKEN_KEY) || null,
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
      const pairingObject: PairingObject = await response.json()
      state.value.currentPairing = pairingObject
      startPairingTimer(pairingObject.ttl)
    } catch (error: any) {
      console.error(error)
    }
  }

  async function refreshPairing(): Promise<void> {
    if (!state.value.currentPairing) {
      return
    }
    try {
      let headers = new Headers()
      headers.append('Content-Type', 'application/json')
      await getCookie('csrftoken').then((token: string | null) => {
        token ? headers.append('X-CSRFToken', token) : undefined
      })

      const response = await fetch(`${BASE_URL}/pairing/refresh/`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({
          token: state.value.currentPairing.token,
          deviceId: state.value.deviceId,
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to refresh pairing')
      }

      const pairingObject: PairingObject = await response.json()
      state.value.currentPairing = pairingObject
      startPairingTimer(pairingObject.ttl)
    } catch (error) {
      console.error('Pairing refresh failed:', error)
      state.value.currentPairing = null
    }
  }

  function generateDeviceId(): string {
    const deviceId = uuidv4().toString()
    localStorage.setItem(DEVICE_ID_KEY, deviceId)
    return deviceId
  }

  function startPairingTimer(ttl: number): void {
    if (state.value.pairingTimer) {
      clearTimeout(state.value.pairingTimer)
    }

    state.value.pairingTimer = window.setTimeout(() => {
      if (state.value.isAvailableForPairing) {
        refreshPairing()
      } else {
        state.value.currentPairing = null
      }
    }, ttl * 1000)
  }

  function setAvailableForPairing(available: boolean): void {
    state.value.isAvailableForPairing = available
    if (!available && state.value.currentPairing) {
      state.value.currentPairing = null
      if (state.value.pairingTimer) {
        clearTimeout(state.value.pairingTimer)
      }
    }
  }

  async function getCookie(name: string): Promise<string | null> {
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
