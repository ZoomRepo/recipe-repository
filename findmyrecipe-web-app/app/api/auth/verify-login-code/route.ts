import { NextResponse } from "next/server"
import { z } from "zod"

import { LOGIN_GATE_COOKIE_NAME, resolveLoginGateConfig } from "@/lib/login-gate-config"
import { consumeLoginCode, isEmailWhitelisted } from "@/lib/login-gate-repository"
import { createLoginSessionToken } from "@/lib/login-session-token"

const requestSchema = z.object({
  email: z.string().email(),
  code: z.string().regex(/^\d{6}$/),
})

export async function POST(request: Request) {
  const config = resolveLoginGateConfig()

  if (!config.enabled) {
    return NextResponse.json({ error: "Temporary login is disabled" }, { status: 404 })
  }

  const body = await request.json().catch(() => null)
  if (!body) {
    return NextResponse.json({ error: "Invalid request" }, { status: 400 })
  }

  const parsed = requestSchema.safeParse(body)
  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid email or code" }, { status: 400 })
  }

  const { email, code } = parsed.data

  const whitelisted = await isEmailWhitelisted(email)
  if (!whitelisted) {
    return NextResponse.json({ error: "This email is not authorized for temporary access" }, { status: 403 })
  }

  const isValid = await consumeLoginCode(email, code)
  if (!isValid) {
    return NextResponse.json({ error: "Invalid or expired code" }, { status: 401 })
  }

  const expiresAt = new Date(Date.now() + config.sessionDurationDays * 24 * 60 * 60 * 1000)
  const token = await createLoginSessionToken(email, expiresAt)
  const response = NextResponse.json({ success: true })

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
