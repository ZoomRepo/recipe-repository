"use client"

import { useState, useEffect, useCallback } from "react"
import { useSearchParams, useRouter } from "next/navigation"
import SearchNavBar from "@/components/search-nav-bar"
import RecipeResultsPage, {
  type FiltersState,
  type RecipesResponse,
} from "@/components/recipe-results-page"

export default function ResultsPage() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedFilters, setSelectedFilters] = useState<FiltersState>({
    cuisine: "",
    meal: "",
    diet: "",
  })
  const [page, setPage] = useState(1)
  const [data, setData] = useState<RecipesResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const q = searchParams.get("q")
    setSearchQuery(q ?? "")

    setSelectedFilters({
      cuisine: searchParams.get("cuisine") ?? "",
      meal: searchParams.get("meal") ?? "",
      diet: searchParams.get("diet") ?? "",
    })

    const rawPage = searchParams.get("page")
    const parsedPage = rawPage ? Number.parseInt(rawPage, 10) : 1
    setPage(Number.isNaN(parsedPage) || parsedPage < 1 ? 1 : parsedPage)
  }, [searchParams])

  useEffect(() => {
    const controller = new AbortController()
    const params = new URLSearchParams()
    const trimmedQuery = searchQuery.trim()
    if (trimmedQuery) {
      params.set("q", trimmedQuery)
    }
    if (selectedFilters.cuisine) {
      params.append("cuisine", selectedFilters.cuisine)
    }
    if (selectedFilters.meal) {
      params.append("meal", selectedFilters.meal)
    }
    if (selectedFilters.diet) {
      params.append("diet", selectedFilters.diet)
    }
    if (page > 1) {
      params.set("page", page.toString())
    }

    const queryString = params.toString()
    const url = `/api/v1/recipes${queryString ? `?${queryString}` : ""}`

    setIsLoading(true)
    setError(null)

    fetch(url, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) {
          const payload = await response.json().catch(() => ({}))
          const message = typeof payload.error === "string" ? payload.error : `Request failed with status ${response.status}`
          throw new Error(message)
        }
        return response.json() as Promise<RecipesResponse>
      })
      .then((json) => {
        setData(json)
        setIsLoading(false)
      })
      .catch((fetchError: unknown) => {
        if ((fetchError as Error).name === "AbortError") {
          return
        }
        setIsLoading(false)
        setError(fetchError instanceof Error ? fetchError.message : "Unable to load recipes")
      })

    return () => {
      controller.abort()
    }
  }, [searchQuery, selectedFilters.cuisine, selectedFilters.meal, selectedFilters.diet, page])

  const handleFilterChange = useCallback(
    (newFilters: FiltersState) => {
      setSelectedFilters(newFilters)
      setPage(1)

      const params = new URLSearchParams()
      const trimmedQuery = searchQuery.trim()
      if (trimmedQuery) {
        params.set("q", trimmedQuery)
      }
      if (newFilters.cuisine) {
        params.append("cuisine", newFilters.cuisine)
      }
      if (newFilters.meal) {
        params.append("meal", newFilters.meal)
      }
      if (newFilters.diet) {
        params.append("diet", newFilters.diet)
      }
      params.set("page", "1")

      const queryString = params.toString()
      router.push(queryString ? `/results?${queryString}` : "/results")
    },
    [router, searchQuery],
  )

  const handlePageChange = useCallback(
    (nextPage: number) => {
      setPage(nextPage)

      const params = new URLSearchParams()
      const trimmedQuery = searchQuery.trim()
      if (trimmedQuery) {
        params.set("q", trimmedQuery)
      }
      if (selectedFilters.cuisine) {
        params.append("cuisine", selectedFilters.cuisine)
      }
      if (selectedFilters.meal) {
        params.append("meal", selectedFilters.meal)
      }
      if (selectedFilters.diet) {
        params.append("diet", selectedFilters.diet)
      }
      if (nextPage > 1) {
        params.set("page", nextPage.toString())
      }

      const queryString = params.toString()
      router.push(queryString ? `/results?${queryString}` : "/results")
    },
    [router, searchQuery, selectedFilters],
  )

  return (
    <main className="min-h-screen bg-background">
      <SearchNavBar searchQuery={searchQuery} setSearchQuery={setSearchQuery} />
      <RecipeResultsPage
        searchQuery={searchQuery}
        filters={selectedFilters}
        onFilterChange={handleFilterChange}
        data={data}
        isLoading={isLoading}
        error={error}
        onPageChange={handlePageChange}
      />
    </main>
  )
}
