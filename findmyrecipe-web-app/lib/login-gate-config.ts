const DEFAULT_CODE_EXPIRY_MINUTES = 15
const DEFAULT_SESSION_DURATION_DAYS = 30
const DEFAULT_EMAIL_SUBJECT = "Your findmyflavour login code"

export const LOGIN_GATE_COOKIE_NAME = "findmyflavour_login_token"

export type LoginGateConfig = {
  enabled: boolean
  codeExpiryMinutes: number
  sessionDurationDays: number
  emailSubject: string
  loginEmailSender: string | null
  smtpHost: string | null
  smtpPort: number | null
  smtpUser: string | null
  smtpPassword: string | null
  smtpSecure: boolean
}

function parseBoolean(value: string | undefined, fallback: boolean): boolean {
  if (value === undefined) {
    return fallback
  }

  const normalized = value.trim().toLowerCase()
  return normalized === "1" || normalized === "true" || normalized === "yes"
}

function parseInteger(value: string | undefined, fallback: number): number {
  if (!value) {
    return fallback
  }

  const parsed = Number.parseInt(value, 10)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback
}

export function resolveLoginGateConfig(): LoginGateConfig {
  const enabled = parseBoolean(process.env.TEMP_LOGIN_ENABLED, false)

  const codeExpiryMinutes = parseInteger(process.env.LOGIN_CODE_EXPIRY_MINUTES, DEFAULT_CODE_EXPIRY_MINUTES)
  const sessionDurationDays = parseInteger(
    process.env.LOGIN_SESSION_DURATION_DAYS,
    DEFAULT_SESSION_DURATION_DAYS
  )

  const emailSubject = process.env.LOGIN_EMAIL_SUBJECT?.trim() || DEFAULT_EMAIL_SUBJECT
  const loginEmailSender = process.env.LOGIN_EMAIL_SENDER?.trim() || null

  const smtpHost = process.env.SMTP_HOST?.trim() || null
  const smtpPort = process.env.SMTP_PORT ? parseInteger(process.env.SMTP_PORT, NaN) : null
  const smtpUser = process.env.SMTP_USERNAME?.trim() || null
  const smtpPassword = process.env.SMTP_PASSWORD?.trim() || null
  const smtpSecure = parseBoolean(process.env.SMTP_SECURE, true)

  return {
    enabled,
    codeExpiryMinutes,
    sessionDurationDays,
    emailSubject,
    loginEmailSender,
    smtpHost,
    smtpPort: smtpPort && Number.isFinite(smtpPort) ? smtpPort : null,
    smtpUser,
    smtpPassword,
    smtpSecure,
  }
}

export function isLoginGateEnabled(): boolean {
  return resolveLoginGateConfig().enabled
}
