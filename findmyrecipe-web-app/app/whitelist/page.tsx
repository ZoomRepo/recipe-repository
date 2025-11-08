"use client"

import { useEffect, useState } from "react"
import Link from "next/link"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

const gateEnabled =
  typeof process !== "undefined" && process.env.NEXT_PUBLIC_TEMP_LOGIN_ENABLED
    ? process.env.NEXT_PUBLIC_TEMP_LOGIN_ENABLED === "true" ||
      process.env.NEXT_PUBLIC_TEMP_LOGIN_ENABLED === "1"
    : true

type FetchState = "idle" | "loading" | "error"

type EmailEntry = {
  email: string
}

export default function WhitelistPage() {
  const [emails, setEmails] = useState<EmailEntry[]>([])
  const [fetchState, setFetchState] = useState<FetchState>("idle")
  const [formEmail, setFormEmail] = useState("")
  const [formError, setFormError] = useState<string | null>(null)
  const [formState, setFormState] = useState<FetchState>("idle")

  useEffect(() => {
    const loadEmails = async () => {
      setFetchState("loading")
      try {
        const response = await fetch("/api/whitelist", { cache: "no-store" })
        if (!response.ok) {
          throw new Error("Failed to load whitelist")
        }
        const data = await response.json()
        const list: string[] = Array.isArray(data?.emails) ? data.emails : []
        setEmails(list.map((email) => ({ email })))
        setFetchState("idle")
      } catch (error) {
        setFetchState("error")
      }
    }

    loadEmails()
  }, [])

  const handleAddEmail = async (event: React.FormEvent) => {
    event.preventDefault()
    if (formState === "loading") {
      return
    }

    setFormError(null)

    if (!gateEnabled) {
      setFormError("Temporary login is currently disabled.")
      return
    }

    setFormState("loading")

    try {
      const normalizedEmail = formEmail.trim().toLowerCase()
      const response = await fetch("/api/whitelist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: normalizedEmail }),
      })

      if (!response.ok) {
        const data = await response.json().catch(() => null)
        throw new Error(data?.error || "Unable to add email")
      }

      setFormEmail("")
      setEmails((prev) => {
        const existing = prev.find((entry) => entry.email === normalizedEmail)
        if (existing) {
          return prev
        }
        return [{ email: normalizedEmail }, ...prev]
      })
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "Unable to add email")
    } finally {
      setFormState("idle")
    }
  }

  const handleRemoveEmail = async (email: string) => {
    if (formState === "loading") {
      return
    }

    if (!gateEnabled) {
      setFormError("Temporary login is currently disabled.")
      return
    }

    setFormState("loading")
    setFormError(null)

    try {
      const response = await fetch("/api/whitelist", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      })

      if (!response.ok) {
        const data = await response.json().catch(() => null)
        throw new Error(data?.error || "Unable to remove email")
      }

      setEmails((prev) => prev.filter((entry) => entry.email !== email))
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "Unable to remove email")
    } finally {
      setFormState("idle")
    }
  }

  return (
    <main className="min-h-screen bg-background px-4 py-12">
      <div className="max-w-3xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Whitelist management</h1>
            <p className="text-muted-foreground mt-1">
              Control who can receive temporary login codes while the gate is enabled.
            </p>
          </div>
          <Link href="/" className="hidden sm:inline-flex">
            <Button variant="outline">Back home</Button>
          </Link>
        </div>

        {!gateEnabled && (
          <Card className="border-destructive/50">
            <CardHeader>
              <CardTitle>Temporary login disabled</CardTitle>
              <CardDescription>
                Turn on the temporary login flag to send codes and manage the whitelist.
              </CardDescription>
            </CardHeader>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Add an email</CardTitle>
            <CardDescription>Approved users must request their temporary code from this address.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleAddEmail} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email address</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="team@company.com"
                  value={formEmail}
                  onChange={(event) => setFormEmail(event.target.value)}
                  required
                  disabled={formState === "loading"}
                />
              </div>
              {formError && <p className="text-sm text-destructive">{formError}</p>}
              <Button type="submit" disabled={formState === "loading"}>
                {formState === "loading" ? "Saving..." : "Add to whitelist"}
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Approved email addresses</CardTitle>
            <CardDescription>
              These contacts can request a temporary login code when the gate is active.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {fetchState === "loading" ? (
              <p className="text-muted-foreground">Loading whitelist…</p>
            ) : fetchState === "error" ? (
              <p className="text-destructive">We couldn't load the whitelist. Please refresh and try again.</p>
            ) : emails.length === 0 ? (
              <p className="text-muted-foreground">No emails have been added yet.</p>
            ) : (
              <ul className="space-y-3">
                {emails.map((entry) => (
                  <li
                    key={entry.email}
                    className="flex items-center justify-between rounded-lg border border-border px-4 py-3"
                  >
                    <span className="text-foreground">{entry.email}</span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="text-destructive hover:text-destructive"
                      disabled={formState === "loading"}
                      onClick={() => handleRemoveEmail(entry.email)}
                    >
                      Remove
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Link href="/" className="sm:hidden block">
          <Button variant="outline" className="w-full">
            Back home
          </Button>
        </Link>
      </div>
    </main>
  )
}
