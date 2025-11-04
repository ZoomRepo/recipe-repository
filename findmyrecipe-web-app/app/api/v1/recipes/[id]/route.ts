import { NextRequest, NextResponse } from "next/server"
import { fetchRecipeDetail } from "@/lib/recipes-repository"

export const dynamic = "force-dynamic"

type RouteContext = {
  params: { id: string }
}

export async function GET(_: NextRequest, context: RouteContext) {
  try {
    const id = Number.parseInt(context.params.id, 10)
    if (!Number.isFinite(id) || id <= 0) {
      return NextResponse.json({ error: "Invalid recipe identifier" }, { status: 400 })
    }
    const recipe = await fetchRecipeDetail(id)
    if (!recipe) {
      return NextResponse.json({ error: "Recipe not found" }, { status: 404 })
    }
    return NextResponse.json(recipe)
  } catch (error) {
    console.error("Failed to load recipe", error)
    return NextResponse.json({ error: "Unable to load recipe" }, { status: 500 })
  }
}
