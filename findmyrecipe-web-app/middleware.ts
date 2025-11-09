import { NextResponse, type NextRequest } from "next/server"

import { LOGIN_GATE_COOKIE_NAME, resolveLoginGateConfig } from "@/lib/login-gate-config"
import { verifyLoginSessionToken } from "@/lib/login-session-token"

const PUBLIC_PATHS = [
  "/auth/login",
  "/auth/sign-up",
  "/auth/sign-up-success",
  "/api/auth/send-login-code",
  "/api/auth/verify-login-code",
  "/api/auth/session",
  "/auth/session/finalize",
  "/app/manifest.json",
  "/manifest.json",
]

function isPublicPath(pathname: string) {
  return PUBLIC_PATHS.some((path) => pathname.startsWith(path))
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const config = resolveLoginGateConfig()

  if (!config.enabled || isPublicPath(pathname)) {
    return NextResponse.next()
  }

  const token = request.cookies.get(LOGIN_GATE_COOKIE_NAME)?.value

  if (!token) {
    const loginUrl = new URL("/auth/login", request.url)
    loginUrl.searchParams.set("redirect", pathname)
    return NextResponse.redirect(loginUrl)
  }

  let sessionValid = false
  try {
    sessionValid = (await verifyLoginSessionToken(token)) !== null
  } catch (error) {
    sessionValid = false
  }

  if (!sessionValid) {
    const response = NextResponse.redirect(new URL("/auth/login", request.url))
    response.cookies.delete(LOGIN_GATE_COOKIE_NAME, { path: "/" })
    return response
  }

  return NextResponse.next()
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"],
}
