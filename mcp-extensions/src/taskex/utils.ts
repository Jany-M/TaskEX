/**
 * TaskEX Extension Utilities
 */

import { execFile } from "child_process";
import { promisify } from "util";

const execFilePromise = promisify(execFile);

export const ADB_BINARY = process.env.ADB_PATH || "adb";

export interface AndroidDevice {
  serial: string;
  status: string;
  port?: number;
}

export function parseAdbDevices(devicesOutput: string): AndroidDevice[] {
  const devices: AndroidDevice[] = [];
  const lines = devicesOutput.split("\n").slice(1);

  for (const line of lines) {
    if (!line.trim()) continue;
    const parts = line.trim().split(/\s+/);
    if (parts.length >= 2) {
      const serial = parts[0];
      const status = parts[1];
      let port: number | undefined;
      if (serial.includes(":")) {
        port = parseInt(serial.split(":")[1], 10);
      }
      devices.push({ serial, status, port });
    }
  }

  return devices;
}

export async function getConnectedDevices(): Promise<AndroidDevice[]> {
  const { stdout } = await execFilePromise(ADB_BINARY, ["devices", "-l"], { encoding: "utf8" });
  return parseAdbDevices(stdout);
}

export async function selectDeviceByPort(port: number): Promise<string | null> {
  const devices = await getConnectedDevices();
  const device = devices.find((d) => d.port === port && d.status === "device");
  return device?.serial || null;
}

export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  baseDelayMs: number = 500,
  maxDelayMs: number = 5000
): Promise<T> {
  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));
      if (attempt < maxRetries) {
        const delay = Math.min(baseDelayMs * Math.pow(2, attempt), maxDelayMs);
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }
  }

  throw lastError || new Error("Retry failed with unknown error");
}

export async function waitForCondition(
  condition: () => Promise<boolean>,
  timeoutMs: number = 10000,
  pollIntervalMs: number = 500
): Promise<boolean> {
  const startTime = Date.now();

  while (Date.now() - startTime < timeoutMs) {
    try {
      if (await condition()) return true;
    } catch (_) {
      // Ignore polling errors
    }
    await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));
  }

  return false;
}

export function scaleCoordinates(
  x: number,
  y: number,
  scaleX: number = 1.0,
  scaleY: number = 1.0
): { x: number; y: number } {
  return { x: Math.round(x * scaleX), y: Math.round(y * scaleY) };
}
