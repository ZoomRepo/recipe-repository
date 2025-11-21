"use client"

import Link from "next/link"
import { useMemo, useState, useRef, useEffect } from "react"
import type React from "react"
import FavoriteButton from "./favorite-button"
import { Input } from "@/components/ui/input"

export type FiltersState = {
  cuisine: string
  meal: string
  diet: string
}

type FilterOption = {
  value: string
  label: string
}

function formatHighlight(highlights?: Record<string, string[]>): string | null {
  if (!highlights) {
    return null
  }

  for (const key of ["description", "ingredients", "title"]) {
    const candidates = highlights[key]
    if (Array.isArray(candidates)) {
      const snippet = candidates.find((value) => typeof value === "string" && value.trim().length > 0)
      if (snippet) {
        return snippet.replace(/<\/?.+?>/gu, "").trim()
      }
    }
  }

  const firstValue = Object.values(highlights).find((value) => Array.isArray(value) && value.length > 0)
  if (firstValue) {
    const snippet = firstValue.find((value) => typeof value === "string" && value.trim().length > 0)
    return snippet ? snippet.replace(/<\/?.+?>/gu, "").trim() : null
  }

  return null
}

export interface RecipeSummary {
  id: number
  title: string | null
  sourceName: string
  sourceUrl: string
  description: string | null
  image: string | null
  updatedAt: string | null
  ingredients: string[]
  nutrients: Record<string, number> | null
  score?: number | null
  highlights?: Record<string, string[]>
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
  ingredients: string[]
  onAddIngredient: (value: string) => void
  onRemoveIngredient: (value: string) => void
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

const NUTRIENT_LABELS: Record<string, { label: string; unit: string }> = {
  calories: { label: "Calories", unit: "kcal" },
  protein: { label: "Protein", unit: "g" },
  carbohydrates: { label: "Carbohydrates", unit: "g" },
  fat: { label: "Fat", unit: "g" },
  fiber: { label: "Fiber", unit: "g" },
  sugar: { label: "Sugar", unit: "g" },
}

const NUTRIENT_ORDER = ["calories", "protein", "carbohydrates", "fat", "fiber", "sugar"] as const

export default function RecipeResultsPage({
  searchQuery,
  filters,
  onFilterChange,
  ingredients,
  onAddIngredient,
  onRemoveIngredient,
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
          <IngredientFilter
            ingredients={ingredients}
            onAddIngredient={onAddIngredient}
            onRemoveIngredient={onRemoveIngredient}
          />
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
                const recipeTitle = recipe.title ?? "Untitled recipe"
                const nutrientEntries = NUTRIENT_ORDER.map((key) => {
                  const value = recipe.nutrients?.[key] ?? null
                  return value !== null && value !== undefined ? [key, value] : null
                }).filter((entry): entry is [string, number] => Array.isArray(entry))
                const formattedUpdatedAt = formatUpdatedAt(recipe.updatedAt)
                const highlightSnippet = formatHighlight(recipe.highlights)

                return (
                  <article
                    key={recipe.id}
                    tabIndex={0}
                    className="group relative flex h-full flex-col overflow-hidden rounded-lg border border-border bg-card shadow-sm transition-shadow focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background hover:shadow-lg"
                  >
                    <div className="pointer-events-none absolute inset-0 z-20 flex bg-slate-950/90 text-slate-100 opacity-0 transition-opacity duration-200 group-hover:opacity-100 group-focus-within:opacity-100">
                      <div className="pointer-events-auto flex w-full flex-col gap-5 overflow-hidden p-5">
                        <div className="flex flex-col gap-3 text-sm text-slate-200">
                          {recipe.score !== null && recipe.score !== undefined && (
                            <span className="inline-flex w-fit items-center gap-2 rounded-full bg-slate-800 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-100">
                              <span>Relevance</span>
                              <span>{recipe.score.toFixed(2)}</span>
                            </span>
                          )}
                          {highlightSnippet && <p className="line-clamp-2 text-slate-200/90">{highlightSnippet}</p>}
                        </div>
                        <div className="grid gap-5 md:grid-cols-2">
                          <section>
                            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-300">Nutrition</h3>
                            {nutrientEntries.length > 0 ? (
                              <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
                                {nutrientEntries.map(([key, value]) => (
                                  <div key={key} className="contents">
                                    <dt className="text-slate-300">{NUTRIENT_LABELS[key].label}</dt>
                                    <dd className="text-right font-semibold text-white">
                                      {value.toFixed(2)} {NUTRIENT_LABELS[key].unit}
                                    </dd>
                                  </div>
                                ))}
                              </dl>
                            ) : (
                              <p className="mt-3 text-sm text-slate-300/80">Nutrition information unavailable.</p>
                            )}
                          </section>
                          <section>
                            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-300">Ingredients</h3>
                            {recipe.ingredients.length > 0 ? (
                              <ul className="mt-3 space-y-2 text-sm leading-snug text-slate-100/90">
                                {recipe.ingredients.map((ingredient, index) => (
                                  <li key={`${ingredient}-${index}`}>{ingredient}</li>
                                ))}
                              </ul>
                            ) : (
                              <p className="mt-3 text-sm text-slate-300/80">Ingredients unavailable.</p>
                            )}
                          </section>
                        </div>
                        <div className="mt-auto flex justify-end">
                          <Link
                            href={`/recipe/${recipe.id}`}
                            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-sm transition hover:bg-primary/90"
                          >
                            View recipe
                            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                            </svg>
                          </Link>
                        </div>
                      </div>
                    </div>

                    <div className="relative h-48 bg-muted">
                      <img
                        src={recipe.image || PLACEHOLDER_IMAGE}
                        alt={recipeTitle}
                        className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
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

                    <div className="flex flex-1 flex-col gap-3 p-4">
                      <h3 className="text-lg font-semibold text-foreground">
                        <Link href={`/recipe/${recipe.id}`} className="hover:text-primary">
                          {recipeTitle}
                        </Link>
                      </h3>
                      {recipe.description && (
                        <p className="line-clamp-3 text-sm text-muted-foreground">{recipe.description}</p>
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

interface IngredientFilterProps {
  ingredients: string[]
  onAddIngredient: (value: string) => void
  onRemoveIngredient: (value: string) => void
}

function IngredientFilter({ ingredients, onAddIngredient, onRemoveIngredient }: IngredientFilterProps) {
  const [isAdding, setIsAdding] = useState(false)
  const [value, setValue] = useState("")
  const inputRef = useRef<HTMLInputElement | null>(null)

  useEffect(() => {
    if (isAdding) {
      inputRef.current?.focus()
    }
  }, [isAdding])

  const handleSubmit = () => {
    const trimmed = value.trim()
    if (!trimmed) {
      setIsAdding(false)
      setValue("")
      return
    }
    onAddIngredient(trimmed)
    setValue("")
    setIsAdding(false)
  }

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      event.preventDefault()
      handleSubmit()
    } else if (event.key === "Escape") {
      event.preventDefault()
      setIsAdding(false)
      setValue("")
    }
  }

  const handleBlur = () => {
    setIsAdding(false)
    setValue("")
  }

  return (
    <div className="flex min-w-[240px] flex-col gap-2">
      <span className="text-sm font-medium text-foreground">Ingredients</span>
      <div className="flex flex-wrap items-center gap-2">
        {ingredients.map((ingredient) => (
          <span
            key={ingredient}
            className="inline-flex items-center gap-1 rounded-full bg-muted px-3 py-1 text-sm text-foreground"
          >
            {ingredient}
            <button
              type="button"
              onClick={() => onRemoveIngredient(ingredient)}
              className="ml-1 text-muted-foreground transition hover:text-foreground"
              aria-label={`Remove ${ingredient}`}
            >
              <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 6l8 8M14 6l-8 8" />
              </svg>
            </button>
          </span>
        ))}
        {isAdding ? (
          <Input
            ref={inputRef}
            value={value}
            onChange={(event) => setValue(event.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={handleBlur}
            placeholder="Add ingredient"
            className="h-9 w-48"
          />
        ) : (
          <button
            type="button"
            onClick={() => setIsAdding(true)}
            className="text-sm font-medium text-primary transition hover:underline"
          >
            + Add ingredient
          </button>
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

