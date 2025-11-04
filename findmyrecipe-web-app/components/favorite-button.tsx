"use client"

import type React from "react"
import { useState } from "react"

interface FavoriteButtonProps {
  recipeId: number
  recipeName: string
  recipeImage: string
  className?: string
  size?: "sm" | "md" | "lg"
}

export default function FavoriteButton({
  recipeId,
  recipeName,
  recipeImage,
  className = "",
  size = "md",
}: FavoriteButtonProps) {
  const [isFavorite, setIsFavorite] = useState(false)

  const handleToggleFavorite = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsFavorite(!isFavorite)
  }

  const sizeClasses = {
    sm: "w-5 h-5",
    md: "w-6 h-6",
    lg: "w-8 h-8",
  }

  return (
    <button
      onClick={handleToggleFavorite}
      className={`transition-colors ${className}`}
      aria-label={isFavorite ? "Remove from favorites" : "Add to favorites"}
    >
      {/* Heart icon using inline SVG */}
      <svg
        className={`${sizeClasses[size]} ${
          isFavorite ? "fill-red-500 text-red-500" : "text-muted-foreground hover:text-red-500"
        } transition-colors`}
        fill={isFavorite ? "currentColor" : "none"}
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"
        />
      </svg>
    </button>
  )
}
