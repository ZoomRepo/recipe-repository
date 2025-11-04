import { NextRequest, NextResponse } from "next/server"
import bcrypt from "bcryptjs"
import { z } from "zod"

import { createUser, findUserByEmail } from "@/lib/users-repository"

const signUpSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8, "Password must be at least 8 characters"),
})

export async function POST(request: NextRequest) {
  let payload: unknown
  try {
    payload = await request.json()
  } catch {
    return NextResponse.json({ error: "Invalid JSON payload" }, { status: 400 })
  }

  const parsed = signUpSchema.safeParse(payload)
  if (!parsed.success) {
    const issues = parsed.error.issues.map((issue) => issue.message)
    return NextResponse.json({ error: "Invalid data", details: issues }, { status: 400 })
  }

  const { email, password } = parsed.data

  const existingUser = await findUserByEmail(email)
  if (existingUser) {
    return NextResponse.json({ error: "An account with this email already exists" }, { status: 409 })
  }

  try {
    const passwordHash = await bcrypt.hash(password, 12)
    const user = await createUser({ email, passwordHash })

    return NextResponse.json({
      user: {
        id: user.id,
        email: user.email,
        createdAt: user.createdAt,
      },
    })
  } catch (error) {
    console.error("Failed to sign up user", error)
    return NextResponse.json({ error: "Unable to create account" }, { status: 500 })
  }
}
