/**
 * TaskEX Extension Configuration
 *
 * Load configuration from environment variables or taskex.config.json.
 * Hierarchy: ENV_VAR > taskex.config.json > defaults
 */

import { readFileSync } from "fs";
import { join } from "path";

export interface TaskExConfig {
  blueStacksPorts: number[];
  evonyPackage: string;
  evonyActivity: string;
  tapRetryTimeout: number;
  swipeRetryTimeout: number;
  screenStateTimeout: number;
  logRetentionLines: number;
  coordinateScaleX: number;
  coordinateScaleY: number;
}

const DEFAULT_CONFIG: TaskExConfig = {
  blueStacksPorts: [5555, 5556],
  evonyPackage: "com.topgamesinc.evony",
  evonyActivity: "com.topgamesinc.androidplugin.UnityActivity",
  tapRetryTimeout: 5000,
  swipeRetryTimeout: 5000,
  screenStateTimeout: 10000,
  logRetentionLines: 100,
  coordinateScaleX: 1.0,
  coordinateScaleY: 1.0
};

export function loadConfig(): TaskExConfig {
  const config = { ...DEFAULT_CONFIG };

  // Try to load from taskex.config.json in TASKEX_CONFIG_PATH or cwd
  const configPath = process.env.TASKEX_CONFIG_PATH || join(process.cwd(), "taskex.config.json");
  try {
    const fileContent = readFileSync(configPath, "utf8");
    const fileConfig = JSON.parse(fileContent) as Partial<TaskExConfig>;
    Object.assign(config, fileConfig);
    console.error(`[TaskEX] Loaded config from ${configPath}`);
  } catch (_) {
    if (process.env.TASKEX_CONFIG_PATH) {
      console.error(`[TaskEX] Warning: Could not load config from ${configPath}, using defaults`);
    }
  }

  // Environment variable overrides
  if (process.env.TASKEX_BLUESTACKS_PORTS) {
    const ports = process.env.TASKEX_BLUESTACKS_PORTS
      .split(",")
      .map((p) => parseInt(p.trim(), 10))
      .filter((p) => !isNaN(p));
    if (ports.length > 0) config.blueStacksPorts = ports;
  }
  if (process.env.TASKEX_EVONY_PACKAGE) config.evonyPackage = process.env.TASKEX_EVONY_PACKAGE;
  if (process.env.TASKEX_EVONY_ACTIVITY) config.evonyActivity = process.env.TASKEX_EVONY_ACTIVITY;

  return config;
}

let configInstance: TaskExConfig | null = null;

export function getConfig(): TaskExConfig {
  if (!configInstance) {
    configInstance = loadConfig();
  }
  return configInstance;
}
