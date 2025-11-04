import { type NextRequest, NextResponse } from "next/server"

export async function POST(req: NextRequest) {
  try {
    const { userId } = await req.json()
    const apiBaseUrl = process.env.FLASK_API_BASE_URL

    if (!apiBaseUrl) {
      return NextResponse.json({ error: "Billing service URL not configured" }, { status: 500 })
    }

    const origin = process.env.NEXT_PUBLIC_DEV_SUPABASE_REDIRECT_URL || new URL(req.url).origin
    const response = await fetch(`${apiBaseUrl}/api/v1/billing/portal`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        userId,
        returnUrl: `${origin}/account`,
      }),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: "Billing portal failed" }))
      return NextResponse.json(error, { status: response.status })
    }

    const data = await response.json()
    return NextResponse.json({ url: data.url })
  } catch (error) {
    console.error("Portal error:", error)
    return NextResponse.json({ error: "Failed to create portal session" }, { status: 500 })
  }
}
