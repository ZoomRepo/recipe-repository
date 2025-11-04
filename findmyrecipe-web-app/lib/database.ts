import mysql from "mysql2/promise"

const DEFAULT_CONFIG = {
  host: "192.168.1.99",
  port: 3306,
  user: "reciperepository",
  password: "Xenomorph123!",
  database: "reciperepository",
  connectionLimit: 5,
}

type PoolHolder = {
  mysqlPool?: mysql.Pool
}

const globalForPool = globalThis as typeof globalThis & PoolHolder

function resolveConfig() {
  const rawPort = Number.parseInt(process.env.DB_PORT ?? String(DEFAULT_CONFIG.port), 10)
  const rawConnectionLimit = Number.parseInt(process.env.DB_POOL_SIZE ?? "", 10)
  return {
    host: process.env.DB_HOST ?? DEFAULT_CONFIG.host,
    port: Number.isFinite(rawPort) && rawPort > 0 ? rawPort : DEFAULT_CONFIG.port,
    user: process.env.DB_USER ?? DEFAULT_CONFIG.user,
    password: process.env.DB_PASSWORD ?? DEFAULT_CONFIG.password,
    database: process.env.DB_NAME ?? DEFAULT_CONFIG.database,
    connectionLimit:
      Number.isFinite(rawConnectionLimit) && rawConnectionLimit > 0
        ? rawConnectionLimit
        : DEFAULT_CONFIG.connectionLimit,
    waitForConnections: true,
    charset: "utf8mb4",
  }
}

export function getPool(): mysql.Pool {
  if (!globalForPool.mysqlPool) {
    globalForPool.mysqlPool = mysql.createPool(resolveConfig())
  }
  return globalForPool.mysqlPool
}
