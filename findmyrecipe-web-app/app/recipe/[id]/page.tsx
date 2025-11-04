"use client"

import type React from "react"
import Link from "next/link"
import { useParams } from "next/navigation"
import SubscriptionGate from "@/components/subscription-gate"

// Recipe data with full details
const recipeDatabase: Record<number, any> = {
  1: {
    id: 1,
    title: "Classic Spaghetti Carbonara",
    image: "/spaghetti-carbonara.png",
    cookTime: 20,
    servings: 4,
    difficulty: "Easy",
    rating: 4.8,
    reviews: 324,
    description: "An authentic Italian pasta dish with a creamy sauce made from eggs, cheese, and pancetta.",
    ingredients: [
      "1 lb spaghetti",
      "6 oz pancetta or bacon, diced",
      "4 large eggs",
      "2 cups Parmesan cheese, grated",
      "2 cloves garlic, minced",
      "Salt and black pepper to taste",
      "Fresh parsley for garnish",
    ],
    instructions: [
      "Bring a large pot of salted water to boil and cook spaghetti according to package directions.",
      "While pasta cooks, fry pancetta in a large skillet until crispy. Remove and set aside.",
      "In a bowl, whisk together eggs and Parmesan cheese.",
      "Drain pasta, reserving 1 cup of pasta water.",
      "Add hot pasta to the pancetta pan (off heat), then quickly stir in egg mixture.",
      "Toss constantly, adding pasta water as needed to create a creamy sauce.",
      "Season with salt and pepper, then serve with fresh parsley.",
    ],
    tips: [
      "Don't let the eggs scramble - work quickly off the heat",
      "Reserve pasta water to adjust sauce consistency",
      "Use real Parmesan cheese for best results",
    ],
  },
  2: {
    id: 2,
    title: "Thai Green Curry",
    image: "/thai-green-curry-in-bowl.jpg",
    cookTime: 35,
    servings: 4,
    difficulty: "Medium",
    rating: 4.6,
    reviews: 289,
    description: "A fragrant and spicy Thai green curry with vegetables and coconut milk.",
    ingredients: [
      "2 tbsp green curry paste",
      "1 can (14 oz) coconut milk",
      "1 lb chicken breast, sliced",
      "2 cups mixed vegetables (bell peppers, zucchini, bamboo shoots)",
      "3 cloves garlic, minced",
      "1 tbsp fish sauce",
      "1 tbsp lime juice",
      "Fresh basil leaves",
      "1 tbsp vegetable oil",
    ],
    instructions: [
      "Heat oil in a large pan and sauté curry paste for 1-2 minutes until fragrant.",
      "Add sliced chicken and cook until no longer pink, about 5-7 minutes.",
      "Pour in coconut milk and bring to a simmer.",
      "Add vegetables and simmer for 15-20 minutes until tender.",
      "Season with fish sauce and lime juice.",
      "Top with fresh basil and serve over rice.",
    ],
    tips: [
      "Adjust curry paste amount based on spice preference",
      "Don't overcook vegetables - they should be tender-crisp",
      "Serve with jasmine rice or noodles",
    ],
  },
  3: {
    id: 3,
    title: "Chocolate Lava Cake",
    image: "/chocolate-lava-cake.png",
    cookTime: 15,
    servings: 2,
    difficulty: "Medium",
    rating: 4.9,
    reviews: 512,
    description: "A rich chocolate cake with a gooey molten center - the perfect dessert.",
    ingredients: [
      "4 oz dark chocolate, chopped",
      "4 oz butter",
      "2 large eggs",
      "2 tbsp sugar",
      "2 tbsp flour",
      "Pinch of salt",
      "Butter and cocoa powder for ramekins",
    ],
    instructions: [
      "Preheat oven to 425°F and grease two ramekins with butter and cocoa powder.",
      "Melt chocolate and butter together over low heat.",
      "Whisk eggs with sugar until pale and fluffy.",
      "Fold melted chocolate into egg mixture.",
      "Gently fold in flour and salt.",
      "Divide batter between ramekins.",
      "Bake for 12-14 minutes until edges are firm but center jiggles slightly.",
      "Invert onto plates and serve immediately with ice cream.",
    ],
    tips: [
      "Don't overbake - center should be slightly underdone",
      "Prepare ramekins ahead of time for quick assembly",
      "Serve with vanilla ice cream or whipped cream",
    ],
  },
  4: {
    id: 4,
    title: "Grilled Salmon",
    image: "/grilled-salmon-with-vegetables.jpg",
    cookTime: 25,
    servings: 2,
    difficulty: "Easy",
    rating: 4.7,
    reviews: 198,
    description: "Perfectly grilled salmon with roasted vegetables - simple, healthy, and delicious.",
    ingredients: [
      "2 salmon fillets (6 oz each)",
      "2 tbsp olive oil",
      "1 lemon, sliced",
      "2 cups mixed vegetables (asparagus, bell peppers, zucchini)",
      "3 cloves garlic, minced",
      "Salt, pepper, and fresh dill",
    ],
    instructions: [
      "Preheat grill to medium-high heat.",
      "Toss vegetables with 1 tbsp olive oil, garlic, salt, and pepper.",
      "Place vegetables on grill and cook for 15 minutes, stirring occasionally.",
      "Brush salmon with remaining oil and season with salt, pepper, and dill.",
      "Place salmon on grill for 8-10 minutes until cooked through.",
      "Serve salmon with grilled vegetables and lemon slices.",
    ],
    tips: [
      "Don't flip salmon too often - once is enough",
      "Vegetables can be prepared ahead of time",
      "Use a fish spatula for easier handling",
    ],
  },
  5: {
    id: 5,
    title: "Beef Tacos",
    image: "/beef-tacos-with-toppings.jpg",
    cookTime: 20,
    servings: 4,
    difficulty: "Easy",
    rating: 4.5,
    reviews: 445,
    description: "Classic beef tacos with all the fixings - a crowd-pleaser for any occasion.",
    ingredients: [
      "1 lb ground beef",
      "8 taco shells or tortillas",
      "2 tbsp taco seasoning",
      "1 cup shredded lettuce",
      "1 cup diced tomatoes",
      "1 cup shredded cheese",
      "1/2 cup sour cream",
      "1/2 cup salsa",
    ],
    instructions: [
      "Brown ground beef in a skillet over medium heat, breaking it up as it cooks.",
      "Drain excess fat and add taco seasoning with 1/4 cup water.",
      "Simmer for 5 minutes until sauce thickens.",
      "Warm taco shells according to package directions.",
      "Assemble tacos with beef and desired toppings.",
      "Serve with salsa and sour cream on the side.",
    ],
    tips: [
      "Toast tortillas lightly for better flavor",
      "Prep all toppings before cooking beef",
      "Make it vegetarian by using seasoned black beans instead of beef",
    ],
  },
  6: {
    id: 6,
    title: "Homemade Pizza",
    image: "/homemade-pizza-with-cheese.jpg",
    cookTime: 45,
    servings: 4,
    difficulty: "Hard",
    rating: 4.7,
    reviews: 267,
    description: "Make your own pizza from scratch with homemade dough and fresh toppings.",
    ingredients: [
      "3 cups all-purpose flour",
      "1 packet instant yeast",
      "1 tsp salt",
      "1 tbsp sugar",
      "1 tbsp olive oil",
      "1 cup warm water",
      "1 cup pizza sauce",
      "2 cups mozzarella cheese",
      "Toppings of choice",
    ],
    instructions: [
      "Combine flour, yeast, salt, and sugar in a large bowl.",
      "Add olive oil and warm water, mix until dough forms.",
      "Knead for 10 minutes until smooth and elastic.",
      "Let dough rise for 1 hour until doubled in size.",
      "Preheat oven to 475°F.",
      "Stretch dough onto a baking sheet.",
      "Spread sauce and add toppings.",
      "Bake for 12-15 minutes until crust is golden and cheese is bubbly.",
    ],
    tips: [
      "Let dough rise in a warm, draft-free place",
      "Don't overload pizza with toppings",
      "Use a pizza stone for crispier crust",
    ],
  },
  7: {
    id: 7,
    title: "Caesar Salad",
    image: "/caesar-salad-fresh-greens.jpg",
    cookTime: 10,
    servings: 2,
    difficulty: "Easy",
    rating: 4.4,
    reviews: 156,
    description: "A classic Caesar salad with crisp romaine and homemade dressing.",
    ingredients: [
      "2 heads romaine lettuce",
      "1/2 cup Parmesan cheese, shaved",
      "1 cup croutons",
      "3 anchovy fillets",
      "3 cloves garlic",
      "1/4 cup olive oil",
      "2 tbsp lemon juice",
      "1 tsp Dijon mustard",
      "Salt and pepper",
    ],
    instructions: [
      "Wash and dry romaine lettuce, then chop into bite-sized pieces.",
      "Make dressing by blending anchovies, garlic, mustard, and lemon juice.",
      "Slowly add olive oil while blending until emulsified.",
      "Toss lettuce with dressing.",
      "Top with Parmesan shavings and croutons.",
      "Serve immediately.",
    ],
    tips: [
      "Make dressing fresh for best flavor",
      "Anchovies are optional but authentic",
      "Can be made vegan by omitting anchovies and using nutritional yeast",
    ],
  },
  8: {
    id: 8,
    title: "Beef Stew",
    image: "/beef-stew-in-bowl.jpg",
    cookTime: 120,
    servings: 6,
    difficulty: "Hard",
    rating: 4.8,
    reviews: 378,
    description: "A hearty, slow-cooked beef stew loaded with vegetables and tender meat.",
    ingredients: [
      "2 lbs beef chuck, cubed",
      "3 tbsp olive oil",
      "3 cloves garlic, minced",
      "2 tbsp tomato paste",
      "2 cups beef broth",
      "1 cup red wine",
      "3 medium potatoes, cubed",
      "3 carrots, sliced",
      "1 large onion, diced",
      "2 bay leaves",
      "Fresh thyme",
    ],
    instructions: [
      "Heat oil in a large pot and brown beef in batches.",
      "Remove beef and set aside.",
      "Sauté onion and garlic until fragrant.",
      "Add tomato paste and cook for 1 minute.",
      "Return beef to pot with broth, wine, bay leaves, and thyme.",
      "Bring to simmer and cook for 1.5 hours.",
      "Add potatoes and carrots, then simmer for another 30 minutes.",
      "Season with salt and pepper, then serve.",
    ],
    tips: [
      "Use chuck steak for tender results",
      "The longer it cooks, the more flavorful it becomes",
      "Can be made in a slow cooker on low for 8 hours",
    ],
  },
}

export default function RecipePage() {
  const params = useParams()
  const id = typeof params.id === "string" ? Number.parseInt(params.id) : 1

  const recipe = recipeDatabase[id]

  if (!recipe) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-foreground mb-4">Recipe Not Found</h1>
          <Link href="/results" className="text-primary hover:underline">
            ← Back to Results
          </Link>
        </div>
      </div>
    )
  }

  return (
    <SubscriptionGate recipeId={recipe.id} recipeName={recipe.title}>
      <RecipeContent recipe={recipe} />
    </SubscriptionGate>
  )
}

function RecipeContent({ recipe }: { recipe: any }) {
  return (
    <div className="min-h-screen bg-background">
      {/* Header Navigation */}
      <div className="sticky top-0 z-50 bg-white border-b border-border shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/results" className="flex items-center gap-2 text-primary hover:underline font-medium">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Results
          </Link>
          <button className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8.684 13.342C8.886 12.938 9 12.469 9 12c0-3.314-2.686-6-6-6s-6 2.686-6 6 2.686 6 6 6c.469 0 .938-.114 1.342-.316m9.618-9.618a9 9 0 112.828 2.828m0 0l-3.536 3.536m3.536-3.536L9 9"
              />
            </svg>
            Share
          </button>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 py-12">
        {/* Recipe Header */}
        <div className="mb-8 space-y-6">
          <div>
            <h1 className="text-4xl font-bold text-foreground mb-3">{recipe.title}</h1>
            <p className="text-lg text-muted-foreground">{recipe.description}</p>
          </div>

          {/* Image */}
          <div className="relative rounded-lg overflow-hidden h-96 bg-muted">
            <img src={recipe.image || "/placeholder.svg"} alt={recipe.title} className="w-full h-full object-cover" />
            <div className="absolute top-4 right-4 bg-primary text-primary-foreground px-4 py-2 rounded-lg font-semibold">
              {recipe.difficulty}
            </div>
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard
              icon={
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              }
              label="Cook Time"
              value={`${recipe.cookTime} min`}
            />
            <StatCard
              icon={
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M17 20h5v-2a3 3 0 00-5.856-1.487M15 10a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                </svg>
              }
              label="Servings"
              value={recipe.servings}
            />
            <StatCard
              icon={
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192l-3.536 3.536M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-5 0a4 4 0 11-8 0 4 4 0 018 0z"
                  />
                </svg>
              }
              label="Difficulty"
              value={recipe.difficulty}
            />
            <StatCard
              icon={<span className="text-xl">★</span>}
              label="Rating"
              value={`${recipe.rating} (${recipe.reviews})`}
            />
          </div>
        </div>

        {/* Ingredients & Instructions */}
        <div className="grid md:grid-cols-3 gap-8 mb-12">
          {/* Ingredients */}
          <div className="md:col-span-1">
            <h2 className="text-2xl font-bold text-foreground mb-4">Ingredients</h2>
            <ul className="space-y-3">
              {recipe.ingredients.map((ingredient: string, index: number) => (
                <li key={index} className="flex gap-3">
                  <input type="checkbox" className="w-5 h-5 rounded border-border text-primary" />
                  <span className="text-foreground">{ingredient}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Instructions */}
          <div className="md:col-span-2">
            <h2 className="text-2xl font-bold text-foreground mb-4">Instructions</h2>
            <ol className="space-y-4">
              {recipe.instructions.map((instruction: string, index: number) => (
                <li key={index} className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 bg-primary text-primary-foreground rounded-full flex items-center justify-center font-semibold">
                    {index + 1}
                  </div>
                  <p className="text-foreground pt-1">{instruction}</p>
                </li>
              ))}
            </ol>
          </div>
        </div>

        {/* Tips */}
        <div className="bg-card border border-border rounded-lg p-6 mb-12">
          <h2 className="text-2xl font-bold text-foreground mb-4">Chef's Tips</h2>
          <ul className="space-y-2">
            {recipe.tips.map((tip: string, index: number) => (
              <li key={index} className="flex gap-3 text-foreground">
                <span className="text-primary font-bold">•</span>
                {tip}
              </li>
            ))}
          </ul>
        </div>
      </main>
    </div>
  )
}

interface StatCardProps {
  icon: React.ReactNode
  label: string
  value: string | number
}

function StatCard({ icon, label, value }: StatCardProps) {
  return (
    <div className="bg-card border border-border rounded-lg p-4 text-center">
      <div className="flex justify-center mb-2 text-primary">{icon}</div>
      <p className="text-sm text-muted-foreground mb-1">{label}</p>
      <p className="font-semibold text-foreground text-lg">{value}</p>
    </div>
  )
}
