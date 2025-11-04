import { type NextRequest, NextResponse } from "next/server"
import Stripe from "stripe"
import { createClient } from "@/lib/supabase/server"

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!)

export async function POST(req: NextRequest) {
  try {
    const { userId, email } = await req.json()

    // Get or create Stripe customer
    let customerId = null

    const supabase = await createClient()
    const { data: subscription } = await supabase
      .from("subscriptions")
      .select("stripe_customer_id")
      .eq("user_id", userId)
      .single()

    if (subscription?.stripe_customer_id && !subscription.stripe_customer_id.startsWith("temp_")) {
      customerId = subscription.stripe_customer_id
    } else {
      const customer = await stripe.customers.create({
        email,
        metadata: { userId },
      })
      customerId = customer.id

      // Update Supabase with Stripe customer ID
      await supabase.from("subscriptions").update({ stripe_customer_id: customerId }).eq("user_id", userId)
    }

    // Create checkout session
    const session = await stripe.checkout.sessions.create({
      customer: customerId,
      payment_method_types: ["card"],
      line_items: [
        {
          price_data: {
            currency: "gbp",
            product_data: {
              name: "findmyflavour Premium",
              description: "Unlock unlimited recipe discovery and features",
            },
            unit_amount: 300, // £3.00
            recurring: {
              interval: "month",
              interval_count: 1,
            },
          },
          quantity: 1,
        },
      ],
      mode: "subscription",
      success_url: `${process.env.NEXT_PUBLIC_DEV_SUPABASE_REDIRECT_URL || new URL(req.url).origin}/account?subscription=success`,
      cancel_url: `${process.env.NEXT_PUBLIC_DEV_SUPABASE_REDIRECT_URL || new URL(req.url).origin}/pricing?subscription=cancelled`,
    })

    return NextResponse.json({ url: session.url })
  } catch (error) {
    console.error("Stripe error:", error)
    return NextResponse.json({ error: "Failed to create checkout session" }, { status: 500 })
  }
}
