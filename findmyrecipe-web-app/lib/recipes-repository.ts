import { CUISINE_LOOKUP, DIET_LOOKUP, MEAL_LOOKUP, normalizeSelection } from "./filters"

class ApiRequestError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

function getApiBaseUrl() {
  const baseUrl = process.env.RECIPES_API_BASE_URL || process.env.NEXT_PUBLIC_RECIPES_API_BASE_URL
  return baseUrl?.replace(/\/$/u, "") || "http://localhost:5000/api/v1"
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

export interface RecipeDetail extends RecipeSummary {
  instructions: string[]
  prepTime: string | null
  cookTime: string | null
  totalTime: string | null
  servings: string | null
  author: string | null
  categories: string[]
  tags: string[]
  raw: Record<string, unknown> | null
}

export interface PaginatedRecipes {
  items: RecipeSummary[]
  total: number
  page: number
  pageSize: number
  totalPages: number
  filters: {
    query: string | null
    ingredients: string[]
    cuisines: string[]
    meals: string[]
    diets: string[]
  }
}

const DEFAULT_PAGE_SIZE = Number.parseInt(process.env.PAGE_SIZE ?? "20", 10)

const NUTRIENT_ALIASES: Record<string, string> = {
  calories: "calories",
  energy: "calories",
  kilocalories: "calories",
  kcal: "calories",
  protein: "protein",
  proteins: "protein",
  carbohydrates: "carbohydrates",
  carbohydrate: "carbohydrates",
  carbs: "carbohydrates",
  fat: "fat",
  fats: "fat",
  lipid: "fat",
  fiber: "fiber",
  fibre: "fiber",
  "dietary fiber": "fiber",
  sugar: "sugar",
  sugars: "sugar",
}

const SUPPORTED_NUTRIENTS = new Set(Object.values(NUTRIENT_ALIASES))

function parsePageSize(rawPageSize: string | null | undefined): number {
  if (!rawPageSize) {
    return Number.isFinite(DEFAULT_PAGE_SIZE) && DEFAULT_PAGE_SIZE > 0 ? DEFAULT_PAGE_SIZE : 20
  }
  const parsed = Number.parseInt(rawPageSize, 10)
  if (!Number.isFinite(parsed) || parsed <= 0 || parsed > 100) {
    return Number.isFinite(DEFAULT_PAGE_SIZE) && DEFAULT_PAGE_SIZE > 0 ? DEFAULT_PAGE_SIZE : 20
  }
  return parsed
}

function normalizeQuery(raw: string | null): string | null {
  if (!raw) {
    return null
  }
  const trimmed = raw.trim()
  return trimmed.length > 0 ? trimmed : null
}

function parseIngredients(searchParams: URLSearchParams): string[] {
  const values: string[] = []
  for (const ingredient of searchParams.getAll("ingredient")) {
    if (ingredient) {
      values.push(ingredient)
    }
  }
  const csv = searchParams.get("ingredients")
  if (csv) {
    for (const part of csv.split(",")) {
      if (part) {
        values.push(part)
      }
    }
  }
  const normalized: string[] = []
  const seen = new Set<string>()
  for (const value of values) {
    const cleaned = value.trim().toLowerCase()
    if (cleaned && !seen.has(cleaned)) {
      normalized.push(cleaned)
      seen.add(cleaned)
    }
  }
  return normalized
}

function parsePage(value: string | null): number {
  const parsed = Number.parseInt(value ?? "1", 10)
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return 1
  }
  return parsed
}

function canonicalNutrientKey(raw: unknown): string | null {
  if (typeof raw !== "string") {
    return null
  }
  const normalized = raw.trim().toLowerCase()
  return NUTRIENT_ALIASES[normalized] ?? (SUPPORTED_NUTRIENTS.has(normalized) ? normalized : null)
}

function roundToTwo(value: number): number {
  return Math.round(value * 100) / 100
}

function coerceToNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value
  }
  if (typeof value === "string") {
    const cleaned = value.trim().toLowerCase().replace(/(kcal|kj|g|mg)$/u, "").trim()
    if (!cleaned) {
      return null
    }
    const parsed = Number.parseFloat(cleaned)
    return Number.isFinite(parsed) ? parsed : null
  }
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>
    if ("amount" in record) {
      const coerced = coerceToNumber(record.amount)
      if (coerced !== null) {
        return coerced
      }
    }
    if ("value" in record) {
      const coerced = coerceToNumber(record.value)
      if (coerced !== null) {
        return coerced
      }
    }
    if ("quantity" in record) {
      const coerced = coerceToNumber(record.quantity)
      if (coerced !== null) {
        return coerced
      }
    }
  }
  return null
}

function normalizeNutrients(source: unknown): Record<string, number> | null {
  if (!source) {
    return null
  }

  if (Array.isArray(source)) {
    const totals = new Map<string, number>()
    for (const entry of source) {
      if (!entry || typeof entry !== "object") {
        continue
      }
      const record = entry as Record<string, unknown>
      const alias =
        canonicalNutrientKey(record.name) ??
        canonicalNutrientKey(record.title) ??
        canonicalNutrientKey(record.label)
      if (!alias) {
        continue
      }
      const value =
        coerceToNumber(record.amount) ??
        coerceToNumber(record.value) ??
        coerceToNumber(record.quantity) ??
        coerceToNumber(entry)
      if (value === null) {
        continue
      }
      totals.set(alias, (totals.get(alias) ?? 0) + value)
    }
    if (totals.size === 0) {
      return null
    }
    return Object.fromEntries(
      Array.from(totals.entries(), ([key, value]) => [key, roundToTwo(value)]),
    )
  }

  if (typeof source === "object") {
    const record = source as Record<string, unknown>
    const normalized: Record<string, number> = {}
    for (const [key, rawValue] of Object.entries(record)) {
      if (key === "nutrients" || key === "nutrition") {
        const nested = normalizeNutrients(rawValue)
        if (nested) {
          for (const [nestedKey, nestedValue] of Object.entries(nested)) {
            normalized[nestedKey] = nestedValue
          }
        }
        continue
      }
      const alias = canonicalNutrientKey(key)
      if (!alias) {
        continue
      }
      const value = coerceToNumber(rawValue)
      if (value === null) {
        continue
      }
      normalized[alias] = roundToTwo(value)
    }
    return Object.keys(normalized).length > 0 ? normalized : null
  }

  return null
}

function aggregateIngredientNutrition(rawIngredients: unknown): Record<string, number> | null {
  if (!Array.isArray(rawIngredients)) {
    return null
  }
  const totals = new Map<string, number>()
  let found = false
  for (const entry of rawIngredients) {
    if (!entry || typeof entry !== "object") {
      continue
    }
    const record = entry as Record<string, unknown>
    const nutrition = normalizeNutrients(record.nutrition ?? record.nutrients)
    if (!nutrition) {
      continue
    }
    found = true
    for (const [key, value] of Object.entries(nutrition)) {
      totals.set(key, (totals.get(key) ?? 0) + value)
    }
  }
  if (!found) {
    return null
  }
  return Object.fromEntries(
    Array.from(totals.entries(), ([key, value]) => [key, roundToTwo(value)]),
  )
}

function extractIngredientStrings(rawIngredients: unknown): string[] {
  if (!Array.isArray(rawIngredients)) {
    return []
  }
  const items: string[] = []
  for (const entry of rawIngredients) {
    if (typeof entry === "string") {
      const cleaned = entry.trim()
      if (cleaned) {
        items.push(cleaned)
      }
      continue
    }
    if (!entry || typeof entry !== "object") {
      continue
    }
    const record = entry as Record<string, unknown>
    const name =
      record.original ??
      record.originalString ??
      record.text ??
      record.name ??
      record.ingredient
    if (typeof name === "string" && name.trim().length > 0) {
      items.push(name.trim())
    }
  }
  return items
}

function extractNormalizedNutrition(
  raw: Record<string, unknown> | null,
): Record<string, number> | null {
  if (!raw) {
    return null
  }
  const direct = normalizeNutrients(raw.nutrition ?? raw.nutrients)
  if (direct) {
    return direct
  }
  return aggregateIngredientNutrition(raw.ingredients)
}

function parseDate(value: unknown): string | null {
  if (!value) {
    return null
  }
  try {
    const date = new Date(value as string)
    return Number.isNaN(date.getTime()) ? null : date.toISOString()
  } catch {
    return null
  }
}

function parseJsonList(value: unknown): string[] {
  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value)
      if (Array.isArray(parsed)) {
        return parsed.filter((item) => typeof item === "string" && item.trim().length > 0).map((item) => item.trim())
      }
    } catch {
      return []
    }
  }
  if (Array.isArray(value)) {
    return value.filter((item) => typeof item === "string" && item.trim().length > 0).map((item) => item.trim())
  }
  return []
}

function parseJsonObject(value: unknown): Record<string, unknown> | null {
  if (!value) {
    return null
  }
  if (typeof value === "object") {
    return value as Record<string, unknown>
  }
  if (typeof value === "string" && value.trim().length > 0) {
    try {
      const parsed = JSON.parse(value)
      return parsed && typeof parsed === "object" ? (parsed as Record<string, unknown>) : null
    } catch {
      return null
    }
  }
  return null
}

export function extractListParams(searchParams: URLSearchParams) {
  const query = normalizeQuery(searchParams.get("q"))
  const page = parsePage(searchParams.get("page"))
  const pageSize = parsePageSize(searchParams.get("pageSize"))
  const ingredients = parseIngredients(searchParams)
  const cuisines = normalizeSelection(searchParams.getAll("cuisine"), CUISINE_LOOKUP)
  const meals = normalizeSelection(searchParams.getAll("meal"), MEAL_LOOKUP)
  const diets = normalizeSelection(searchParams.getAll("diet"), DIET_LOOKUP)
  return {
    query,
    page,
    pageSize,
    ingredients,
    cuisines,
    meals,
    diets,
  }
}

export async function fetchRecipes(searchParams: URLSearchParams): Promise<PaginatedRecipes> {
  const { query, page, pageSize, ingredients, cuisines, meals, diets } = extractListParams(searchParams)

  const outbound = new URLSearchParams()
  if (query) {
    outbound.set("q", query)
  }
  outbound.set("page", String(page))
  outbound.set("pageSize", String(pageSize))
  for (const ingredient of ingredients) {
    outbound.append("ingredient", ingredient)
  }
  for (const cuisine of cuisines) {
    outbound.append("cuisine", cuisine)
  }
  for (const meal of meals) {
    outbound.append("meal", meal)
  }
  for (const diet of diets) {
    outbound.append("diet", diet)
  }

  const apiUrl = `${getApiBaseUrl()}/recipes${outbound.toString() ? `?${outbound.toString()}` : ""}`
  let response: Response
  try {
    response = await fetch(apiUrl)
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Failed to reach recipes API"
    throw new ApiRequestError(message, 502)
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    const message = typeof payload.error === "string" ? payload.error : `Request failed with status ${response.status}`
    throw new ApiRequestError(message, response.status)
  }

  const payload = (await response.json()) as PaginatedRecipes

  return {
    items: Array.isArray(payload.items)
      ? payload.items.map(normalizeSummary)
      : [],
    total: typeof payload.total === "number" ? payload.total : payload.pagination?.total ?? 0,
    page: payload.pagination?.page ?? page,
    pageSize: payload.pagination?.pageSize ?? pageSize,
    totalPages: payload.pagination?.totalPages ?? payload.totalPages ?? 1,
    filters: payload.filters ?? {
      query,
      ingredients,
      cuisines,
      meals,
      diets,
    },
  }
}

export async function fetchRecipeDetail(id: number): Promise<RecipeDetail | null> {
  if (!Number.isFinite(id) || id <= 0) {
    return null
  }

  const apiUrl = `${getApiBaseUrl()}/recipes/${id}`
  const response = await fetch(apiUrl)
  if (response.status === 404) {
    return null
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    const message = typeof payload.error === "string" ? payload.error : `Request failed with status ${response.status}`
    throw new Error(message)
  }

  const payload = (await response.json()) as RecipeDetail
  return normalizeDetail(payload)
}

function normalizeHighlights(highlights: unknown): Record<string, string[]> | undefined {
  if (!highlights || typeof highlights !== "object") {
    return undefined
  }
  const entries: [string, string[]][] = []
  for (const [key, value] of Object.entries(highlights)) {
    const parts = Array.isArray(value)
      ? value.filter((part) => typeof part === "string" && part.trim().length > 0).map((part) => part.trim())
      : []
    if (parts.length > 0) {
      entries.push([key, parts])
    }
  }
  return entries.length > 0 ? Object.fromEntries(entries) : undefined
}

function normalizeSummary(payload: any): RecipeSummary {
  const raw = parseJsonObject(payload?.raw)
  const normalizedIngredients = parseJsonList(payload?.ingredients)
  const fallbackIngredients = extractIngredientStrings(raw?.ingredients)
  const nutrients =
    (payload?.nutrients && typeof payload.nutrients === "object" ? (payload.nutrients as Record<string, number>) : null) ??
    extractNormalizedNutrition(raw)

  const scoreValue = typeof payload?.score === "number" && Number.isFinite(payload.score) ? payload.score : null

  return {
    id: Number(payload?.id) || 0,
    title: typeof payload?.title === "string" ? payload.title : null,
    sourceName: typeof payload?.sourceName === "string" ? payload.sourceName : "",
    sourceUrl: typeof payload?.sourceUrl === "string" ? payload.sourceUrl : "",
    description: typeof payload?.description === "string" ? payload.description : null,
    image: typeof payload?.image === "string" ? payload.image : null,
    updatedAt: parseDate(payload?.updatedAt),
    ingredients: normalizedIngredients.length > 0 ? normalizedIngredients : fallbackIngredients,
    nutrients,
    score: scoreValue,
    highlights: normalizeHighlights(payload?.highlights),
  }
}

function normalizeDetail(payload: any): RecipeDetail {
  const summary = normalizeSummary(payload)
  const raw = parseJsonObject(payload?.raw)
  const instructions = parseJsonList(payload?.instructions)
  const categories = parseJsonList(payload?.categories)
  const tags = parseJsonList(payload?.tags)

  return {
    ...summary,
    ingredients: summary.ingredients,
    instructions,
    prepTime: typeof payload?.prepTime === "string" ? payload.prepTime : null,
    cookTime: typeof payload?.cookTime === "string" ? payload.cookTime : null,
    totalTime: typeof payload?.totalTime === "string" ? payload.totalTime : null,
    servings: typeof payload?.servings === "string" ? payload.servings : null,
    author: typeof payload?.author === "string" ? payload.author : null,
    categories,
    tags,
    raw,
    nutrients: summary.nutrients ?? extractNormalizedNutrition(raw),
  }
}
