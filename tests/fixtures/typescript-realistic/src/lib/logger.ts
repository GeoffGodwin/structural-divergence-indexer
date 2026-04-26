// Structured logging utilities.
import { config } from "@/config";

type LogLevel = "debug" | "info" | "warn" | "error";

const LEVELS: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

function shouldLog(level: LogLevel): boolean {
  return LEVELS[level] >= LEVELS[config.logLevel];
}

function formatEntry(level: LogLevel, message: string, meta?: object): string {
  const entry = {
    ts: new Date().toISOString(),
    level,
    message,
    ...(meta ?? {}),
  };
  return JSON.stringify(entry);
}

export const logger = {
  debug(message: string, meta?: object): void {
    if (shouldLog("debug")) {
      console.log(formatEntry("debug", message, meta));
    }
  },

  info(message: string, meta?: object): void {
    if (shouldLog("info")) {
      console.log(formatEntry("info", message, meta));
    }
  },

  warn(message: string, meta?: object): void {
    if (shouldLog("warn")) {
      console.warn(formatEntry("warn", message, meta));
    }
  },

  error(message: string, error?: Error, meta?: object): void {
    if (shouldLog("error")) {
      console.error(
        formatEntry("error", message, {
          ...meta,
          errorMessage: error?.message,
          stack: error?.stack,
        })
      );
    }
  },
};
