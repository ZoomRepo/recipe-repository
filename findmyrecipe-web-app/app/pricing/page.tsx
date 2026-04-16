"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Check } from "lucide-react"

export default function PricingPage() {
  const [isLoading, setIsLoading] = useState(false)

  const handleSubscribe = async () => {
    setIsLoading(true)
    window.setTimeout(() => setIsLoading(false), 500)
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
                {isLoading ? "Loading..." : "Premium coming soon"}
              </Button>
              <p className="text-sm text-muted-foreground">
                Authentication has been removed from the app, so paid subscriptions are temporarily unavailable.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
