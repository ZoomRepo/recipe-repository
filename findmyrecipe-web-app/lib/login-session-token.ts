const encoder = new TextEncoder()

let cachedKey: CryptoKey | null = null

function getSecret(): string {
  const secret = process.env.LOGIN_SESSION_SECRET || process.env.AUTH_SECRET || process.env.NEXTAUTH_SECRET
  if (!secret) {
    throw new Error("LOGIN_SESSION_SECRET (or AUTH_SECRET) must be set to issue login session tokens")
  }
  return secret
}

function getSubtleCrypto(): SubtleCrypto {
  if (typeof globalThis.crypto !== "undefined" && globalThis.crypto.subtle) {
    return globalThis.crypto.subtle
  }
  throw new Error("Web Crypto API is not available in this runtime")
}

async function getKey(): Promise<CryptoKey> {
  if (cachedKey) {
    return cachedKey
  }

  const subtle = getSubtleCrypto()
  const key = await subtle.importKey(
    "raw",
    encoder.encode(getSecret()),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign", "verify"]
  )
  cachedKey = key
  return key
}

function bufferToHex(buffer: ArrayBuffer): string {
  return Array.from(new Uint8Array(buffer))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("")
}

function hexToArrayBuffer(hex: string): ArrayBuffer {
  if (hex.length % 2 !== 0) {
    throw new Error("Invalid hex string")
  }
  const bytes = new Uint8Array(hex.length / 2)
  for (let i = 0; i < hex.length; i += 2) {
    bytes[i / 2] = Number.parseInt(hex.slice(i, i + 2), 16)
  }
  return bytes.buffer
}

export async function createLoginSessionToken(
  email: string,
  sessionId: string,
  expiresAt: Date
): Promise<string> {
  const encodedEmail = encodeURIComponent(email)
  const safeSessionId = encodeURIComponent(sessionId)
  const expiry = expiresAt.getTime()
  const payload = `${encodedEmail}.${safeSessionId}.${expiry}`
  const key = await getKey()
  const subtle = getSubtleCrypto()
  const signatureBuffer = await subtle.sign("HMAC", key, encoder.encode(payload))
  const signatureHex = bufferToHex(signatureBuffer)
  return `${payload}.${signatureHex}`
}

export async function verifyLoginSessionToken(
  token: string
): Promise<{ email: string; sessionId: string; expiresAt: Date } | null> {
  const parts = token.split(".")
  if (parts.length < 4) {
    return null
  }

  const signatureHex = parts.pop()
  const expiresRaw = parts.pop()
  const encodedSessionId = parts.pop()
  const encodedEmail = parts.join(".")

  if (!encodedEmail || !encodedSessionId || !expiresRaw || !signatureHex) {
    return null
  }

  const expiresMs = Number.parseInt(expiresRaw, 10)
  if (!Number.isFinite(expiresMs)) {
    return null
  }

  const expiresAt = new Date(expiresMs)
  if (expiresAt.getTime() <= Date.now()) {
    return null
  }

  const payload = `${encodedEmail}.${encodedSessionId}.${expiresRaw}`
  try {
    const signatureBuffer = hexToArrayBuffer(signatureHex)
    const key = await getKey()
    const subtle = getSubtleCrypto()
    const verified = await subtle.verify("HMAC", key, signatureBuffer, encoder.encode(payload))
    if (!verified) {
      return null
    }
  } catch (error) {
    return null
  }

  try {
    const email = decodeURIComponent(encodedEmail)
    const sessionId = decodeURIComponent(encodedSessionId)
    return { email, sessionId, expiresAt }
  } catch (error) {
    return null
  }
}
