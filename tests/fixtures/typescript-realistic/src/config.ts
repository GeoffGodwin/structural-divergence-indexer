// Application configuration loaded from environment variables.

export interface AppConfig {
  port: number;
  dbHost: string;
  dbPort: number;
  dbName: string;
  dbUser: string;
  dbPassword: string;
  redisHost: string;
  redisPort: number;
  jwtSecret: string;
  logLevel: "debug" | "info" | "warn" | "error";
  nodeEnv: "development" | "test" | "production";
}

function requireEnv(key: string): string {
  const value = process.env[key];
  if (!value) {
    throw new Error(`Required environment variable not set: ${key}`);
  }
  return value;
}

function optionalEnv(key: string, defaultValue: string): string {
  return process.env[key] ?? defaultValue;
}

export function loadConfig(): AppConfig {
  return {
    port: parseInt(optionalEnv("PORT", "8080"), 10),
    dbHost: optionalEnv("DB_HOST", "localhost"),
    dbPort: parseInt(optionalEnv("DB_PORT", "5432"), 10),
    dbName: optionalEnv("DB_NAME", "appdb"),
    dbUser: optionalEnv("DB_USER", "app"),
    dbPassword: requireEnv("DB_PASSWORD"),
    redisHost: optionalEnv("REDIS_HOST", "localhost"),
    redisPort: parseInt(optionalEnv("REDIS_PORT", "6379"), 10),
    jwtSecret: requireEnv("JWT_SECRET"),
    logLevel: (optionalEnv("LOG_LEVEL", "info") as AppConfig["logLevel"]),
    nodeEnv: (optionalEnv("NODE_ENV", "development") as AppConfig["nodeEnv"]),
  };
}

export const config = loadConfig();
