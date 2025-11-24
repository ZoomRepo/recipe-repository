import { NextRequest, NextResponse } from "next/server"
import { fetchRecipeDetail } from "@/lib/recipes-repository"
import { normalizeRecipeId } from "@/lib/recipe-id"

export const dynamic = "force-dynamic"

type RouteContext = {
  params: { id: string | string[] }
}

export async function GET(request: NextRequest, context: RouteContext) {
  try {
    const params = await(context.params)
    const id = normalizeRecipeId(params.id)
    if (id === null) {
      return NextResponse.json({ error: "Invalid recipe identifier" }, { status: 400 })
    }
    const recipe = await fetchRecipeDetail(
      id,
      request.headers.get("authorization"),
      request.headers.get("cookie"),
    )
    if (!recipe) {
      return NextResponse.json({ error: "Recipe not found" }, { status: 404 })
    }
    return NextResponse.json(recipe)
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unable to load recipe"
    const status = (error as { status?: number }).status ?? 500
    console.error("Failed to load recipe", error)
    return NextResponse.json({ error: message }, { status })
  }
}
