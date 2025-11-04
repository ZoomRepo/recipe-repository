"use client"

import { useState, useEffect } from "react"
import { createClient } from "@/lib/supabase/client"
import { Heart, X } from "lucide-react"
import Link from "next/link"

interface Favorite {
  id: string
  recipe_id: string
  recipe_name: string
  recipe_image: string
}

export default function FavoritesList() {
  const [favorites, setFavorites] = useState<Favorite[]>([])
  const [isOpen, setIsOpen] = useState(false)
  const [user, setUser] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const checkUser = async () => {
      try {
        const supabase = createClient()
        const {
          data: { user },
        } = await supabase.auth.getUser()
        setUser(user)
      } catch (error) {
        console.log("[v0] Error checking user:", error)
      }
      setIsLoading(false)
    }

    checkUser()
  }, [])

  useEffect(() => {
    const loadFavorites = async () => {
      if (!user || !isOpen) return

      try {
        const supabase = createClient()
        const { data } = await supabase
          .from("favorites")
          .select("*")
          .eq("user_id", user.id)
          .order("created_at", { ascending: false })

        setFavorites(data || [])
      } catch (error) {
        console.log("[v0] Error loading favorites:", error)
      }
    }

    loadFavorites()
  }, [isOpen, user])

  const handleRemoveFavorite = async (favoriteId: string) => {
    try {
      const supabase = createClient()
      await supabase.from("favorites").delete().eq("id", favoriteId)
      setFavorites(favorites.filter((fav) => fav.id !== favoriteId))
    } catch (error) {
      console.log("[v0] Error removing favorite:", error)
    }
  }

  if (isLoading || !user) return null

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 hover:bg-secondary rounded-lg transition-colors"
        aria-label="View favorites"
      >
        <Heart className={`w-5 h-5 ${favorites.length > 0 ? "fill-red-500 text-red-500" : "text-foreground"}`} />
        {favorites.length > 0 && (
          <span className="absolute top-0 right-0 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
            {favorites.length}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-card border border-border rounded-lg shadow-lg z-50">
          <div className="p-4 border-b border-border flex items-center justify-between">
            <h3 className="font-semibold text-foreground">My Favorites</h3>
            <button onClick={() => setIsOpen(false)} className="text-muted-foreground hover:text-foreground">
              <X className="w-5 h-5" />
            </button>
          </div>

          {favorites.length > 0 ? (
            <div className="max-h-96 overflow-y-auto">
              {favorites.map((favorite) => (
                <Link key={favorite.id} href={`/recipe/${favorite.recipe_id}`}>
                  <div
                    className="p-3 border-b border-border hover:bg-secondary transition-colors flex items-center gap-3"
                    onClick={() => setIsOpen(false)}
                  >
                    {favorite.recipe_image && (
                      <img
                        src={favorite.recipe_image || "/placeholder.svg"}
                        alt={favorite.recipe_name}
                        className="w-12 h-12 rounded object-cover"
                      />
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-foreground line-clamp-2">{favorite.recipe_name}</p>
                    </div>
                    <button
                      onClick={(e) => {
                        e.preventDefault()
                        e.stopPropagation()
                        handleRemoveFavorite(favorite.id)
                      }}
                      className="text-muted-foreground hover:text-red-500 transition-colors"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="p-8 text-center text-muted-foreground">
              <p>No favorites yet. Start adding recipes!</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
