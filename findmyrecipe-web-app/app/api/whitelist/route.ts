import { NextResponse } from "next/server"
import { z } from "zod"

import { addEmailToWhitelist, listWhitelistedEmails, removeEmailFromWhitelist } from "@/lib/login-gate-repository"
import { resolveLoginGateConfig } from "@/lib/login-gate-config"

const addSchema = z.object({
  email: z.string().email(),
})

const removeSchema = z.object({
  email: z.string().email(),
})

export async function GET() {
  const emails = await listWhitelistedEmails()
  return NextResponse.json({ emails })
}

export async function POST(request: Request) {
  const config = resolveLoginGateConfig()
  if (!config.enabled) {
    return NextResponse.json({ error: "Temporary login is disabled" }, { status: 404 })
  }

  const body = await request.json().catch(() => null)
  if (!body) {
    return NextResponse.json({ error: "Invalid request" }, { status: 400 })
  }

  const parsed = addSchema.safeParse(body)
  if (!parsed.success) {
    return NextResponse.json({ error: "Please provide a valid email" }, { status: 400 })
  }

  await addEmailToWhitelist(parsed.data.email)
  return NextResponse.json({ success: true })
}

export async function DELETE(request: Request) {
  const config = resolveLoginGateConfig()
  if (!config.enabled) {
    return NextResponse.json({ error: "Temporary login is disabled" }, { status: 404 })
  }

  const body = await request.json().catch(() => null)
  if (!body) {
    return NextResponse.json({ error: "Invalid request" }, { status: 400 })
  }

  const parsed = removeSchema.safeParse(body)
  if (!parsed.success) {
    return NextResponse.json({ error: "Please provide a valid email" }, { status: 400 })
  }

  await removeEmailFromWhitelist(parsed.data.email)
  return NextResponse.json({ success: true })
}
