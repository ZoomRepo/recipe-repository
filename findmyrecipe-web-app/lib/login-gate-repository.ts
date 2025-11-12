import { Buffer } from "buffer"
import { createHash, randomBytes, timingSafeEqual } from "crypto"
import type { ResultSetHeader, RowDataPacket } from "mysql2/promise"

import { getPool } from "./database"

let hasEnsuredTables = false

async function ensureLoginGateTables() {
  if (hasEnsuredTables) {
    return getPool()
  }

  const pool = getPool()

  await pool.query(`
    CREATE TABLE IF NOT EXISTS login_whitelist (
      id INT UNSIGNED NOT NULL AUTO_INCREMENT,
      email VARCHAR(320) NOT NULL,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (id),
      UNIQUE KEY uniq_login_whitelist_email (email)
    )
    ENGINE=InnoDB
    DEFAULT CHARSET = utf8mb4
    COLLATE = utf8mb4_unicode_ci
  `)

  await pool.query(`
    CREATE TABLE IF NOT EXISTS login_codes (
      id INT UNSIGNED NOT NULL AUTO_INCREMENT,
      email VARCHAR(320) NOT NULL,
      code_hash CHAR(64) NOT NULL,
      expires_at DATETIME NOT NULL,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (id),
      UNIQUE KEY uniq_login_codes_email (email),
      KEY idx_login_codes_expires_at (expires_at)
    )
    ENGINE=InnoDB
    DEFAULT CHARSET = utf8mb4
    COLLATE = utf8mb4_unicode_ci
  `)

  await pool.query(`
    CREATE TABLE IF NOT EXISTS login_sessions (
      id INT UNSIGNED NOT NULL AUTO_INCREMENT,
      email VARCHAR(320) NOT NULL,
      session_code_hash CHAR(64) DEFAULT NULL,
      session_token_hash CHAR(64) DEFAULT NULL,
      expires_at DATETIME NOT NULL,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      PRIMARY KEY (id),
      UNIQUE KEY uniq_login_sessions_email (email),
      UNIQUE KEY uniq_login_sessions_code_hash (session_code_hash),
      UNIQUE KEY uniq_login_sessions_token_hash (session_token_hash),
      KEY idx_login_sessions_expires_at (expires_at)
    )
    ENGINE=InnoDB
    DEFAULT CHARSET = utf8mb4
    COLLATE = utf8mb4_unicode_ci
  `)

  // Ensure legacy tables receive the token hash column and nullable code hash if they
  // were created before the structure change above. Individual ALTER statements are
  // wrapped in try/catch blocks so repeated deployments do not fail once the schema
  // is up to date.
  try {
    await pool.query(`
      ALTER TABLE login_sessions
      MODIFY COLUMN session_code_hash CHAR(64) DEFAULT NULL
    `)
  } catch (error) {
    // Column already nullable – ignore.
  }

  try {
    await pool.query(`
      ALTER TABLE login_sessions
      ADD COLUMN session_token_hash CHAR(64) DEFAULT NULL AFTER session_code_hash
    `)
  } catch (error) {
    // Column already exists – ignore.
  }

  try {
    await pool.query(`
      ALTER TABLE login_sessions
      ADD UNIQUE KEY uniq_login_sessions_token_hash (session_token_hash)
    `)
  } catch (error) {
    // Index already exists – ignore.
  }

  hasEnsuredTables = true
  return pool
}

function normalizeEmail(email: string): string {
  return email.trim().toLowerCase()
}

type WhitelistRow = RowDataPacket & {
  email: string
  created_at: Date
}

type LoginCodeRow = RowDataPacket & {
  email: string
  code_hash: string
  expires_at: Date
}

type LoginSessionRow = RowDataPacket & {
  email: string
  session_code_hash: string | null
  session_token_hash: string | null
  expires_at: Date
}

export async function listWhitelistedEmails(): Promise<string[]> {
  const pool = await ensureLoginGateTables()
  const [rows] = await pool.query<WhitelistRow[]>(
    "SELECT email, created_at FROM login_whitelist ORDER BY created_at DESC"
  )
  return rows.map((row) => row.email)
}

export async function addEmailToWhitelist(email: string): Promise<void> {
  const pool = await ensureLoginGateTables()
  const normalizedEmail = normalizeEmail(email)

  await pool.execute<ResultSetHeader>(
    "INSERT IGNORE INTO login_whitelist (email, created_at) VALUES (?, NOW())",
    [normalizedEmail]
  )
}

export async function removeEmailFromWhitelist(email: string): Promise<void> {
  const pool = await ensureLoginGateTables()
  const normalizedEmail = normalizeEmail(email)

  await pool.execute<ResultSetHeader>(
    "DELETE FROM login_whitelist WHERE email = ?",
    [normalizedEmail]
  )
}

export async function isEmailWhitelisted(email: string): Promise<boolean> {
  const pool = await ensureLoginGateTables()
  const normalizedEmail = normalizeEmail(email)

  const [rows] = await pool.query<WhitelistRow[]>(
    "SELECT email FROM login_whitelist WHERE email = ? LIMIT 1",
    [normalizedEmail]
  )

  return rows.length > 0
}

export function generateLoginCode(): string {
  const code = Math.floor(Math.random() * 1_000_000)
  return code.toString().padStart(6, "0")
}

export function hashLoginCode(code: string): string {
  return createHash("sha256").update(code).digest("hex")
}

function generateRandomHex(bytes: number): string {
  return randomBytes(bytes).toString("hex")
}

export async function storeLoginCode(email: string, code: string, expiresAt: Date): Promise<void> {
  const pool = await ensureLoginGateTables()
  const normalizedEmail = normalizeEmail(email)
  const codeHash = hashLoginCode(code)

  await pool.execute<ResultSetHeader>(
    `
      INSERT INTO login_codes (email, code_hash, expires_at, created_at)
      VALUES (?, ?, ?, NOW())
      ON DUPLICATE KEY UPDATE code_hash = VALUES(code_hash), expires_at = VALUES(expires_at), created_at = NOW()
    `,
    [normalizedEmail, codeHash, expiresAt]
  )
}

export async function hasActiveLoginSession(email: string): Promise<boolean> {
  const pool = await ensureLoginGateTables()
  const normalizedEmail = normalizeEmail(email)

  const [rows] = await pool.query<LoginSessionRow[]>(
    "SELECT expires_at, session_token_hash FROM login_sessions WHERE email = ? LIMIT 1",
    [normalizedEmail]
  )

  if (rows.length === 0) {
    return false
  }

  const row = rows[0]
  const now = new Date()

  if (row.expires_at <= now) {
    await pool.execute<ResultSetHeader>("DELETE FROM login_sessions WHERE email = ?", [normalizedEmail])
    return false
  }

  return typeof row.session_token_hash === "string" && row.session_token_hash.length > 0
}

export async function getLoginSessionByToken(
  token: string
): Promise<{ email: string; expiresAt: Date } | null> {
  const pool = await ensureLoginGateTables()
  const tokenHash = hashLoginCode(token)

  const [rows] = await pool.query<LoginSessionRow[]>(
    "SELECT email, session_token_hash, expires_at FROM login_sessions WHERE session_token_hash = ? LIMIT 1",
    [tokenHash]
  )

  if (rows.length === 0) {
    return null
  }

  const row = rows[0]
  const now = new Date()

  if (row.expires_at <= now) {
    await pool.execute<ResultSetHeader>(
      "DELETE FROM login_sessions WHERE session_token_hash = ?",
      [tokenHash]
    )
    return null
  }

  return { email: row.email, expiresAt: row.expires_at }
}

export function generateLoginSessionToken(): string {
  return generateRandomHex(48)
}

export async function saveLoginSessionToken(
  email: string,
  token: string,
  expiresAt: Date
): Promise<void> {
  const pool = await ensureLoginGateTables()
  const normalizedEmail = normalizeEmail(email)
  const tokenHash = hashLoginCode(token)

  await pool.execute<ResultSetHeader>(
    `
      INSERT INTO login_sessions (email, session_token_hash, session_code_hash, expires_at, created_at, updated_at)
      VALUES (?, ?, NULL, ?, NOW(), NOW())
      ON DUPLICATE KEY UPDATE
        session_token_hash = VALUES(session_token_hash),
        session_code_hash = NULL,
        expires_at = VALUES(expires_at),
        updated_at = NOW()
    `,
    [normalizedEmail, tokenHash, expiresAt]
  )
}

export async function consumeLoginCode(email: string, code: string): Promise<boolean> {
  const pool = await ensureLoginGateTables()
  const normalizedEmail = normalizeEmail(email)
  const hashedAttempt = hashLoginCode(code)

  const [rows] = await pool.query<LoginCodeRow[]>(
    "SELECT code_hash, expires_at FROM login_codes WHERE email = ? LIMIT 1",
    [normalizedEmail]
  )

  if (rows.length === 0) {
    return false
  }

  const row = rows[0]
  const now = new Date()
  if (row.expires_at < now) {
    await pool.execute<ResultSetHeader>("DELETE FROM login_codes WHERE email = ?", [normalizedEmail])
    return false
  }

  const storedBuffer = Buffer.from(row.code_hash, "hex")
  const attemptBuffer = Buffer.from(hashedAttempt, "hex")

  if (storedBuffer.length !== attemptBuffer.length) {
    await pool.execute<ResultSetHeader>("DELETE FROM login_codes WHERE email = ?", [normalizedEmail])
    return false
  }

  const matches = timingSafeEqual(storedBuffer, attemptBuffer)

  if (matches) {
    await pool.execute<ResultSetHeader>("DELETE FROM login_codes WHERE email = ?", [normalizedEmail])
    return true
  }

  return false
}
