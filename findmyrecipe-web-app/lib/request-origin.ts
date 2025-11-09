import type { NextRequest } from "next/server"

function sanitize(value: string | null): string | null {
  if (!value) return null

  const trimmed = value.trim()
  if (!trimmed) return null

  const normalized = trimmed.toLowerCase()
  if (normalized === "null" || normalized === "(null)" || normalized === "undefined") {
    return null
  }

  return trimmed
}

function firstHeaderValue(value: string | null): string | null {
  if (!value) return null
  const [first] = value.split(",")
  return sanitize(first)
}

export function getRequestOrigin(request: NextRequest): string {
  const forwardedHost = firstHeaderValue(request.headers.get("x-forwarded-host"))
  const host = forwardedHost || firstHeaderValue(request.headers.get("host"))

  const forwardedProto = firstHeaderValue(request.headers.get("x-forwarded-proto"))
  const protocol = forwardedProto || sanitize(request.nextUrl.protocol.replace(/:$/, "")) || "https"

  if (host) {
    return `${protocol}://${host}`
  }

  const urlHost = sanitize(request.nextUrl.hostname)
  if (urlHost) {
    const port = sanitize(request.nextUrl.port)
    const hostWithPort = port ? `${urlHost}:${port}` : urlHost
    return `${protocol}://${hostWithPort}`
  }

  return `${protocol}://localhost`
}
