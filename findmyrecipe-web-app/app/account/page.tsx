"use client"

import Link from "next/link"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { CreditCard } from "lucide-react"

export default function AccountPage() {
  return (
    <div className="min-h-screen bg-background py-8 px-4">
      <div className="max-w-2xl mx-auto space-y-6">
        <div className="space-y-2">
          <h1 className="text-3xl font-bold text-foreground">Account</h1>
          <p className="text-muted-foreground">Account-based features have been removed from findmyflavour.</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="w-5 h-5" />
              Public access
            </CardTitle>
            <CardDescription>You can now browse the app without signing in.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-muted-foreground">
              There is no longer a login flow or account dashboard in this app. Recipe search is available directly
              from the home page.
            </p>
            <div className="pt-2">
              <Link href="/">
                <Button className="w-full">Go to recipe search</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
