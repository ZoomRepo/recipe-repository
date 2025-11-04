import type { RowDataPacket } from "mysql2"
import { getPool } from "./database"
import {
  CUISINE_LOOKUP,
  DIET_LOOKUP,
  MEAL_LOOKUP,
  type FilterOption,
  normalizeSelection,
  normalizedKeywords,
} from "./filters"

export interface RecipeSummary {
  id: number
  title: string | null
  sourceName: string
  sourceUrl: string
  description: string | null
  image: string | null
  updatedAt: string | null
}

export interface RecipeDetail extends RecipeSummary {
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

function buildQueryConditions(
  query: string | null,
  ingredients: string[],
  cuisines: string[],
  meals: string[],
  diets: string[],
): { whereClause: string; params: unknown[] } {
  const conditions: string[] = []
  const params: unknown[] = []

  if (query) {
    const lowered = query.toLowerCase()
    const like = `%${lowered}%`
    const normalizedClause =
      "(LOWER(COALESCE(title, '')) LIKE ? OR " +
      "LOWER(COALESCE(description, '')) LIKE ? OR " +
      "LOWER(COALESCE(ingredients, '')) LIKE ? OR " +
      "LOWER(COALESCE(instructions, '')) LIKE ? OR " +
      "LOWER(COALESCE(categories, '')) LIKE ? OR " +
      "LOWER(COALESCE(tags, '')) LIKE ?)"
    const queryClauses = [normalizedClause]
    params.push(like, like, like, like, like, like)

    const keywords = lowered
      .split(/\s+/)
      .map((keyword) => keyword.trim())
      .filter((keyword) => keyword.length > 0)

    if (keywords.length > 1) {
      const keywordClause = "(LOWER(COALESCE(title, '')) LIKE ? OR LOWER(COALESCE(description, '')) LIKE ?)"
      for (const keyword of keywords) {
        const keywordLike = `%${keyword}%`
        queryClauses.push(keywordClause)
        params.push(keywordLike, keywordLike)
      }
    }

    conditions.push(`(${queryClauses.join(" OR ")})`)
  }

  for (const ingredient of ingredients) {
    const like = `%${ingredient.toLowerCase()}%`
    conditions.push("LOWER(ingredients) LIKE ?")
    params.push(like)
  }

  applyOptionFilters(cuisines, CUISINE_LOOKUP, conditions, params)
  applyOptionFilters(meals, MEAL_LOOKUP, conditions, params)
  applyOptionFilters(diets, DIET_LOOKUP, conditions, params)

  const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(" AND ")}` : ""
  return { whereClause, params }
}

function applyOptionFilters(
  selected: string[],
  lookup: Record<string, FilterOption>,
  conditions: string[],
  params: unknown[],
) {
  if (selected.length === 0) {
    return
  }

  const optionClauses: string[] = []
  for (const value of selected) {
    const option = lookup[value]
    if (!option) {
      continue
    }
    const keywords = normalizedKeywords(option)
    const clause = buildKeywordClause(keywords, params)
    if (clause) {
      optionClauses.push(clause)
    }
  }
  if (optionClauses.length > 0) {
    conditions.push(`(${optionClauses.join(" OR ")})`)
  }
}

function buildKeywordClause(keywords: string[], params: unknown[]): string | null {
  if (keywords.length === 0) {
    return null
  }

  const columnTemplate =
    "LOWER(COALESCE(title, '')) LIKE ? OR " +
    "LOWER(COALESCE(description, '')) LIKE ? OR " +
    "LOWER(COALESCE(categories, '')) LIKE ? OR " +
    "LOWER(COALESCE(tags, '')) LIKE ? OR " +
    "LOWER(COALESCE(ingredients, '')) LIKE ?"

  const keywordClauses: string[] = []
  for (const keyword of keywords) {
    const like = `%${keyword}%`
    keywordClauses.push(`(${columnTemplate})`)
    params.push(like, like, like, like, like)
  }

  if (keywordClauses.length === 0) {
    return null
  }
  return `(${keywordClauses.join(" OR ")})`
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
  if (typeof value !== "string" || value.trim().length === 0) {
    return []
  }
  try {
    const parsed = JSON.parse(value)
    if (Array.isArray(parsed)) {
      return parsed.filter((item) => typeof item === "string" && item.trim().length > 0).map((item) => item.trim())
    }
  } catch {
    return []
  }
  return []
}

function parseJsonObject(value: unknown): Record<string, unknown> | null {
  if (typeof value !== "string" || value.trim().length === 0) {
    return null
  }
  try {
    const parsed = JSON.parse(value)
    return parsed && typeof parsed === "object" ? (parsed as Record<string, unknown>) : null
  } catch {
    return null
  }
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
  const { whereClause, params } = buildQueryConditions(query, ingredients, cuisines, meals, diets)
  const offset = (page - 1) * pageSize

  const listingSql = `
    SELECT
      id,
      title,
      source_name AS sourceName,
      source_url AS sourceUrl,
      description,
      image,
      updated_at AS updatedAt
    FROM recipes
    ${whereClause}
    ORDER BY updated_at DESC, id DESC
    LIMIT ? OFFSET ?
  `

  const countSql = `SELECT COUNT(*) AS total FROM recipes ${whereClause}`

  const pool = getPool()
  const [rows] = await pool.query<RowDataPacket[]>(listingSql, [...params, pageSize, offset])
  const [countRows] = await pool.query<RowDataPacket[]>(countSql, params)
  const total = countRows.length > 0 ? Number(countRows[0].total ?? 0) : 0
  const normalizedPage = page > 0 ? page : 1
  const totalPages = total > 0 ? Math.ceil(total / pageSize) : 1

  return {
    items: rows.map((row) => ({
      id: Number(row.id),
      title: row.title ?? null,
      sourceName: row.sourceName,
      sourceUrl: row.sourceUrl,
      description: row.description ?? null,
      image: row.image ?? null,
      updatedAt: parseDate(row.updatedAt),
    })),
    total,
    page: normalizedPage,
    pageSize,
    totalPages,
    filters: {
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
  const sql = `
    SELECT
      id,
      title,
      source_name AS sourceName,
      source_url AS sourceUrl,
      description,
      image,
      ingredients,
      instructions,
      prep_time AS prepTime,
      cook_time AS cookTime,
      total_time AS totalTime,
      servings,
      author,
      categories,
      tags,
      raw,
      updated_at AS updatedAt
    FROM recipes
    WHERE id = ?
  `
  const pool = getPool()
  const [rows] = await pool.query<RowDataPacket[]>(sql, [id])
  if (rows.length === 0) {
    return null
  }
  const row = rows[0]
  return {
    id: Number(row.id),
    title: row.title ?? null,
    sourceName: row.sourceName,
    sourceUrl: row.sourceUrl,
    description: row.description ?? null,
    image: row.image ?? null,
    updatedAt: parseDate(row.updatedAt),
    ingredients: parseJsonList(row.ingredients),
    instructions: parseJsonList(row.instructions),
    prepTime: row.prepTime ?? null,
    cookTime: row.cookTime ?? null,
    totalTime: row.totalTime ?? null,
    servings: row.servings ?? null,
    author: row.author ?? null,
    categories: parseJsonList(row.categories),
    tags: parseJsonList(row.tags),
    raw: parseJsonObject(row.raw),
  }
}
