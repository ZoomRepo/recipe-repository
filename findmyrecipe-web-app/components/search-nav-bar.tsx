"use client"

import { useRouter } from "next/navigation"
import { Input } from "@/components/ui/input"
import Link from "next/link"
import type React from "react"

interface SearchNavBarProps {
  searchQuery: string
  setSearchQuery: (query: string) => void
}

export default function SearchNavBar({ searchQuery, setSearchQuery }: SearchNavBarProps) {
  const router = useRouter()
  const user = null

  const handleSearchChange = (value: string) => {
    setSearchQuery(value)
    if (value.trim()) {
      router.push(`/results?q=${encodeURIComponent(value)}`)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      if (searchQuery.trim()) {
        router.push(`/results?q=${encodeURIComponent(searchQuery)}`)
      }
    }
  }

  return (
    <nav className="sticky top-0 z-50 bg-background border-b border-border">
      <div className="max-w-7xl mx-auto px-4 py-4 flex items-center gap-4">
        {/* Logo */}
        <Link href="/" className="text-2xl font-bold text-foreground font-sans whitespace-nowrap">
          find<span className="text-primary">my</span>flavour
        </Link>

        {/* Search bar */}
        <div className="flex-1 flex gap-2">
          <div className="flex-1 relative max-w-md">
            <svg
              className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            <Input
              type="text"
              placeholder="Search recipes..."
              value={searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
              onKeyPress={handleKeyPress}
              className="pl-9 py-2 text-sm border border-border rounded-full bg-white text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-primary focus:border-transparent"
            />
          </div>
        </div>

        {/* Auth/User actions */}
        <div className="flex items-center gap-3">
          {user ? (
            <Link href="/account" className="text-sm font-medium text-foreground hover:text-primary transition-colors">
              Account
            </Link>
          ) : (
            <>
              <Link
                href="/auth/login"
                className="text-sm font-medium text-foreground hover:text-primary transition-colors"
              >
                Login
              </Link>
              <Link
                href="/auth/sign-up"
                className="text-sm font-medium text-foreground hover:text-primary transition-colors"
              >
                Sign up
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  )
}
