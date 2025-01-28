export interface PairingObject {
  token: string
  ttl: number
}

export interface PairingState {
  isAvailableForPairing: boolean
  currentPairing: PairingObject | null
  deviceId: string
  pairingTimer: number
}

export interface Device {
  deviceId: string
  available: boolean
}

export interface PairingComplete {
  token: string
  device: Device
}
