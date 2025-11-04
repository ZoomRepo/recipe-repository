"use client"

import type React from "react"

import { useState, useEffect } from "react"
import Link from "next/link"
import { Button } from "@/components/ui/button"

interface SubscriptionGateProps {
  recipeId: number
  recipeName: string
  children: React.ReactNode
}

export default function SubscriptionGate({ recipeId, recipeName, children }: SubscriptionGateProps) {
  const [recipeViews, setRecipeViews] = useState<number>(0)
  const [isSubscribed, setIsSubscribed] = useState(false)
  const [showGate, setShowGate] = useState(false)

  useEffect(() => {
    const subscriptionStatus = localStorage.getItem("subscriptionStatus")
    setIsSubscribed(subscriptionStatus === "active")

    const viewsKey = `recipe_views_${recipeId}`
    const currentViews = Number.parseInt(localStorage.getItem(viewsKey) || "0")
    const newViews = currentViews + 1
    localStorage.setItem(viewsKey, String(newViews))
    setRecipeViews(newViews)

    if (newViews > 2 && !isSubscribed) {
      setShowGate(true)
    }
  }, [recipeId, isSubscribed])

  if (showGate && !isSubscribed) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center relative">
        {/* Blurred background content */}
        <div className="absolute inset-0 opacity-50 blur-md pointer-events-none">{children}</div>

        {/* Gate overlay */}
        <div className="relative z-10 max-w-md mx-auto text-center space-y-6 bg-card border border-border rounded-lg p-8 shadow-lg">
          <h2 className="text-2xl font-bold text-foreground">Unlock Full Recipes</h2>
          <p className="text-muted-foreground">
            You've viewed {recipeViews} recipes for free. Subscribe to unlock unlimited access to all recipes and
            exclusive features.
          </p>

          <div className="bg-secondary rounded-lg p-4 space-y-2">
            <div className="flex items-center gap-2 text-sm">
              <svg className="w-5 h-5 text-primary" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                  clipRule="evenodd"
                />
              </svg>
              <span className="text-foreground">Unlimited recipe access</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <svg className="w-5 h-5 text-primary" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                  clipRule="evenodd"
                />
              </svg>
              <span className="text-foreground">Save favorites</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <svg className="w-5 h-5 text-primary" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                  clipRule="evenodd"
                />
              </svg>
              <span className="text-foreground">Ad-free experience</span>
            </div>
          </div>

          <div className="space-y-2">
            <Link href="/pricing" className="block">
              <Button className="w-full bg-primary hover:bg-primary/90 text-primary-foreground">
                Subscribe for £3/month
              </Button>
            </Link>
            <Link href="/auth/sign-up" className="block">
              <Button variant="outline" className="w-full bg-transparent">
                Create Account
              </Button>
            </Link>
          </div>

          <p className="text-xs text-muted-foreground">
            Already have an account?{" "}
            <Link href="/auth/login" className="text-primary hover:underline">
              Login
            </Link>
          </p>
        </div>
      </div>
    )
  }

  return <>{children}</>
}
