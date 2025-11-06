export function normalizeRecipeId(raw: string | string[] | undefined): number | null {
  if (raw === undefined || raw === null) {
    return null
  }

  const value = Array.isArray(raw) ? raw[raw.length - 1] : raw
  if (typeof value !== "string") {
    return null
  }

  const trimmed = value.trim()
  if (!trimmed) {
    return null
  }

  if (/^\d+$/.test(trimmed)) {
    const numeric = Number.parseInt(trimmed, 10)
    return Number.isFinite(numeric) && numeric > 0 ? numeric : null
  }

  const matches = trimmed.match(/\d+/g)
  if (!matches) {
    return null
  }

  for (let index = matches.length - 1; index >= 0; index -= 1) {
    const candidate = Number.parseInt(matches[index], 10)
    if (Number.isFinite(candidate) && candidate > 0) {
      return candidate
    }
  }

  return null
}
