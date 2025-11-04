"use client"

import { useState } from "react"
import type React from "react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import Link from "next/link"
import { useRouter } from "next/navigation"

interface RecipeSearchProps {
  searchQuery: string
  setSearchQuery: (query: string) => void
  onSearch: () => void
}

export default function RecipeSearch({ searchQuery, setSearchQuery, onSearch }: RecipeSearchProps) {
  const [isOpen, setIsOpen] = useState(false)
  const router = useRouter()
  const subscriptionStatus = typeof window !== "undefined" ? localStorage.getItem("subscriptionStatus") : null
  const user = subscriptionStatus === "active"

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      onSearch()
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-background px-4 py-12 relative">
      {/* Navigation bar */}
      <div className="absolute top-0 left-0 right-0 bg-background border-b border-border">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/" className="text-xl font-bold text-foreground">
            find<span className="text-primary">my</span>flavour
          </Link>

          <div className="flex items-center gap-4">
            {user ? (
              <>
                <div className="relative">
                  <button
                    onClick={() => setIsOpen(!isOpen)}
                    className="p-2 hover:bg-secondary rounded-lg transition-colors"
                  >
                    {isOpen ? (
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    ) : (
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M4 6h16M4 12h16M4 18h16"
                        />
                      </svg>
                    )}
                  </button>

                  {isOpen && (
                    <div className="absolute right-0 mt-2 w-56 bg-card border border-border rounded-lg shadow-lg z-50">
                      <div className="px-4 py-3 border-b border-border">
                        <p className="text-sm text-muted-foreground">Subscribed User</p>
                      </div>
                      <Link
                        href="/account"
                        className="block px-4 py-2 hover:bg-secondary text-foreground"
                        onClick={() => setIsOpen(false)}
                      >
                        Manage Subscription
                      </Link>
                      <Link
                        href="/account"
                        className="block px-4 py-2 hover:bg-secondary text-foreground"
                        onClick={() => setIsOpen(false)}
                      >
                        View Favorites
                      </Link>
                      <button
                        onClick={() => {
                          localStorage.removeItem("subscriptionStatus")
                          setIsOpen(false)
                          router.refresh()
                        }}
                        className="block w-full text-left px-4 py-2 hover:bg-secondary text-foreground rounded-b-lg"
                      >
                        Logout
                      </button>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="flex items-center gap-2">
                <Link href="/auth/login">
                  <Button variant="outline" size="sm">
                    Login
                  </Button>
                </Link>
                <Link href="/auth/sign-up">
                  <Button size="sm">Sign up</Button>
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="w-full max-w-2xl space-y-8 mt-20">
        <div className="text-center space-y-2">
          <h1 className="text-5xl font-bold text-foreground font-sans">
            find<span className="text-primary">my</span>flavour
          </h1>
          <p className="text-muted-foreground text-lg">Discover recipes that match your taste</p>
        </div>

        {/* ... existing search bar code ... */}
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <svg
              className="absolute left-4 top-1/2 transform -translate-y-1/2 text-muted-foreground w-5 h-5"
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
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              className="pl-12 py-6 text-lg border border-border rounded-full bg-white text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-primary focus:border-transparent"
            />
          </div>
          <Button
            onClick={onSearch}
            className="px-8 py-6 text-lg bg-primary hover:bg-primary/90 text-primary-foreground rounded-full font-medium transition-colors"
          >
            Search
          </Button>
        </div>

        {/* Suggestions */}
        <div className="text-center space-y-2">
          
          
        </div>
      </div>
    </div>
  )
}
