import { NextRequest, NextResponse } from "next/server"
import { fetchRecipes } from "@/lib/recipes-repository"

export const dynamic = "force-dynamic"

export async function GET(request: NextRequest) {
  try {
    const result = await fetchRecipes(request.nextUrl.searchParams)
    return NextResponse.json({
      items: result.items,
      pagination: {
        page: result.page,
        pageSize: result.pageSize,
        total: result.total,
        totalPages: result.totalPages,
      },
      filters: result.filters,
    })
  } catch (error) {
    console.error("Failed to load recipes", error)
    return NextResponse.json({ error: "Unable to load recipes" }, { status: 500 })
  }
}
