"use client"

import Link from "next/link"
import { useMemo } from "react"
import FavoriteButton from "./favorite-button"

export type FiltersState = {
  cuisine: string
  meal: string
  diet: string
}

type FilterOption = {
  value: string
  label: string
}

export interface RecipeSummary {
  id: number
  title: string | null
  sourceName: string
  sourceUrl: string
  description: string | null
  image: string | null
  updatedAt: string | null
}

interface PaginationInfo {
  page: number
  pageSize: number
  total: number
  totalPages: number
}

export interface RecipesResponse {
  items: RecipeSummary[]
  pagination: PaginationInfo
  filters: {
    query: string | null
    ingredients: string[]
    cuisines: string[]
    meals: string[]
    diets: string[]
  }
}

interface RecipeResultsPageProps {
  searchQuery: string
  filters: FiltersState
  onFilterChange: (filters: FiltersState) => void
  data: RecipesResponse | null
  isLoading: boolean
  error: string | null
  onPageChange: (page: number) => void
}

const CUISINE_OPTIONS: FilterOption[] = [
  { value: "", label: "All cuisines" },
  { value: "american", label: "American" },
  { value: "british", label: "British" },
  { value: "chinese", label: "Chinese" },
  { value: "french", label: "French" },
  { value: "greek", label: "Greek" },
  { value: "indian", label: "Indian" },
  { value: "italian", label: "Italian" },
  { value: "japanese", label: "Japanese" },
  { value: "mexican", label: "Mexican" },
  { value: "middle_eastern", label: "Middle Eastern" },
  { value: "spanish", label: "Spanish" },
  { value: "thai", label: "Thai" },
  { value: "mediterranean", label: "Mediterranean" },
]

const MEAL_OPTIONS: FilterOption[] = [
  { value: "", label: "All meals" },
  { value: "breakfast", label: "Breakfast" },
  { value: "lunch", label: "Lunch" },
  { value: "dinner", label: "Dinner" },
  { value: "starter", label: "Starter" },
  { value: "dessert", label: "Dessert" },
  { value: "drink", label: "Drink" },
]

const DIET_OPTIONS: FilterOption[] = [
  { value: "", label: "All diets" },
  { value: "vegetarian", label: "Vegetarian" },
  { value: "vegan", label: "Vegan" },
  { value: "gluten_free", label: "Gluten-Free" },
  { value: "keto", label: "Keto" },
  { value: "paleo", label: "Paleo" },
  { value: "healthy", label: "Healthy" },
]

const PLACEHOLDER_IMAGE = "/placeholder.svg"

export default function RecipeResultsPage({
  searchQuery,
  filters,
  onFilterChange,
  data,
  isLoading,
  error,
  onPageChange,
}: RecipeResultsPageProps) {
  const items = data?.items ?? []
  const pagination = data?.pagination
  const normalizedQuery = data?.filters.query ?? (searchQuery.trim() || null)
  const heading = normalizedQuery ? `Results for "${normalizedQuery}"` : "Latest recipes"
  const total = pagination?.total ?? 0
  const subtitle = `${total} recipe${total === 1 ? "" : "s"} found`

  const appliedFilters = useMemo(() => buildAppliedFilterLabels(data), [data])

  return (
    <div className="bg-background min-h-screen px-4 py-12">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8 space-y-3">
          <h2 className="text-3xl font-bold text-foreground">{heading}</h2>
          <p className="text-muted-foreground">{isLoading && !data ? "Loading recipes..." : subtitle}</p>
          {appliedFilters.length > 0 && (
            <div className="flex flex-wrap gap-2 text-sm text-muted-foreground">
              {appliedFilters.map((label) => (
                <span key={label} className="rounded-full bg-muted px-3 py-1">
                  {label}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="mb-8 flex flex-wrap gap-4">
          <FilterSelect
            label="Cuisine"
            value={filters.cuisine}
            options={CUISINE_OPTIONS}
            onChange={(value) => onFilterChange({ ...filters, cuisine: value })}
          />
          <FilterSelect
            label="Meal"
            value={filters.meal}
            options={MEAL_OPTIONS}
            onChange={(value) => onFilterChange({ ...filters, meal: value })}
          />
          <FilterSelect
            label="Diet"
            value={filters.diet}
            options={DIET_OPTIONS}
            onChange={(value) => onFilterChange({ ...filters, diet: value })}
          />
        </div>

        {error ? (
          <div className="py-12 text-center">
            <p className="text-lg text-red-500">{error}</p>
          </div>
        ) : isLoading && !data ? (
          <div className="py-12 text-center">
            <p className="text-lg text-muted-foreground">Loading recipes...</p>
          </div>
        ) : items.length > 0 ? (
          <>
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {items.map((recipe) => {
                const formattedUpdatedAt = formatUpdatedAt(recipe.updatedAt)
                const recipeTitle = recipe.title ?? "Untitled recipe"
                return (
                  <article key={recipe.id} className="flex h-full flex-col overflow-hidden rounded-lg border border-border bg-card">
                    <div className="relative h-48 bg-muted">
                      <img
                        src={recipe.image || PLACEHOLDER_IMAGE}
                        alt={recipeTitle}
                        className="h-full w-full object-cover"
                      />
                      <div className="absolute left-3 top-3">
                        <FavoriteButton
                          recipeId={recipe.id}
                          recipeName={recipeTitle}
                          recipeImage={recipe.image || PLACEHOLDER_IMAGE}
                          size="md"
                        />
                      </div>
                    </div>
                    <div className="flex flex-1 flex-col p-4">
                      <Link
                        href={`/recipe/${recipe.id}`}
                        className="mb-2 block text-lg font-semibold text-foreground hover:text-primary"
                      >
                        {recipeTitle}
                      </Link>
                      {recipe.description && (
                        <p className="mb-4 line-clamp-3 text-sm text-muted-foreground">{recipe.description}</p>
                      )}
                      <div className="mt-auto space-y-1 text-sm text-muted-foreground">
                        <p>
                          From{" "}
                          <a className="font-medium hover:text-primary" href={recipe.sourceUrl} target="_blank" rel="noopener noreferrer">
                            {recipe.sourceName}
                          </a>
                        </p>
                        {formattedUpdatedAt && <p>Updated {formattedUpdatedAt}</p>}
                      </div>
                    </div>
                  </article>
                )
              })}
            </div>
            {pagination && (
              <Pagination
                page={pagination.page}
                totalPages={pagination.totalPages}
                onPageChange={onPageChange}
                isLoading={isLoading}
              />
            )}
          </>
        ) : (
          <div className="py-12 text-center">
            <p className="text-lg text-muted-foreground">No recipes found. Try adjusting your filters.</p>
          </div>
        )}
      </div>
    </div>
  )
}

function formatUpdatedAt(value: string | null): string | null {
  if (!value) {
    return null
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return null
  }
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date)
}

function buildAppliedFilterLabels(data: RecipesResponse | null): string[] {
  if (!data) {
    return []
  }
  const labels: string[] = []
  const { filters } = data
  if (filters.cuisines.length > 0) {
    labels.push(`Cuisine: ${filters.cuisines.map((value) => findLabel(CUISINE_OPTIONS, value)).join(", ")}`)
  }
  if (filters.meals.length > 0) {
    labels.push(`Meal: ${filters.meals.map((value) => findLabel(MEAL_OPTIONS, value)).join(", ")}`)
  }
  if (filters.diets.length > 0) {
    labels.push(`Diet: ${filters.diets.map((value) => findLabel(DIET_OPTIONS, value)).join(", ")}`)
  }
  if (filters.ingredients.length > 0) {
    labels.push(`Ingredients: ${filters.ingredients.join(", ")}`)
  }
  return labels
}

function findLabel(options: FilterOption[], value: string): string {
  const option = options.find((candidate) => candidate.value === value)
  return option ? option.label : value
}

interface FilterSelectProps {
  label: string
  value: string
  options: FilterOption[]
  onChange: (value: string) => void
}

function FilterSelect({ label, value, options, onChange }: FilterSelectProps) {
  return (
    <div className="flex flex-col gap-2">
      <label className="text-sm font-medium text-foreground">{label}</label>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="cursor-pointer rounded-lg border border-border bg-card px-4 py-2 text-foreground focus:border-transparent focus:ring-2 focus:ring-primary"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  )
}

interface PaginationProps {
  page: number
  totalPages: number
  onPageChange: (page: number) => void
  isLoading: boolean
}

function Pagination({ page, totalPages, onPageChange, isLoading }: PaginationProps) {
  if (totalPages <= 1) {
    return null
  }
  const pages = buildPageSequence(page, totalPages)
  return (
    <nav className="mt-10 flex justify-center" aria-label="Search results pages">
      <ul className="flex items-center gap-2">
        <li>
          <button
            type="button"
            className="rounded-md border border-border px-3 py-2 text-sm text-foreground transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
            onClick={() => onPageChange(page - 1)}
            disabled={page === 1 || isLoading}
          >
            Previous
          </button>
        </li>
        {pages.map((pageNumber) => (
          <li key={pageNumber}>
            <button
              type="button"
              onClick={() => onPageChange(pageNumber)}
              disabled={pageNumber === page || isLoading}
              className={`rounded-md px-3 py-2 text-sm transition-colors ${
                pageNumber === page
                  ? "bg-primary text-primary-foreground"
                  : "border border-border text-foreground hover:bg-muted"
              } disabled:cursor-not-allowed disabled:opacity-70`}
            >
              {pageNumber}
            </button>
          </li>
        ))}
        <li>
          <button
            type="button"
            className="rounded-md border border-border px-3 py-2 text-sm text-foreground transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
            onClick={() => onPageChange(page + 1)}
            disabled={page === totalPages || isLoading}
          >
            Next
          </button>
        </li>
      </ul>
    </nav>
  )
}

function buildPageSequence(page: number, totalPages: number): number[] {
  if (totalPages <= 10) {
    return Array.from({ length: totalPages }, (_, index) => index + 1)
  }
  if (page < 10) {
    return Array.from({ length: 10 }, (_, index) => index + 1)
  }
  let start = Math.max(1, page - 5)
  let end = Math.min(totalPages, page + 5)
  if (end - start < 10 && start > 1) {
    start = Math.max(1, end - 10)
  }
  return Array.from({ length: end - start + 1 }, (_, index) => start + index)
}

