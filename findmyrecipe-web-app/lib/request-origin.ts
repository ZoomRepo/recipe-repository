import type { NextRequest } from "next/server"

function firstHeaderValue(value: string | null): string | null {
  if (!value) return null
  const [first] = value.split(",")
  return first?.trim() || null
}

export function getRequestOrigin(request: NextRequest): string {
  const forwardedHost = firstHeaderValue(request.headers.get("x-forwarded-host"))
  const host = forwardedHost || firstHeaderValue(request.headers.get("host"))

  const forwardedProto = firstHeaderValue(request.headers.get("x-forwarded-proto"))
  const protocol = forwardedProto || request.nextUrl.protocol.replace(/:$/, "") || "https"

  if (host) {
    return `${protocol}://${host}`
  }

  return request.nextUrl.origin
}
