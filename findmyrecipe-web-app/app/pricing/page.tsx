"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { createClient } from "@/lib/supabase/client"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Check } from "lucide-react"

export default function PricingPage() {
  const [isLoading, setIsLoading] = useState(false)
  const [user, setUser] = useState<any>(null)
  const router = useRouter()

  useEffect(() => {
    const checkUser = async () => {
      const supabase = createClient()
      const {
        data: { user },
      } = await supabase.auth.getUser()
      setUser(user)
    }
    checkUser()
  }, [])

  const handleSubscribe = async () => {
    if (!user) {
      router.push("/auth/sign-up")
      return
    }

    setIsLoading(true)
    try {
      const response = await fetch("/api/stripe/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userId: user.id, email: user.email }),
      })
      const { url } = await response.json()
      if (url) router.push(url)
    } catch (error) {
      console.error("Error:", error)
    } finally {
      setIsLoading(false)
    }
  }

  const features = [
    "Access all recipes",
    "Save favorites",
    "Personalized recommendations",
    "Recipe filtering",
    "Ad-free experience",
  ]

  return (
    <div className="min-h-screen bg-background py-12 px-4">
      <div className="max-w-4xl mx-auto space-y-12">
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold text-foreground">
            find<span className="text-primary">my</span>flavour Premium
          </h1>
          <p className="text-muted-foreground text-lg">Unlock unlimited recipe discovery</p>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          {/* Free Plan */}
          <Card>
            <CardHeader>
              <CardTitle>Free</CardTitle>
              <CardDescription>Perfect for exploring</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <span className="text-3xl font-bold">£0</span>
                <span className="text-muted-foreground">/month</span>
              </div>
              <ul className="space-y-3">
                <li className="flex items-center gap-2">
                  <Check className="w-5 h-5 text-primary" />
                  <span>Limited searches</span>
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-5 h-5 text-primary" />
                  <span>Basic search only</span>
                </li>
              </ul>
              <Button disabled className="w-full">
                Current Plan
              </Button>
            </CardContent>
          </Card>

          {/* Premium Plan */}
          <Card className="border-primary border-2 relative">
            <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
              <div className="bg-primary text-primary-foreground px-4 py-1 rounded-full text-sm font-medium">
                Popular
              </div>
            </div>
            <CardHeader>
              <CardTitle>Premium</CardTitle>
              <CardDescription>Full access to all features</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <span className="text-3xl font-bold">£3</span>
                <span className="text-muted-foreground">/month</span>
              </div>
              <ul className="space-y-3">
                {features.map((feature) => (
                  <li key={feature} className="flex items-center gap-2">
                    <Check className="w-5 h-5 text-primary" />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
              <Button onClick={handleSubscribe} disabled={isLoading} className="w-full">
                {isLoading ? "Loading..." : user ? "Subscribe Now" : "Sign up to Subscribe"}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
