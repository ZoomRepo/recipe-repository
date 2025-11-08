"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { InputOTP, InputOTPGroup, InputOTPSlot } from "@/components/ui/input-otp"

const gateEnabled =
  typeof process !== "undefined" && process.env.NEXT_PUBLIC_TEMP_LOGIN_ENABLED
    ? process.env.NEXT_PUBLIC_TEMP_LOGIN_ENABLED === "true" ||
      process.env.NEXT_PUBLIC_TEMP_LOGIN_ENABLED === "1"
    : true

export default function LoginPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [email, setEmail] = useState("")
  const [code, setCode] = useState("")
  const [step, setStep] = useState<"email" | "code">("email")
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    setError(null)
    setMessage(null)
  }, [step])

  const handleRequestCode = async (event: React.FormEvent) => {
    event.preventDefault()

    if (!gateEnabled) {
      setError("Temporary login is currently disabled.")
      return
    }

    setIsSubmitting(true)
    setError(null)
    setMessage(null)

    try {
      const response = await fetch("/api/auth/send-login-code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      })

      if (!response.ok) {
        const data = await response.json().catch(() => null)
        throw new Error(data?.error || "Unable to send login code")
      }

      setMessage("We've sent a 6-digit code to your email. Enter it below to continue.")
      setStep("code")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to send login code")
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleVerifyCode = async (event: React.FormEvent) => {
    event.preventDefault()

    if (!gateEnabled) {
      setError("Temporary login is currently disabled.")
      return
    }

    if (code.length !== 6) {
      setError("Please enter the full 6-digit code")
      return
    }

    setIsSubmitting(true)
    setError(null)

    try {
      const response = await fetch("/api/auth/verify-login-code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, code }),
      })

      if (!response.ok) {
        const data = await response.json().catch(() => null)
        throw new Error(data?.error || "Invalid or expired code")
      }

      setMessage("Success! Redirecting you now...")
      const redirectPath = searchParams?.get("redirect") || "/"
      setTimeout(() => {
        router.push(redirectPath)
        router.refresh()
      }, 500)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid or expired code")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold text-foreground">
            find<span className="text-primary">my</span>flavour
          </h1>
          <p className="text-muted-foreground">Secure temporary access</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>{step === "email" ? "Request access" : "Enter your code"}</CardTitle>
            <CardDescription>
              {step === "email"
                ? "Enter an approved email address to receive a login code."
                : "Check your inbox for the 6-digit code we just sent."
              }
            </CardDescription>
          </CardHeader>
          <CardContent>
            {step === "email" ? (
              <form onSubmit={handleRequestCode} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@example.com"
                    required
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                  />
                </div>
                {error && <p className="text-sm text-destructive">{error}</p>}
                {message && <p className="text-sm text-muted-foreground">{message}</p>}
                <Button type="submit" className="w-full" disabled={isSubmitting}>
                  {isSubmitting ? "Sending code..." : "Send login code"}
                </Button>
              </form>
            ) : (
              <form onSubmit={handleVerifyCode} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="code">6-digit code</Label>
                  <InputOTP
                    maxLength={6}
                    value={code}
                    onChange={(value) => setCode(value)}
                    containerClassName="justify-between"
                  >
                    <InputOTPGroup className="gap-2">
                      {Array.from({ length: 6 }).map((_, index) => (
                        <InputOTPSlot key={index} index={index} />
                      ))}
                    </InputOTPGroup>
                  </InputOTP>
                  <p className="text-xs text-muted-foreground">
                    We sent the code to <span className="font-medium text-foreground">{email}</span>
                  </p>
                </div>
                {error && <p className="text-sm text-destructive">{error}</p>}
                {message && <p className="text-sm text-muted-foreground">{message}</p>}
                <div className="space-y-2">
                  <Button type="submit" className="w-full" disabled={isSubmitting}>
                    {isSubmitting ? "Verifying..." : "Verify and continue"}
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    className="w-full"
                    disabled={isSubmitting}
                    onClick={() => {
                      setStep("email")
                      setCode("")
                    }}
                  >
                    Use a different email
                  </Button>
                </div>
              </form>
            )}
            <div className="mt-4 text-center text-sm text-muted-foreground">
              Need to manage access? {" "}
              <Link href="/whitelist" className="text-primary hover:underline">
                View whitelist
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
