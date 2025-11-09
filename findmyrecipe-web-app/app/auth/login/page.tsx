// app/auth/login/page.tsx
"use client"

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react"
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

const LOCAL_SESSION_KEY = "findmyrecipe.loginSession"
const FINALIZE_SESSION_FALLBACK_ERROR =
  "We couldn't start your session automatically. Please request a new code."

function clearStoredSession() {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(LOCAL_SESSION_KEY)
  }
}

export default function LoginPage() {
  // ⬇️ Wrap the component that uses useSearchParams() in Suspense
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center">Loading…</div>}>
      <LoginPageInner />
    </Suspense>
  )
}

// Everything below is your original logic, moved into an inner component
function LoginPageInner() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [email, setEmail] = useState("")
  const [code, setCode] = useState("")
  const [step, setStep] = useState<"email" | "code">("email")
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isCheckingSession, setIsCheckingSession] = useState(gateEnabled)
  const hasCheckedSessionRef = useRef(false)

  const redirectParam = searchParams?.get("redirect") || "/"
  const redirectPath = useMemo(() => {
    const candidate = redirectParam.startsWith("/") ? redirectParam : "/"
    return candidate.startsWith("/auth/session") ? "/" : candidate
  }, [redirectParam])
  const redirectError = searchParams?.get("error")

  const redirectToApp = useCallback(
    (statusMessage = "Redirecting you now...") => {
      setError(null)
      setMessage(statusMessage)
      setTimeout(() => {
        if (typeof window !== "undefined") {
          window.location.replace(redirectPath)
        } else {
          router.replace(redirectPath)
          router.refresh()
        }
      }, 300)
    },
    [redirectPath, router]
  )

  const finalizeSessionCode = useCallback(async (sessionCode: string) => {
    if (!sessionCode) {
      clearStoredSession()
      return { ok: false as const, error: FINALIZE_SESSION_FALLBACK_ERROR }
    }

    try {
      const response = await fetch("/api/auth/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ code: sessionCode }),
      })

      const data = await response.json().catch(() => null)

      if (response.ok && data?.authenticated) {
        clearStoredSession()
        return { ok: true as const }
      }

      if (response.status === 401) {
        try {
          const fallback = await fetch("/api/auth/session", {
            method: "GET",
            credentials: "include",
            cache: "no-store",
          })

          if (fallback.ok) {
            const fallbackData: { authenticated?: boolean } = await fallback
              .json()
              .catch(() => ({}))
            if (fallbackData?.authenticated) {
              clearStoredSession()
              return { ok: true as const }
            }
          }
        } catch {
          // ignore and allow normal error handling below
        }
      }

      clearStoredSession()
      const apiError =
        typeof data?.error === "string" ? data.error : FINALIZE_SESSION_FALLBACK_ERROR

      return { ok: false as const, error: apiError }
    } catch {
      return {
        ok: false as const,
        error: "We couldn't start your session automatically. Please try again.",
      }
    }
  }, [])

  const restoreSessionFromStorage = useCallback(async () => {
    if (typeof window === "undefined") return { restored: false as const }

    const raw = window.localStorage.getItem(LOCAL_SESSION_KEY)
    if (!raw) return { restored: false as const }

    let stored: { email?: string; code?: string } | null = null
    try {
      stored = JSON.parse(raw)
    } catch {
      clearStoredSession()
      return { restored: false as const }
    }

    if (!stored?.code) {
      clearStoredSession()
      return { restored: false as const }
    }

    const result = await finalizeSessionCode(stored.code)
    if (result.ok) {
      return { restored: true as const }
    }

    return {
      restored: false as const,
      error:
        result.error ||
        "We couldn't restore your access automatically. Please request a new code.",
    }
  }, [finalizeSessionCode])

  useEffect(() => {
    setError(null)
    setMessage(null)
  }, [step])

  useEffect(() => {
    if (hasCheckedSessionRef.current) {
      return
    }

    hasCheckedSessionRef.current = true
    if (!gateEnabled) {
      setIsCheckingSession(false)
      return
    }

    let cancelled = false
    const checkSession = async () => {
      setIsCheckingSession(true)
      try {
        const response = await fetch("/api/auth/session", {
          method: "GET",
          credentials: "include",
          cache: "no-store",
        })

        if (!cancelled && response.ok) {
          const data: { authenticated?: boolean } = await response.json()
          if (data?.authenticated) {
            redirectToApp("You're already signed in. Redirecting...")
            return
          }
        }

        if (!cancelled) {
          const restored = await restoreSessionFromStorage()
          if (restored.restored) {
            redirectToApp("Welcome back! Redirecting you now...")
            return
          }
          if (restored.error) {
            setError(restored.error)
          }
          setMessage(null)
        }
      } catch {
        // ignore errors and allow normal flow
      } finally {
        if (!cancelled) setIsCheckingSession(false)
      }
    }

    checkSession()
    return () => {
      cancelled = true
      hasCheckedSessionRef.current = false
    }
  }, [restoreSessionFromStorage, redirectToApp])

  const handleRequestCode = async (event: React.FormEvent) => {
    event.preventDefault()
    if (isCheckingSession) return
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
        credentials: "include",
        body: JSON.stringify({ email }),
      })

      if (!response.ok) {
        const data = await response.json().catch(() => null)
        throw new Error(data?.error || "Unable to send login code")
      }

      const data = await response.json().catch(() => null)
      if (data?.alreadyVerified) {
        setMessage("You're already verified on this device. Restoring your access...")
        setIsCheckingSession(true)
        const restored = await restoreSessionFromStorage()
        if (restored.restored) {
          setIsCheckingSession(false)
          redirectToApp("Welcome back! Redirecting you now...")
          return
        }

        setIsCheckingSession(false)
        setMessage(null)
        setError(
          restored.error ||
            "We couldn't restore your access automatically. Please try again or contact support."
        )
        return
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
    if (isCheckingSession) return
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
        credentials: "include",
        body: JSON.stringify({ email, code }),
      })

      if (!response.ok) {
        const data = await response.json().catch(() => null)
        throw new Error(data?.error || "Invalid or expired code")
      }

      const data: { sessionCode?: string; expiresAt?: string } = await response.json().catch(() => ({}))

      if (typeof window !== "undefined" && data?.sessionCode) {
        window.localStorage.setItem(
          LOCAL_SESSION_KEY,
          JSON.stringify({ email, code: data.sessionCode })
        )
      }

      if (data?.sessionCode) {
        setIsCheckingSession(true)
        const result = await finalizeSessionCode(data.sessionCode)
        setIsCheckingSession(false)

        if (result.ok) {
          redirectToApp("Success! Redirecting you now...")
          return
        }

        setMessage(null)
        setError(result.error || FINALIZE_SESSION_FALLBACK_ERROR)
        return
      }

      setError(FINALIZE_SESSION_FALLBACK_ERROR)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid or expired code")
    } finally {
      setIsSubmitting(false)
    }
  }

  useEffect(() => {
    if (!redirectError) {
      return
    }

    setError(
      redirectError === "session"
        ? "We couldn't restore your access automatically. Please request a new code."
        : "We couldn't restore your access. Please try again."
    )

    if (typeof window !== "undefined") {
      window.localStorage.removeItem(LOCAL_SESSION_KEY)
    }
  }, [redirectError])

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
                : "Check your inbox for the 6-digit code we just sent."}
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
                <Button type="submit" className="w-full" disabled={isSubmitting || isCheckingSession}>
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
                  <Button type="submit" className="w-full" disabled={isSubmitting || isCheckingSession}>
                    {isSubmitting ? "Verifying..." : "Verify and continue"}
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    className="w-full"
                    disabled={isSubmitting || isCheckingSession}
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
              Need to manage access?{" "}
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
