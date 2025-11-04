import type { ResultSetHeader, RowDataPacket } from "mysql2/promise"

import { getPool } from "./database"

const USER_FIELDS = "id, email, password_hash AS passwordHash, created_at AS createdAt, updated_at AS updatedAt"

let hasEnsuredUsersTable = false

async function ensureUsersTable() {
  const pool = getPool()

  if (!hasEnsuredUsersTable) {
    await pool.query(`
      CREATE TABLE IF NOT EXISTS users (
        id INT UNSIGNED NOT NULL AUTO_INCREMENT,
        email VARCHAR(320) NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        UNIQUE KEY uniq_users_email (email)
      )
      ENGINE=InnoDB
      DEFAULT CHARSET = utf8mb4
      COLLATE = utf8mb4_unicode_ci
    `)

    hasEnsuredUsersTable = true
  }

  return pool
}

type UserRow = RowDataPacket & {
  id: number
  email: string
  passwordHash: string
  createdAt: Date
  updatedAt: Date
}

export type UserRecord = {
  id: number
  email: string
  passwordHash: string
  createdAt: Date
  updatedAt: Date
}

export async function findUserByEmail(email: string): Promise<UserRecord | null> {
  const pool = await ensureUsersTable()
  const normalizedEmail = email.trim().toLowerCase()
  const [rows] = await pool.query<UserRow[]>(
    `SELECT ${USER_FIELDS} FROM users WHERE email = ? LIMIT 1`,
    [normalizedEmail]
  )

  if (rows.length === 0) {
    return null
  }

  const row = rows[0]
  return {
    id: row.id,
    email: row.email,
    passwordHash: row.passwordHash,
    createdAt: new Date(row.createdAt),
    updatedAt: new Date(row.updatedAt),
  }
}

export async function findUserById(id: number): Promise<UserRecord | null> {
  const pool = await ensureUsersTable()
  const [rows] = await pool.query<UserRow[]>(
    `SELECT ${USER_FIELDS} FROM users WHERE id = ? LIMIT 1`,
    [id]
  )

  if (rows.length === 0) {
    return null
  }

  const row = rows[0]
  return {
    id: row.id,
    email: row.email,
    passwordHash: row.passwordHash,
    createdAt: new Date(row.createdAt),
    updatedAt: new Date(row.updatedAt),
  }
}

export async function createUser({
  email,
  passwordHash,
}: {
  email: string
  passwordHash: string
}): Promise<UserRecord> {
  const pool = await ensureUsersTable()
  const normalizedEmail = email.trim().toLowerCase()
  const [result] = await pool.execute<ResultSetHeader>(
    "INSERT INTO users (email, password_hash, created_at, updated_at) VALUES (?, ?, NOW(), NOW())",
    [normalizedEmail, passwordHash]
  )

  const insertedUser = await findUserById(result.insertId)
  if (!insertedUser) {
    throw new Error("Failed to load user after creation")
  }
  return insertedUser
}
