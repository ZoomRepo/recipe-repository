import { NextRequest, NextResponse } from "next/server"
import { fetchRecipes } from "@/lib/recipes-repository"

export const dynamic = "force-dynamic"

export async function GET(request: NextRequest) {
  try {
    const result = await fetchRecipes(
      request.nextUrl.searchParams,
      request.headers.get("authorization"),
      request.headers.get("cookie"),
      request.headers.get("x-api-token"),
    )
    const response = NextResponse.json({
      items: result.items,
      pagination: {
        page: result.page,
        pageSize: result.pageSize,
        total: result.total,
        totalPages: result.totalPages,
      },
      filters: result.filters,
      searchBackend: result.searchBackend,
    })
    if (result.searchBackend) {
      response.headers.set("X-Search-Backend", result.searchBackend)
    }
    return response
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unable to load recipes"
    const status = (error as { status?: number }).status ?? 502
    console.error("Failed to load recipes", error)
    return NextResponse.json({ error: message }, { status })
  }
}
