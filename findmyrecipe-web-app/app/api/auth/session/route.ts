import { NextResponse } from "next/server"
import { cookies } from "next/headers"

import { LOGIN_GATE_COOKIE_NAME, resolveLoginGateConfig } from "@/lib/login-gate-config"
import { verifyLoginSessionToken } from "@/lib/login-session-token"

export async function GET() {
  const config = resolveLoginGateConfig()

  if (!config.enabled) {
    return NextResponse.json({ authenticated: false })
  }

  const cookieStore = cookies()
  const token = cookieStore.get(LOGIN_GATE_COOKIE_NAME)?.value

  if (!token) {
    return NextResponse.json({ authenticated: false }, { status: 401 })
  }

  try {
    const session = await verifyLoginSessionToken(token)
    if (!session) {
      const response = NextResponse.json({ authenticated: false }, { status: 401 })
      response.cookies.delete(LOGIN_GATE_COOKIE_NAME, { path: "/" })
      return response
    }

    return NextResponse.json({
      authenticated: true,
      email: session.email,
      expiresAt: session.expiresAt.toISOString(),
    })
  } catch (error) {
    const response = NextResponse.json({ authenticated: false }, { status: 401 })
    response.cookies.delete(LOGIN_GATE_COOKIE_NAME, { path: "/" })
    return response
  }
}
