"use client"

import { useMemo } from "react"
import { Clock, Users } from "lucide-react"

interface Recipe {
  id: number
  title: string
  image: string
  cookTime: number
  servings: number
  difficulty: "Easy" | "Medium" | "Hard"
  rating: number
  reviews: number
}

interface RecipeResultsProps {
  searchQuery: string
  filters: {
    cookTime: string
    servings: string
    difficulty: string
  }
  onFilterChange: (filters: any) => void
}

// Sample recipe data
const allRecipes: Recipe[] = [
  {
    id: 1,
    title: "Classic Spaghetti Carbonara",
    image: "/spaghetti-carbonara.png",
    cookTime: 20,
    servings: 4,
    difficulty: "Easy",
    rating: 4.8,
    reviews: 324,
  },
  {
    id: 2,
    title: "Thai Green Curry",
    image: "/thai-green-curry-in-bowl.jpg",
    cookTime: 35,
    servings: 4,
    difficulty: "Medium",
    rating: 4.6,
    reviews: 289,
  },
  {
    id: 3,
    title: "Chocolate Lava Cake",
    image: "/chocolate-lava-cake.png",
    cookTime: 15,
    servings: 2,
    difficulty: "Medium",
    rating: 4.9,
    reviews: 512,
  },
  {
    id: 4,
    title: "Grilled Salmon",
    image: "/grilled-salmon-with-vegetables.jpg",
    cookTime: 25,
    servings: 2,
    difficulty: "Easy",
    rating: 4.7,
    reviews: 198,
  },
  {
    id: 5,
    title: "Beef Tacos",
    image: "/beef-tacos-with-toppings.jpg",
    cookTime: 20,
    servings: 4,
    difficulty: "Easy",
    rating: 4.5,
    reviews: 445,
  },
  {
    id: 6,
    title: "Homemade Pizza",
    image: "/homemade-pizza-with-cheese.jpg",
    cookTime: 45,
    servings: 4,
    difficulty: "Hard",
    rating: 4.7,
    reviews: 267,
  },
  {
    id: 7,
    title: "Caesar Salad",
    image: "/caesar-salad-fresh-greens.jpg",
    cookTime: 10,
    servings: 2,
    difficulty: "Easy",
    rating: 4.4,
    reviews: 156,
  },
  {
    id: 8,
    title: "Beef Stew",
    image: "/beef-stew-in-bowl.jpg",
    cookTime: 120,
    servings: 6,
    difficulty: "Hard",
    rating: 4.8,
    reviews: 378,
  },
]

export default function RecipeResults({ searchQuery, filters, onFilterChange }: RecipeResultsProps) {
  const filteredRecipes = useMemo(() => {
    return allRecipes.filter((recipe) => {
      // Search filter
      const matchesSearch = searchQuery === "" || recipe.title.toLowerCase().includes(searchQuery.toLowerCase())

      // Cook time filter
      const matchesCookTime =
        filters.cookTime === "" ||
        (filters.cookTime === "quick" && recipe.cookTime <= 20) ||
        (filters.cookTime === "medium" && recipe.cookTime > 20 && recipe.cookTime <= 45) ||
        (filters.cookTime === "long" && recipe.cookTime > 45)

      // Servings filter
      const matchesServings =
        filters.servings === "" ||
        (filters.servings === "1-2" && recipe.servings <= 2) ||
        (filters.servings === "3-4" && recipe.servings >= 3 && recipe.servings <= 4) ||
        (filters.servings === "5+" && recipe.servings >= 5)

      // Difficulty filter
      const matchesDifficulty = filters.difficulty === "" || recipe.difficulty === filters.difficulty

      return matchesSearch && matchesCookTime && matchesServings && matchesDifficulty
    })
  }, [searchQuery, filters])

  if (searchQuery === "") {
    return null
  }

  return (
    <div className="bg-background min-h-screen px-4 py-12">
      <div className="max-w-7xl mx-auto">
        {/* Results header */}
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-foreground mb-2">Results for "{searchQuery}"</h2>
          <p className="text-muted-foreground">
            {filteredRecipes.length} recipe{filteredRecipes.length !== 1 ? "s" : ""} found
          </p>
        </div>

        {/* Filters */}
        <div className="mb-8 flex flex-wrap gap-4">
          <FilterSelect
            label="Cook Time"
            value={filters.cookTime}
            options={[
              { value: "", label: "All" },
              { value: "quick", label: "Quick (≤20 min)" },
              { value: "medium", label: "Medium (20-45 min)" },
              { value: "long", label: "Long (45+ min)" },
            ]}
            onChange={(value) => onFilterChange({ ...filters, cookTime: value })}
          />

          <FilterSelect
            label="Servings"
            value={filters.servings}
            options={[
              { value: "", label: "All" },
              { value: "1-2", label: "1-2" },
              { value: "3-4", label: "3-4" },
              { value: "5+", label: "5+" },
            ]}
            onChange={(value) => onFilterChange({ ...filters, servings: value })}
          />

          <FilterSelect
            label="Difficulty"
            value={filters.difficulty}
            options={[
              { value: "", label: "All" },
              { value: "Easy", label: "Easy" },
              { value: "Medium", label: "Medium" },
              { value: "Hard", label: "Hard" },
            ]}
            onChange={(value) => onFilterChange({ ...filters, difficulty: value })}
          />
        </div>

        {/* Results grid */}
        {filteredRecipes.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {filteredRecipes.map((recipe) => (
              <RecipeCard key={recipe.id} recipe={recipe} />
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <p className="text-muted-foreground text-lg">No recipes found. Try adjusting your filters.</p>
          </div>
        )}
      </div>
    </div>
  )
}

interface FilterSelectProps {
  label: string
  value: string
  options: { value: string; label: string }[]
  onChange: (value: string) => void
}

function FilterSelect({ label, value, options, onChange }: FilterSelectProps) {
  return (
    <div className="flex flex-col gap-2">
      <label className="text-sm font-medium text-foreground">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="px-4 py-2 border border-border rounded-lg bg-card text-foreground focus:ring-2 focus:ring-primary focus:border-transparent cursor-pointer"
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

interface RecipeCardProps {
  recipe: Recipe
}

function RecipeCard({ recipe }: RecipeCardProps) {
  return (
    <div className="bg-card rounded-lg overflow-hidden border border-border hover:shadow-lg transition-shadow cursor-pointer group">
      {/* Image */}
      <div className="relative h-40 bg-muted overflow-hidden">
        <img
          src={recipe.image || "/placeholder.svg"}
          alt={recipe.title}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
        />
        <div className="absolute top-2 right-2 bg-primary text-primary-foreground px-2 py-1 rounded text-sm font-medium">
          {recipe.difficulty}
        </div>
      </div>

      {/* Content */}
      <div className="p-4 space-y-3">
        <h3 className="font-semibold text-foreground line-clamp-2">{recipe.title}</h3>

        {/* Stats */}
        <div className="flex gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-1">
            <Clock className="w-4 h-4" />
            <span>{recipe.cookTime}m</span>
          </div>
          <div className="flex items-center gap-1">
            <Users className="w-4 h-4" />
            <span>{recipe.servings}</span>
          </div>
        </div>

        {/* Rating */}
        <div className="flex items-center gap-2 pt-2 border-t border-border">
          <div className="flex items-center gap-1">
            <span className="text-sm font-semibold text-foreground">{recipe.rating}</span>
            <span className="text-xs text-muted-foreground">★</span>
          </div>
          <span className="text-xs text-muted-foreground">({recipe.reviews})</span>
        </div>
      </div>
    </div>
  )
}
