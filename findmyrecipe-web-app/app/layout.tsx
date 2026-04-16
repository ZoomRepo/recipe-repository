import type React from "react"
import type { Metadata } from "next"

import "./globals.css"

export const metadata: Metadata = {
  title: "findmyflavour - Recipe Search Engine",
  description: "Discover delicious recipes tailored to your taste with findmyflavour",
  generator: "v0.app",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <meta name="apple-mobile-web-app-title" content="Find My Flavour" />
      <body className={`font-sans antialiased`}>{children}</body>
    </html>
  )
}
