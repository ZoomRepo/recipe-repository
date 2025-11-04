"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { createClient } from "@/lib/supabase/client"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { LogOut, Trash2, CreditCard, AlertTriangle } from "lucide-react"
import Link from "next/link"

interface Subscription {
  id: string
  plan_type: string
  status: string
  current_period_end: string
  stripe_subscription_id: string
}

export default function AccountPage() {
  const [user, setUser] = useState<any>(null)
  const [subscription, setSubscription] = useState<Subscription | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [actionMessage, setActionMessage] = useState<{ type: string; text: string } | null>(null)
  const router = useRouter()

  useEffect(() => {
    const loadAccountData = async () => {
      const supabase = createClient()
      const {
        data: { user },
      } = await supabase.auth.getUser()

      if (!user) {
        router.push("/auth/login")
        return
      }

      setUser(user)

      const { data: subData } = await supabase.from("subscriptions").select("*").eq("user_id", user.id).single()

      if (subData) {
        setSubscription(subData)
      }
      setIsLoading(false)
    }

    loadAccountData()
  }, [router])

  const handleLogout = async () => {
    const supabase = createClient()
    await supabase.auth.signOut()
    router.push("/")
  }

  const handleManageBilling = async () => {
    setIsLoading(true)
    try {
      const response = await fetch("/api/stripe/portal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userId: user.id }),
      })
      const { url } = await response.json()
      if (url) window.open(url, "_blank")
    } catch (error) {
      console.error("Error:", error)
      setActionMessage({ type: "error", text: "Failed to open billing portal" })
    } finally {
      setIsLoading(false)
    }
  }

  const handleDeleteAccount = async () => {
    setIsLoading(true)
    try {
      // Delete from Supabase first
      const supabase = createClient()

      // Cancel subscription if active
      if (subscription?.stripe_subscription_id && subscription.status === "active") {
        await fetch("/api/stripe/cancel-subscription", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ subscriptionId: subscription.stripe_subscription_id }),
        })
      }

      // Delete auth user (this cascades to profiles and subscriptions)
      await supabase.auth.admin.deleteUser(user.id)

      // Sign out and redirect
      await supabase.auth.signOut()
      router.push("/")
    } catch (error) {
      console.error("Error:", error)
      setActionMessage({ type: "error", text: "Failed to delete account" })
      setIsLoading(false)
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">Loading...</div>
      </div>
    )
  }

  if (!user) {
    return null
  }

  const renewalDate = subscription?.current_period_end
    ? new Date(subscription.current_period_end).toLocaleDateString()
    : null

  return (
    <div className="min-h-screen bg-background py-8 px-4">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <div className="space-y-2">
          <h1 className="text-3xl font-bold text-foreground">Account Settings</h1>
          <p className="text-muted-foreground">Manage your findmyflavour account</p>
        </div>

        {actionMessage && (
          <Alert variant={actionMessage.type === "error" ? "destructive" : "default"}>
            <AlertDescription>{actionMessage.text}</AlertDescription>
          </Alert>
        )}

        {/* Account Info */}
        <Card>
          <CardHeader>
            <CardTitle>Account Information</CardTitle>
            <CardDescription>Your profile details</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between items-center py-2 border-b border-border">
              <span className="text-muted-foreground">Email</span>
              <span className="font-medium">{user.email}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-border">
              <span className="text-muted-foreground">Member Since</span>
              <span className="font-medium">{new Date(user.created_at).toLocaleDateString()}</span>
            </div>
          </CardContent>
        </Card>

        {/* Subscription Info */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="w-5 h-5" />
              Subscription
            </CardTitle>
            <CardDescription>Manage your subscription and billing</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between items-center py-2 border-b border-border">
              <span className="text-muted-foreground">Plan</span>
              <span className="font-medium capitalize">
                {subscription?.plan_type === "premium" ? "Premium (£3/month)" : "Free"}
              </span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-border">
              <span className="text-muted-foreground">Status</span>
              <span
                className={`font-medium capitalize ${
                  subscription?.status === "active" ? "text-green-500" : "text-muted-foreground"
                }`}
              >
                {subscription?.status || "inactive"}
              </span>
            </div>
            {subscription?.plan_type === "premium" && renewalDate && (
              <div className="flex justify-between items-center py-2">
                <span className="text-muted-foreground">Next Renewal</span>
                <span className="font-medium">{renewalDate}</span>
              </div>
            )}

            <div className="space-y-2 pt-4">
              {subscription?.plan_type === "free" ? (
                <Link href="/pricing">
                  <Button className="w-full">Upgrade to Premium</Button>
                </Link>
              ) : (
                <Button
                  variant="outline"
                  onClick={handleManageBilling}
                  disabled={isLoading}
                  className="w-full bg-transparent"
                >
                  Manage Billing
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Danger Zone */}
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="text-destructive flex items-center gap-2">
              <AlertTriangle className="w-5 h-5" />
              Danger Zone
            </CardTitle>
            <CardDescription>Irreversible actions</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Button variant="outline" onClick={handleLogout} className="w-full bg-transparent" disabled={isLoading}>
                <LogOut className="w-4 h-4 mr-2" />
                Logout
              </Button>
            </div>

            {showDeleteConfirm ? (
              <div className="space-y-2 p-4 bg-destructive/10 rounded-lg">
                <p className="text-sm font-medium">
                  This will permanently delete your account and all associated data. This cannot be undone.
                </p>
                <div className="flex gap-2">
                  <Button variant="destructive" onClick={handleDeleteAccount} disabled={isLoading} className="flex-1">
                    {isLoading ? "Deleting..." : "Delete Permanently"}
                  </Button>
                  <Button variant="outline" onClick={() => setShowDeleteConfirm(false)} className="flex-1">
                    Cancel
                  </Button>
                </div>
              </div>
            ) : (
              <Button variant="destructive" onClick={() => setShowDeleteConfirm(true)} className="w-full">
                <Trash2 className="w-4 h-4 mr-2" />
                Delete Account
              </Button>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
