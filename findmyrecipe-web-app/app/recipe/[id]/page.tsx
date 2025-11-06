"use client"

import Link from "next/link"
import { useParams } from "next/navigation"
import { useEffect, useMemo, useState } from "react"
import type { ReactNode } from "react"
import SubscriptionGate from "@/components/subscription-gate"

interface RecipeDetail {
  id: number
  title: string | null
  sourceName: string
  sourceUrl: string
  description: string | null
  image: string | null
  updatedAt: string | null
  ingredients: string[]
  instructions: string[]
  prepTime: string | null
  cookTime: string | null
  totalTime: string | null
  servings: string | null
  author: string | null
  categories: string[]
  tags: string[]
  raw: Record<string, unknown> | null
  nutrients: Record<string, number> | null
}

export default function RecipePage() {
  const params = useParams()
  const rawId = Array.isArray(params?.id) ? params?.id[0] : params?.id
  const recipeId = rawId ? Number.parseInt(rawId, 10) : Number.NaN
  const [recipe, setRecipe] = useState<RecipeDetail | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!Number.isFinite(recipeId) || recipeId <= 0) {
      setError("Invalid recipe identifier.")
      setIsLoading(false)
      return
    }

    const controller = new AbortController()
    const url = `/api/v1/recipes/${recipeId}`

    setIsLoading(true)
    setError(null)

    fetch(url, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) {
          const payload = await response.json().catch(() => ({}))
          const message = typeof payload.error === "string" ? payload.error : `Unable to load recipe (${response.status})`
          throw new Error(message)
        }
        return response.json() as Promise<RecipeDetail>
      })
      .then((payload) => {
        setRecipe(payload)
        setIsLoading(false)
      })
      .catch((fetchError: unknown) => {
        if ((fetchError as Error).name === "AbortError") {
          return
        }
        setIsLoading(false)
        setError(fetchError instanceof Error ? fetchError.message : "Unable to load recipe details")
      })

    return () => {
      controller.abort()
    }
  }, [recipeId])

  if (isLoading) {
    return (
      <CenteredState>
        <p className="text-lg text-muted-foreground">Loading recipe...</p>
      </CenteredState>
    )
  }

  if (error) {
    return (
      <CenteredState>
        <div className="space-y-4 text-center">
          <h1 className="text-3xl font-bold text-foreground">Unable to display this recipe</h1>
          <p className="text-muted-foreground">{error}</p>
          <Link href="/results" className="text-primary hover:underline">
            ← Back to Results
          </Link>
        </div>
      </CenteredState>
    )
  }

  if (!recipe) {
    return (
      <CenteredState>
        <div className="space-y-4 text-center">
          <h1 className="text-3xl font-bold text-foreground">Recipe not found</h1>
          <Link href="/results" className="text-primary hover:underline">
            ← Back to Results
          </Link>
        </div>
      </CenteredState>
    )
  }

  return (
    <SubscriptionGate recipeId={recipe.id} recipeName={recipe.title ?? "Recipe"}>
      <RecipeContent recipe={recipe} />
    </SubscriptionGate>
  )
}

function RecipeContent({ recipe }: { recipe: RecipeDetail }) {
  const formattedUpdatedAt = formatUpdatedAt(recipe.updatedAt)
  const metaItems = useMemo(
    () =>
      [
        { label: "Prep time", value: recipe.prepTime },
        { label: "Cook time", value: recipe.cookTime },
        { label: "Total time", value: recipe.totalTime },
        { label: "Servings", value: recipe.servings },
        { label: "Author", value: recipe.author },
      ].filter((entry) => Boolean(entry.value)),
    [recipe.prepTime, recipe.cookTime, recipe.totalTime, recipe.servings, recipe.author],
  )

  return (
    <div className="min-h-screen bg-background">
      <div className="sticky top-0 z-50 bg-white/90 backdrop-blur border-b border-border">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-4">
          <Link href="/results" className="flex items-center gap-2 text-primary hover:underline">
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Results
          </Link>
          <a
            href={recipe.sourceUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-medium text-muted-foreground hover:text-foreground"
          >
            View original recipe
          </a>
        </div>
      </div>

      <main className="mx-auto max-w-4xl space-y-10 px-4 py-12">
        <header className="space-y-6">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold text-foreground">{recipe.title ?? "Untitled recipe"}</h1>
            {recipe.description && <p className="text-lg text-muted-foreground">{recipe.description}</p>}
          </div>
          <div className="flex flex-col gap-2 text-sm text-muted-foreground">
            <span>
              From{" "}
              <a className="font-medium hover:text-primary" href={recipe.sourceUrl} target="_blank" rel="noopener noreferrer">
                {recipe.sourceName}
              </a>
            </span>
            {formattedUpdatedAt && <span>Updated {formattedUpdatedAt}</span>}
          </div>
          {recipe.image && (
            <div className="overflow-hidden rounded-lg border border-border bg-muted">
              <img src={recipe.image} alt={recipe.title ?? "Recipe image"} className="h-full w-full object-cover" />
            </div>
          )}
        </header>

        {metaItems.length > 0 && (
          <section className="grid gap-4 rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground md:grid-cols-2">
            {metaItems.map((item) => (
              <div key={item.label}>
                <p className="text-xs uppercase tracking-wide text-muted-foreground">{item.label}</p>
                <p className="text-base font-medium text-foreground">{item.value}</p>
              </div>
            ))}
          </section>
        )}

        {recipe.ingredients.length > 0 && (
          <section className="space-y-4">
            <h2 className="text-2xl font-semibold text-foreground">Ingredients</h2>
            <ul className="list-disc space-y-2 pl-5 text-foreground">
              {recipe.ingredients.map((item, index) => (
                <li key={`${item}-${index}`}>{item}</li>
              ))}
            </ul>
          </section>
        )}

        {recipe.instructions.length > 0 && (
          <section className="space-y-4">
            <h2 className="text-2xl font-semibold text-foreground">Instructions</h2>
            <ol className="space-y-3 pl-5 text-foreground">
              {recipe.instructions.map((step, index) => (
                <li key={`${step}-${index}`} className="list-decimal">
                  {step}
                </li>
              ))}
            </ol>
          </section>
        )}

        {(recipe.categories.length > 0 || recipe.tags.length > 0) && (
          <section className="space-y-4">
            {recipe.categories.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Categories</h3>
                <TagList items={recipe.categories} />
              </div>
            )}
            {recipe.tags.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Tags</h3>
                <TagList items={recipe.tags} />
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  )
}

function TagList({ items }: { items: string[] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <span key={item} className="rounded-full bg-muted px-3 py-1 text-sm text-foreground">
          {item}
        </span>
      ))}
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
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date)
}

function CenteredState({ children }: { children: ReactNode }) {
  return <div className="flex min-h-screen items-center justify-center bg-background px-4">{children}</div>
}

