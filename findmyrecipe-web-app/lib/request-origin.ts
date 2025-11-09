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
  const trimmed = first?.trim()
  return trimmed ? trimmed : null
}

function stripWrappingParens(value: string): string {
  return value.replace(/^\(+/, "").replace(/\)+$/, "")
}

function sanitizeHost(value: string | null): string | null {
  const sanitized = sanitize(value)
  if (!sanitized) return null

  const withoutParens = stripWrappingParens(sanitized)
  // Treat common placeholder values (often injected by misconfigured proxies) as missing
  const placeholderCandidate = withoutParens.split(":")[0]?.trim().toLowerCase()
  if (placeholderCandidate === "null" || placeholderCandidate === "undefined") {
    return null
  }

  try {
    const parsed = new URL(`http://${withoutParens}`)
    const hostname = parsed.hostname.toLowerCase()
    if (hostname === "null" || hostname === "undefined") {
      return null
    }
    return parsed.host || null
  } catch {
    if (/\b(null|undefined)\b/i.test(withoutParens.replace(/[^a-z0-9]+/gi, " "))) {
      return null
    }
    return null
  }
}

export function getRequestOrigin(request: NextRequest): string {
  const forwardedHost = sanitizeHost(firstHeaderValue(request.headers.get("x-forwarded-host")))
  const host = forwardedHost || sanitizeHost(firstHeaderValue(request.headers.get("host")))

  const forwardedProto = sanitize(firstHeaderValue(request.headers.get("x-forwarded-proto")))
  const protocol = forwardedProto || sanitize(request.nextUrl.protocol.replace(/:$/, "")) || "https"

  if (host) {
    return `${protocol}://${host}`
  }

  const urlHost = sanitizeHost(request.nextUrl.host)
  if (urlHost) {
    return `${protocol}://${urlHost}`
  }

  return `${protocol}://localhost`
}
