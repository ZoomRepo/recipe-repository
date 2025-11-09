import { NextRequest, NextResponse } from "next/server"

import { LOGIN_GATE_COOKIE_NAME, resolveLoginGateConfig } from "@/lib/login-gate-config"
import { getLoginSessionByCode } from "@/lib/login-gate-repository"
import { createLoginSessionToken } from "@/lib/login-session-token"
import { getRequestOrigin } from "@/lib/request-origin"

function sanitizeRedirect(target: string | null): string {
  if (!target) return "/"
  if (!target.startsWith("/")) return "/"
  if (target.startsWith("/auth/session")) return "/"
  return target
}

function buildLoginRedirect(request: NextRequest, redirectPath: string) {
  const origin = getRequestOrigin(request)
  const loginUrl = new URL("/auth/login", origin)
  if (redirectPath && redirectPath !== "/") {
    loginUrl.searchParams.set("redirect", redirectPath)
  }
  loginUrl.searchParams.set("error", "session")
  return loginUrl
}

export async function GET(request: NextRequest) {
  const config = resolveLoginGateConfig()
  const { searchParams } = request.nextUrl

  const code = searchParams.get("code")
  const redirectParam = sanitizeRedirect(searchParams.get("redirect"))
  const redirectPath = redirectParam || "/"

  if (!config.enabled || !code) {
    return NextResponse.redirect(buildLoginRedirect(request, redirectPath))
  }

  const session = await getLoginSessionByCode(code)
  if (!session) {
    return NextResponse.redirect(buildLoginRedirect(request, redirectPath))
  }

  const expiresAt = session.expiresAt instanceof Date ? session.expiresAt : new Date(session.expiresAt)
  if (Number.isNaN(expiresAt.getTime()) || expiresAt.getTime() <= Date.now()) {
    return NextResponse.redirect(buildLoginRedirect(request, redirectPath))
  }

  const token = await createLoginSessionToken(session.email, expiresAt)

  const origin = getRequestOrigin(request)
  const destination = new URL(redirectPath, origin)
  const response = NextResponse.redirect(destination)
  response.cookies.set({
    name: LOGIN_GATE_COOKIE_NAME,
    value: token,
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    expires: expiresAt,
    path: "/",
  })
  response.headers.set("Cache-Control", "no-store")
  return response
}
