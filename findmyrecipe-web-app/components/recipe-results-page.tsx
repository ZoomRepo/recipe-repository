"use client"

import { useMemo, useState } from "react"
import Link from "next/link"
import FavoriteButton from "./favorite-button"

interface Recipe {
  id: number
  title: string
  image: string
  cookTime: number
  servings: number
  difficulty: "Easy" | "Medium" | "Hard"
  rating: number
  reviews: number
  cuisine: string
  ingredients: string[]
  nutrition: {
    calories: number
    protein: number
    carbs: number
    fat: number
  }
}

interface RecipeResultsPageProps {
  searchQuery: string
  filters: {
    cookTime: string
    servings: string
    difficulty: string
    cuisine: string
  }
  onFilterChange: (filters: any) => void
}

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
    cuisine: "Italian",
    ingredients: ["400g spaghetti", "200g guanciale", "4 egg yolks", "100g Pecorino Romano", "Black pepper"],
    nutrition: { calories: 520, protein: 18, carbs: 62, fat: 22 },
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
    cuisine: "Thai",
    ingredients: ["500g chicken", "2 tbsp green curry paste", "400ml coconut milk", "Thai basil", "Lime"],
    nutrition: { calories: 380, protein: 28, carbs: 8, fat: 28 },
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
    cuisine: "French",
    ingredients: ["200g dark chocolate", "100g butter", "2 eggs", "2 tbsp sugar", "Flour"],
    nutrition: { calories: 680, protein: 8, carbs: 58, fat: 48 },
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
    cuisine: "Scandinavian",
    ingredients: ["400g salmon fillet", "Lemon", "Dill", "Olive oil", "Salt & pepper"],
    nutrition: { calories: 420, protein: 42, carbs: 2, fat: 28 },
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
    cuisine: "Mexican",
    ingredients: ["500g ground beef", "8 taco shells", "Lettuce", "Tomato", "Cheddar cheese"],
    nutrition: { calories: 450, protein: 32, carbs: 35, fat: 24 },
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
    cuisine: "Italian",
    ingredients: ["500g flour", "Yeast", "Mozzarella", "Tomato sauce", "Basil"],
    nutrition: { calories: 380, protein: 14, carbs: 58, fat: 10 },
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
    cuisine: "American",
    ingredients: ["Romaine lettuce", "Parmesan cheese", "Croutons", "Caesar dressing", "Anchovies"],
    nutrition: { calories: 240, protein: 12, carbs: 15, fat: 16 },
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
    cuisine: "British",
    ingredients: ["800g beef", "Potatoes", "Carrots", "Celery", "Beef broth"],
    nutrition: { calories: 320, protein: 28, carbs: 22, fat: 14 },
  },
]

export default function RecipeResultsPage({ searchQuery, filters, onFilterChange }: RecipeResultsPageProps) {
  const [expandedRecipe, setExpandedRecipe] = useState<number | null>(null)

  const filteredRecipes = useMemo(() => {
    return allRecipes.filter((recipe) => {
      const matchesSearch = searchQuery === "" || recipe.title.toLowerCase().includes(searchQuery.toLowerCase())
      const matchesCookTime =
        filters.cookTime === "" ||
        (filters.cookTime === "quick" && recipe.cookTime <= 20) ||
        (filters.cookTime === "medium" && recipe.cookTime > 20 && recipe.cookTime <= 45) ||
        (filters.cookTime === "long" && recipe.cookTime > 45)
      const matchesServings =
        filters.servings === "" ||
        (filters.servings === "1-2" && recipe.servings <= 2) ||
        (filters.servings === "3-4" && recipe.servings >= 3 && recipe.servings <= 4) ||
        (filters.servings === "5+" && recipe.servings >= 5)
      const matchesDifficulty = filters.difficulty === "" || recipe.difficulty === filters.difficulty
      const matchesCuisine = filters.cuisine === "" || recipe.cuisine === filters.cuisine

      return matchesSearch && matchesCookTime && matchesServings && matchesDifficulty && matchesCuisine
    })
  }, [searchQuery, filters])

  return (
    <div className="bg-background min-h-screen px-4 py-12">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-foreground mb-2">Results for "{searchQuery}"</h2>
          <p className="text-muted-foreground">
            {filteredRecipes.length} recipe{filteredRecipes.length !== 1 ? "s" : ""} found
          </p>
        </div>

        <div className="mb-8 flex flex-wrap gap-4">
          <FilterSelect
            label="Cuisine"
            value={filters.cuisine}
            options={[
              { value: "", label: "All" },
              { value: "Italian", label: "Italian" },
              { value: "Thai", label: "Thai" },
              { value: "French", label: "French" },
              { value: "Mexican", label: "Mexican" },
              { value: "American", label: "American" },
              { value: "Scandinavian", label: "Scandinavian" },
              { value: "British", label: "British" },
            ]}
            onChange={(value) => onFilterChange({ ...filters, cuisine: value })}
          />

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

        {filteredRecipes.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {filteredRecipes.map((recipe) => (
              <div key={recipe.id}>
                <Link href={`/recipe/${recipe.id}`}>
                  <div
                    className="bg-card rounded-lg overflow-hidden border border-border hover:shadow-lg transition-shadow cursor-pointer group h-full"
                    onMouseEnter={() => setExpandedRecipe(recipe.id)}
                    onMouseLeave={() => setExpandedRecipe(null)}
                  >
                    <div className="relative h-40 bg-muted overflow-hidden">
                      {expandedRecipe === recipe.id ? (
                        <div className="w-full h-full p-3 bg-gradient-to-b from-background/80 to-background/95 flex flex-col gap-2 overflow-y-auto">
                          <div>
                            <h4 className="font-semibold text-foreground text-xs mb-1">Ingredients</h4>
                            <p className="text-xs text-muted-foreground line-clamp-3">
                              {recipe.ingredients.slice(0, 3).join(", ")}
                              {recipe.ingredients.length > 3 && ` +${recipe.ingredients.length - 3} more`}
                            </p>
                          </div>
                          <div className="border-t border-border pt-2">
                            <h4 className="font-semibold text-foreground text-xs mb-1">Nutrition</h4>
                            <p className="text-xs text-muted-foreground">
                              {recipe.nutrition.calories} cal, {recipe.nutrition.protein}g protein,{" "}
                              {recipe.nutrition.carbs}g carbs, {recipe.nutrition.fat}g fat
                            </p>
                          </div>
                        </div>
                      ) : (
                        <>
                          <img
                            src={recipe.image || "/placeholder.svg"}
                            alt={recipe.title}
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                          />
                          <div className="absolute top-2 right-2 bg-primary text-primary-foreground px-2 py-1 rounded text-sm font-medium">
                            {recipe.difficulty}
                          </div>
                          <div className="absolute top-2 left-2 bg-background/80 backdrop-blur-sm rounded-full p-2 hover:bg-background transition-colors">
                            <FavoriteButton
                              recipeId={recipe.id}
                              recipeName={recipe.title}
                              recipeImage={recipe.image}
                              size="md"
                            />
                          </div>
                        </>
                      )}
                    </div>

                    <div className="p-4 space-y-3">
                      <h3 className="font-semibold text-foreground line-clamp-2">{recipe.title}</h3>

                      <div className="flex gap-4 text-sm text-muted-foreground">
                        <div className="flex items-center gap-1">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M12 8v4l3 2m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                            />
                          </svg>
                          <span>{recipe.cookTime}m</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M12 4.354a4 4 0 110 5.292M15 12H9m6 0a9 9 0 11-18 0 9 9 0 0118 0z"
                            />
                          </svg>
                          <span>{recipe.servings}</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 pt-2 border-t border-border">
                        <div className="flex items-center gap-1">
                          <span className="text-sm font-semibold text-foreground">{recipe.rating}</span>
                          <span className="text-xs text-muted-foreground">★</span>
                        </div>
                        <span className="text-xs text-muted-foreground">({recipe.reviews})</span>
                      </div>
                    </div>
                  </div>
                </Link>
              </div>
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
