"use client"

import * as React from "react"
import { OTPInput, OTPInputContext } from "input-otp"

import { cn } from "@/lib/utils"

const InputOTP = React.forwardRef<React.ElementRef<typeof OTPInput>, React.ComponentPropsWithoutRef<typeof OTPInput>>(
  ({ className, containerClassName, ...props }, ref) => (
    <OTPInput
      ref={ref}
      containerClassName={cn("flex items-center gap-2", containerClassName)}
      className={cn("flex gap-2", className)}
      {...props}
    />
  )
)
InputOTP.displayName = "InputOTP"

const InputOTPGroup = React.forwardRef<
  React.ElementRef<"div">,
  React.ComponentPropsWithoutRef<"div">
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("flex items-center gap-2", className)} {...props} />
))
InputOTPGroup.displayName = "InputOTPGroup"

const InputOTPSlot = React.forwardRef<
  HTMLDivElement,
  React.ComponentPropsWithoutRef<"div"> & { index: number }
>(({ index, className, ...props }, ref) => {
  const inputOTPContext = React.useContext(OTPInputContext)

  const slot = inputOTPContext.slots[index]
  const char = slot?.char ?? ""
  const isActive = slot?.isActive ?? false
  const hasFakeCaret = slot?.hasFakeCaret ?? false

  return (
    <div
      ref={ref}
      className={cn(
        "relative flex h-12 w-12 items-center justify-center rounded-lg border border-input bg-background text-lg font-medium transition-colors",
        "shadow-sm",
        isActive && "border-primary ring-2 ring-primary/20",
        className
      )}
      {...props}
    >
      {char}
      {hasFakeCaret && <FakeCaret />}
      <span className="sr-only">Digit {index + 1}</span>
    </div>
  )
})
InputOTPSlot.displayName = "InputOTPSlot"

const InputOTPSeparator = React.forwardRef<HTMLDivElement, React.ComponentPropsWithoutRef<"div">>(
  ({ className, ...props }, ref) => (
    <div ref={ref} role="separator" className={cn("w-2", className)} {...props} />
  )
)
InputOTPSeparator.displayName = "InputOTPSeparator"

function FakeCaret() {
  return <div className="pointer-events-none absolute inset-y-3 left-1/2 w-px -translate-x-1/2 bg-primary" />
}

export { InputOTP, InputOTPGroup, InputOTPSeparator, InputOTPSlot }
