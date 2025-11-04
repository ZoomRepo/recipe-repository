import { type NextRequest, NextResponse } from "next/server"

export async function POST(req: NextRequest) {
  const apiBaseUrl = process.env.FLASK_API_BASE_URL

  if (!apiBaseUrl) {
    return NextResponse.json({ error: "Billing service URL not configured" }, { status: 500 })
  }

  const body = await req.text()
  const signature = req.headers.get("stripe-signature") ?? ""
  const contentType = req.headers.get("content-type") ?? "application/json"

  const response = await fetch(`${apiBaseUrl}/api/v1/billing/webhook`, {
    method: "POST",
    headers: {
      "stripe-signature": signature,
      "content-type": contentType,
    },
    body,
  })

  const text = await response.text()
  return new NextResponse(text, {
    status: response.status,
    headers: { "content-type": response.headers.get("content-type") ?? "application/json" },
  })
}
