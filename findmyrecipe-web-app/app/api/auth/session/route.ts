import { NextRequest, NextResponse } from "next/server"

import { z } from "zod"

import { LOGIN_GATE_COOKIE_NAME, resolveLoginGateConfig } from "@/lib/login-gate-config"
import { getLoginSessionByCode } from "@/lib/login-gate-repository"
import { createLoginSessionToken, verifyLoginSessionToken } from "@/lib/login-session-token"

const postSchema = z.object({
  code: z.string().min(1).max(128),
})

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

export async function POST(request: NextRequest) {
  const config = resolveLoginGateConfig()

  if (!config.enabled) {
    return NextResponse.json({ authenticated: false }, { status: 404 })
  }

  const existingToken = request.cookies.get(LOGIN_GATE_COOKIE_NAME)?.value ?? null
  let shouldClearCookie = false

  if (existingToken) {
    try {
      const session = await verifyLoginSessionToken(existingToken)
      if (session) {
        return NextResponse.json({
          authenticated: true,
          email: session.email,
          expiresAt: session.expiresAt.toISOString(),
          restored: false,
        })
      }
      shouldClearCookie = true
    } catch (error) {
      shouldClearCookie = true
    }
  }

  const body = await request.json().catch(() => null)
  if (!body) {
    return NextResponse.json({ error: "Invalid request" }, { status: 400 })
  }

  const parsed = postSchema.safeParse(body)
  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid session code" }, { status: 400 })
  }

  const { code } = parsed.data
  const session = await getLoginSessionByCode(code)

  if (!session) {
    const response = NextResponse.json({ authenticated: false }, { status: 401 })
    if (shouldClearCookie) {
      response.cookies.delete(LOGIN_GATE_COOKIE_NAME, { path: "/" })
    }
    return response
  }

  const { email, expiresAt } = session
  const token = await createLoginSessionToken(email, expiresAt)
  const response = NextResponse.json({
    authenticated: true,
    email,
    expiresAt: expiresAt.toISOString(),
    restored: true,
  })

  response.cookies.set({
    name: LOGIN_GATE_COOKIE_NAME,
    value: token,
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    expires: expiresAt,
    path: "/",
  })

  return response
}
