"use client"

import { useState, useEffect, useCallback } from "react"
import { useSearchParams, useRouter } from "next/navigation"
import type { ReadonlyURLSearchParams } from "next/navigation"
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
  const [ingredients, setIngredients] = useState<string[]>([])
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

    setIngredients(parseIngredientParams(searchParams))

    const rawPage = searchParams.get("page")
    const parsedPage = rawPage ? Number.parseInt(rawPage, 10) : 1
    setPage(Number.isNaN(parsedPage) || parsedPage < 1 ? 1 : parsedPage)
  }, [searchParams])

  useEffect(() => {
    const controller = new AbortController()
    const params = buildResultsSearchParams(searchQuery, selectedFilters, ingredients, page)
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
  }, [searchQuery, selectedFilters.cuisine, selectedFilters.meal, selectedFilters.diet, page, ingredients])

  const handleFilterChange = useCallback(
    (newFilters: FiltersState) => {
      setSelectedFilters(newFilters)
      setPage(1)

      const params = buildResultsSearchParams(searchQuery, newFilters, ingredients, 1)
      const queryString = params.toString()
      router.push(queryString ? `/results?${queryString}` : "/results")
    },
    [router, searchQuery, ingredients],
  )

  const handlePageChange = useCallback(
    (nextPage: number) => {
      setPage(nextPage)

      const params = buildResultsSearchParams(searchQuery, selectedFilters, ingredients, nextPage)
      const queryString = params.toString()
      router.push(queryString ? `/results?${queryString}` : "/results")
    },
    [router, searchQuery, selectedFilters, ingredients],
  )

  const handleSearchChange = useCallback((value: string) => {
    setSearchQuery(value)
  }, [])

  const handleSearchSubmit = useCallback(
    (value: string) => {
      setPage(1)
      const params = buildResultsSearchParams(value, selectedFilters, ingredients, 1)
      const queryString = params.toString()
      router.push(queryString ? `/results?${queryString}` : "/results")
    },
    [router, selectedFilters, ingredients],
  )

  const handleAddIngredient = useCallback(
    (value: string) => {
      const trimmed = value.trim()
      if (!trimmed) {
        return
      }
      if (ingredients.some((ingredient) => ingredient.toLowerCase() === trimmed.toLowerCase())) {
        return
      }
      const nextIngredients = [...ingredients, trimmed]
      setIngredients(nextIngredients)
      setPage(1)

      const params = buildResultsSearchParams(searchQuery, selectedFilters, nextIngredients, 1)
      const queryString = params.toString()
      router.push(queryString ? `/results?${queryString}` : "/results")
    },
    [ingredients, router, searchQuery, selectedFilters],
  )

  const handleRemoveIngredient = useCallback(
    (value: string) => {
      const normalized = value.trim().toLowerCase()
      const nextIngredients = ingredients.filter((ingredient) => ingredient.toLowerCase() !== normalized)
      if (nextIngredients.length === ingredients.length) {
        return
      }
      setIngredients(nextIngredients)
      setPage(1)

      const params = buildResultsSearchParams(searchQuery, selectedFilters, nextIngredients, 1)
      const queryString = params.toString()
      router.push(queryString ? `/results?${queryString}` : "/results")
    },
    [ingredients, router, searchQuery, selectedFilters],
  )

  return (
    <main className="min-h-screen bg-background">
      <SearchNavBar
        searchQuery={searchQuery}
        onSearchChange={handleSearchChange}
        onSearchSubmit={handleSearchSubmit}
      />
      <RecipeResultsPage
        searchQuery={searchQuery}
        filters={selectedFilters}
        ingredients={ingredients}
        onFilterChange={handleFilterChange}
        onAddIngredient={handleAddIngredient}
        onRemoveIngredient={handleRemoveIngredient}
        data={data}
        isLoading={isLoading}
        error={error}
        onPageChange={handlePageChange}
      />
    </main>
  )
}

function parseIngredientParams(params: URLSearchParams | ReadonlyURLSearchParams): string[] {
  const collected: string[] = []
  for (const value of params.getAll("ingredient")) {
    if (value) {
      collected.push(value)
    }
  }
  const csv = params.get("ingredients")
  if (csv) {
    for (const part of csv.split(",")) {
      if (part) {
        collected.push(part)
      }
    }
  }

  const seen = new Set<string>()
  const normalized: string[] = []
  for (const value of collected) {
    const trimmed = value.trim()
    if (!trimmed) {
      continue
    }
    const lower = trimmed.toLowerCase()
    if (seen.has(lower)) {
      continue
    }
    seen.add(lower)
    normalized.push(trimmed)
  }
  return normalized
}

function buildResultsSearchParams(
  query: string,
  filters: FiltersState,
  ingredients: string[],
  page: number,
): URLSearchParams {
  const params = new URLSearchParams()
  const trimmedQuery = query.trim()
  if (trimmedQuery) {
    params.set("q", trimmedQuery)
  }
  if (filters.cuisine) {
    params.append("cuisine", filters.cuisine)
  }
  if (filters.meal) {
    params.append("meal", filters.meal)
  }
  if (filters.diet) {
    params.append("diet", filters.diet)
  }
  for (const ingredient of ingredients) {
    const cleaned = ingredient.trim()
    if (cleaned) {
      params.append("ingredient", cleaned)
    }
  }
  if (page > 1) {
    params.set("page", page.toString())
  }
  return params
}
