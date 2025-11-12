import { NextRequest, NextResponse } from "next/server"

import { LOGIN_GATE_COOKIE_NAME, resolveLoginGateConfig } from "@/lib/login-gate-config"
import { getLoginSessionByToken } from "@/lib/login-gate-repository"
import { verifyLoginSessionToken } from "@/lib/login-session-token"

export const runtime = "nodejs"

export async function GET(request: NextRequest) {
  const config = resolveLoginGateConfig()

  if (!config.enabled) {
    return NextResponse.json({ authenticated: false })
  }

  const token = request.cookies.get(LOGIN_GATE_COOKIE_NAME)?.value

  if (!token) {
    return NextResponse.json({ authenticated: false }, { status: 401 })
  }

  try {
    const decoded = await verifyLoginSessionToken(token)
    if (!decoded) {
      const response = NextResponse.json({ authenticated: false }, { status: 401 })
      response.cookies.delete(LOGIN_GATE_COOKIE_NAME, { path: "/" })
      return response
    }

    const dbSession = await getLoginSessionByToken(token)
    if (!dbSession || dbSession.email.trim().toLowerCase() !== decoded.email.trim().toLowerCase()) {
      const response = NextResponse.json({ authenticated: false }, { status: 401 })
      response.cookies.delete(LOGIN_GATE_COOKIE_NAME, { path: "/" })
      return response
    }

    return NextResponse.json({
      authenticated: true,
      email: dbSession.email,
      expiresAt: dbSession.expiresAt.toISOString(),
    })
  } catch (error) {
    const response = NextResponse.json({ authenticated: false }, { status: 401 })
    response.cookies.delete(LOGIN_GATE_COOKIE_NAME, { path: "/" })
    return response
  }
}
