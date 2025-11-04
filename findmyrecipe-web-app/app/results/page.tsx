"use client"

import { useState, useEffect, useCallback } from "react"
import { useSearchParams, useRouter } from "next/navigation"
import SearchNavBar from "@/components/search-nav-bar"
import RecipeResultsPage from "@/components/recipe-results-page"

export default function ResultsPage() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedFilters, setSelectedFilters] = useState({
    cookTime: "",
    servings: "",
    difficulty: "",
    cuisine: "",
  })

  useEffect(() => {
    const q = searchParams.get("q")
    if (q) {
      setSearchQuery(decodeURIComponent(q))
    }
  }, [searchParams])

  const handleFilterChange = useCallback(
    (newFilters: typeof selectedFilters) => {
      setSelectedFilters(newFilters)

      const params = new URLSearchParams()
      if (searchQuery) params.set("q", searchQuery)
      if (newFilters.cookTime) params.set("cookTime", newFilters.cookTime)
      if (newFilters.servings) params.set("servings", newFilters.servings)
      if (newFilters.difficulty) params.set("difficulty", newFilters.difficulty)
      if (newFilters.cuisine) params.set("cuisine", newFilters.cuisine)

      const queryString = params.toString()
      router.push(queryString ? `/results?${queryString}` : "/results")
    },
    [searchQuery, router],
  )

  return (
    <main className="min-h-screen bg-background">
      <SearchNavBar searchQuery={searchQuery} setSearchQuery={setSearchQuery} />
      <RecipeResultsPage searchQuery={searchQuery} filters={selectedFilters} onFilterChange={handleFilterChange} />
    </main>
  )
}
