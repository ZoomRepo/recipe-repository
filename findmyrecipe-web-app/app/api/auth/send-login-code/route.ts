import { NextRequest, NextResponse } from "next/server"
import { z } from "zod"

import { LOGIN_GATE_COOKIE_NAME, resolveLoginGateConfig } from "@/lib/login-gate-config"
import {
  generateLoginCode,
  getLoginSessionByToken,
  isEmailWhitelisted,
  storeLoginCode,
} from "@/lib/login-gate-repository"
import { sendLoginCodeEmail } from "@/lib/email-service"
import { verifyLoginSessionToken } from "@/lib/login-session-token"

const requestSchema = z.object({
  email: z.string().email(),
})

export async function POST(request: NextRequest) {
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
  const normalizedEmail = email.trim().toLowerCase()

  const existingToken = request.cookies.get(LOGIN_GATE_COOKIE_NAME)?.value ?? null
  if (existingToken) {
    try {
      const session = await verifyLoginSessionToken(existingToken)
      if (session) {
        const dbSession = await getLoginSessionByToken(existingToken)
        const sessionEmail = dbSession?.email?.trim().toLowerCase()
        if (sessionEmail && sessionEmail === normalizedEmail) {
          return NextResponse.json({ success: true, alreadyVerified: true })
        }
      }
    } catch (error) {
      // Ignore token verification failures and proceed with sending a new code.
    }
  }

  const whitelisted = await isEmailWhitelisted(email)
  if (!whitelisted) {
    return NextResponse.json({ error: "This email is not authorized for temporary access" }, { status: 403 })
  }

  const code = generateLoginCode()
  const expiresAt = new Date(Date.now() + config.codeExpiryMinutes * 60 * 1000)
  await storeLoginCode(email, code, expiresAt)
  await sendLoginCodeEmail({ recipient: email, code })

  return NextResponse.json({ success: true })
}
