import { NextResponse, type NextRequest } from "next/server"

import { LOGIN_GATE_COOKIE_NAME, resolveLoginGateConfig } from "@/lib/login-gate-config"
import { verifyLoginSessionToken } from "@/lib/login-session-token"
import { getRequestOrigin } from "@/lib/request-origin"

const PUBLIC_PATHS = [
  "/auth/login",
  "/auth/sign-up",
  "/auth/sign-up-success",
  "/api/auth/send-login-code",
  "/api/auth/verify-login-code",
  "/api/auth/session",
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
    const origin = getRequestOrigin(request)
    const loginUrl = new URL("/auth/login", origin)
    loginUrl.searchParams.set("redirect", pathname)
    return NextResponse.redirect(loginUrl)
  }

  try {
    const decoded = await verifyLoginSessionToken(token)
    if (decoded) {
      return NextResponse.next()
    }
  } catch (error) {
    // fall through to redirect below
  }

  const origin = getRequestOrigin(request)
  const response = NextResponse.redirect(new URL("/auth/login", origin))
  response.cookies.delete(LOGIN_GATE_COOKIE_NAME, { path: "/" })
  return response
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"],
}
