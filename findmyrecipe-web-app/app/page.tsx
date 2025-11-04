"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import RecipeSearch from "@/components/recipe-search"

export default function Home() {
  const [searchQuery, setSearchQuery] = useState("")
  const router = useRouter()

  const handleSearch = () => {
    if (searchQuery.trim()) {
      router.push(`/results?q=${encodeURIComponent(searchQuery)}`)
    }
  }

  return (
    <main className="min-h-screen bg-background">
      <RecipeSearch searchQuery={searchQuery} setSearchQuery={setSearchQuery} onSearch={handleSearch} />
    </main>
  )
}
