import { NextResponse } from "next/server"
import { z } from "zod"

import { resolveLoginGateConfig } from "@/lib/login-gate-config"
import {
  consumeLoginCode,
  generateLoginSessionCode,
  isEmailWhitelisted,
  storeLoginSessionCode,
} from "@/lib/login-gate-repository"

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
  const sessionCode = generateLoginSessionCode()
  await storeLoginSessionCode(email, sessionCode, expiresAt)

  return NextResponse.json({
    success: true,
    sessionCode,
    expiresAt: expiresAt.toISOString(),
  })
}
