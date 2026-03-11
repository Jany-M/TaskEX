import { z } from "zod";
import { execFile } from "child_process";
import { promisify } from "util";
import { dirname, join, resolve } from "path";
import { existsSync } from "fs";
import { getConfig } from "../config";
import { McpServerInterface } from "../../extension";

const execFilePromise = promisify(execFile);

const TemplateMatchSchema = z.object({
  templatePath: z.string(),
  threshold: z.number().optional(),
  device: z.string().optional(),
});

const ScreenRegionSchema = z.object({
  x1: z.number(),
  y1: z.number(),
  x2: z.number(),
  y2: z.number(),
  outputPath: z.string().optional(),
  device: z.string().optional(),
});

function resolveTaskExRootPath(): string {
  const config = getConfig();

  if (config.taskexRootPath && config.taskexRootPath.trim()) {
    return config.taskexRootPath.trim();
  }

  if (process.env.TASKEX_CONFIG_PATH && process.env.TASKEX_CONFIG_PATH.trim()) {
    const configPath = process.env.TASKEX_CONFIG_PATH.trim();
    return resolve(dirname(configPath), "..");
  }

  return process.cwd();
}

function resolveTaskExPythonPath(taskexRootPath: string): string {
  const config = getConfig();

  if (config.taskexPythonPath && config.taskexPythonPath.trim()) {
    return config.taskexPythonPath.trim();
  }

  const venvPython = join(taskexRootPath, ".venv", "Scripts", "python.exe");
  if (existsSync(venvPython)) {
    return venvPython;
  }

  return "python";
}

async function runVisionHelper(args: string[]): Promise<Record<string, unknown>> {
  const taskexRootPath = resolveTaskExRootPath();
  const pythonPath = resolveTaskExPythonPath(taskexRootPath);
  const helperPath = join(taskexRootPath, "utils", "mcp_vision_helper.py");

  if (!existsSync(helperPath)) {
    throw new Error(`Vision helper not found at: ${helperPath}`);
  }

  const result = await execFilePromise(
    pythonPath,
    [helperPath, ...args],
    { cwd: taskexRootPath, encoding: "utf8", maxBuffer: 10 * 1024 * 1024 }
  );

  const stdout = ((result.stdout as string) || "").trim();
  if (!stdout) {
    throw new Error("Vision helper returned empty output.");
  }

  return JSON.parse(stdout) as Record<string, unknown>;
}

export async function registerTemplateMatch(server: McpServerInterface): Promise<void> {
  server.tool(
    "taskex_template_match",
    TemplateMatchSchema.shape,
    async (args: unknown) => {
      const v = TemplateMatchSchema.parse(args);
      try {
        const helperArgs = [
          "template-match",
          "--template", v.templatePath,
          "--threshold", String(v.threshold ?? 0.85),
        ];
        if (v.device) helperArgs.push("--device", v.device);

        const output = await runVisionHelper(helperArgs);
        return { content: [{ type: "text" as const, text: JSON.stringify(output) }] };
      } catch (error) {
        return {
          content: [{ type: "text" as const, text: `Error: ${error instanceof Error ? error.message : String(error)}` }],
          isError: true,
        };
      }
    },
    {
      description:
        "Capture current device screen and run OpenCV template match using a local image template. " +
        "Returns match score and center coordinates when found.",
    }
  );
}

export async function registerScreenRegion(server: McpServerInterface): Promise<void> {
  server.tool(
    "taskex_screen_region",
    ScreenRegionSchema.shape,
    async (args: unknown) => {
      const v = ScreenRegionSchema.parse(args);
      try {
        const helperArgs = [
          "screen-region",
          "--x1", String(v.x1),
          "--y1", String(v.y1),
          "--x2", String(v.x2),
          "--y2", String(v.y2),
        ];

        if (v.outputPath) helperArgs.push("--output", v.outputPath);
        if (v.device) helperArgs.push("--device", v.device);

        const output = await runVisionHelper(helperArgs);
        return { content: [{ type: "text" as const, text: JSON.stringify(output) }] };
      } catch (error) {
        return {
          content: [{ type: "text" as const, text: `Error: ${error instanceof Error ? error.message : String(error)}` }],
          isError: true,
        };
      }
    },
    {
      description:
        "Capture current device screen and crop a rectangular region by coordinates. " +
        "Returns metadata and optionally writes a PNG file.",
    }
  );
}
