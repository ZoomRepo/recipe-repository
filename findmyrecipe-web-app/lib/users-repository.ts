import type { ResultSetHeader, RowDataPacket } from "mysql2/promise"

import { getPool } from "./database"

const USER_FIELDS = "id, email, password_hash AS passwordHash, created_at AS createdAt, updated_at AS updatedAt"

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
  const pool = getPool()
  const [rows] = await pool.query<UserRow[]>(
    `SELECT ${USER_FIELDS} FROM users WHERE email = ? LIMIT 1`,
    [email.toLowerCase()]
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
  const pool = getPool()
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
  const pool = getPool()
  const normalizedEmail = email.toLowerCase()
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
