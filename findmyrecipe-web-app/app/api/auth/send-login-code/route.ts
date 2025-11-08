import { NextResponse } from "next/server"
import { z } from "zod"

import { resolveLoginGateConfig } from "@/lib/login-gate-config"
import {
  generateLoginCode,
  hasActiveLoginSession,
  isEmailWhitelisted,
  storeLoginCode,
} from "@/lib/login-gate-repository"
import { sendLoginCodeEmail } from "@/lib/email-service"

const requestSchema = z.object({
  email: z.string().email(),
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
    return NextResponse.json({ error: "Please provide a valid email address" }, { status: 400 })
  }

  const { email } = parsed.data

  const whitelisted = await isEmailWhitelisted(email)
  if (!whitelisted) {
    return NextResponse.json({ error: "This email is not authorized for temporary access" }, { status: 403 })
  }

  const alreadyVerified = await hasActiveLoginSession(email)
  if (alreadyVerified) {
    return NextResponse.json({ success: true, alreadyVerified: true })
  }

  const code = generateLoginCode()
  const expiresAt = new Date(Date.now() + config.codeExpiryMinutes * 60 * 1000)
  await storeLoginCode(email, code, expiresAt)
  await sendLoginCodeEmail({ recipient: email, code })

  return NextResponse.json({ success: true })
}
