export interface FilterOption {
  value: string
  label: string
  keywords: readonly string[]
}

function option(value: string, label: string, ...keywords: string[]): FilterOption {
  return { value, label, keywords }
}

export const CUISINE_OPTIONS: readonly FilterOption[] = [
  option("american", "American", "american", "southern", "bbq", "barbecue", "tex-mex", "comfort food"),
  option("british", "British", "british", "english", "uk", "united kingdom", "scottish", "welsh"),
  option("chinese", "Chinese", "chinese", "szechuan", "cantonese", "dim sum", "stir-fry"),
  option("french", "French", "french", "provencal", "bistro", "bourguignon"),
  option("greek", "Greek", "greek", "souvlaki", "feta", "tzatziki", "gyro"),
  option("indian", "Indian", "indian", "curry", "masala", "tikka", "dal", "biryani"),
  option("italian", "Italian", "italian", "pasta", "risotto", "gnocchi", "antipasti"),
  option("japanese", "Japanese", "japanese", "sushi", "ramen", "teriyaki", "tempura"),
  option("mexican", "Mexican", "mexican", "taco", "enchilada", "quesadilla", "salsa"),
  option("middle_eastern", "Middle Eastern", "middle eastern", "lebanese", "turkish", "persian", "shawarma", "falafel"),
  option("spanish", "Spanish", "spanish", "paella", "tapas", "chorizo", "gazpacho"),
  option("thai", "Thai", "thai", "lemongrass", "pad thai", "green curry", "massaman"),
  option("mediterranean", "Mediterranean", "mediterranean", "mezze", "olive", "mediterranean diet"),
] as const

export const MEAL_OPTIONS: readonly FilterOption[] = [
  option("breakfast", "Breakfast", "breakfast", "brunch", "morning", "pancake", "omelette"),
  option("lunch", "Lunch", "lunch", "midday", "sandwich", "wrap", "salad"),
  option("dinner", "Dinner", "dinner", "supper", "main course", "entree", "evening meal"),
  option("starter", "Starter", "starter", "appetizer", "appetiser", "hors d'oeuvre", "snack"),
  option("dessert", "Dessert", "dessert", "pudding", "sweet", "cake", "ice cream"),
  option("drink", "Drink", "drink", "beverage", "cocktail", "smoothie", "juice"),
] as const

export const DIET_OPTIONS: readonly FilterOption[] = [
  option("vegetarian", "Vegetarian", "vegetarian", "meatless", "veggie"),
  option("vegan", "Vegan", "vegan", "plant-based", "plant based"),
  option("gluten_free", "Gluten-Free", "gluten-free", "gluten free", "coeliac"),
  option("keto", "Keto", "keto", "ketogenic", "low carb", "low-carb"),
  option("paleo", "Paleo", "paleo", "primal"),
  option("healthy", "Healthy", "healthy", "light", "wholesome", "clean eating", "low-fat", "low fat"),
] as const

function buildLookup(options: readonly FilterOption[]): Record<string, FilterOption> {
  return options.reduce<Record<string, FilterOption>>((acc, option) => {
    acc[option.value] = option
    return acc
  }, {})
}

export const CUISINE_LOOKUP = buildLookup(CUISINE_OPTIONS)
export const MEAL_LOOKUP = buildLookup(MEAL_OPTIONS)
export const DIET_LOOKUP = buildLookup(DIET_OPTIONS)

export function normalizeSelection(values: Iterable<string>, lookup: Record<string, FilterOption>): string[] {
  const normalized: string[] = []
  const seen = new Set<string>()
  for (const raw of values) {
    if (!raw) {
      continue
    }
    const candidate = String(raw).trim().toLowerCase().replace(/ |-/g, "_")
    if (candidate && lookup[candidate] && !seen.has(candidate)) {
      normalized.push(candidate)
      seen.add(candidate)
    }
  }
  return normalized
}

export function normalizedKeywords(option: FilterOption): string[] {
  return Array.from(
    new Set(option.keywords.map((keyword) => keyword.trim().toLowerCase()).filter((keyword) => keyword.length > 0)),
  ).sort()
}
