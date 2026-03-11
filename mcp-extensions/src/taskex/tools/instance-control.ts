import { z } from "zod";
import { execFile } from "child_process";
import { promisify } from "util";
import { dirname, join, resolve } from "path";
import { existsSync } from "fs";
import { getConfig } from "../config";
import { McpServerInterface } from "../../extension";

const execFilePromise = promisify(execFile);

const ListInstancesSchema = z.object({});

const InstanceControlBaseSchema = z.object({
  action: z.enum(["start", "stop"]),
  identifier: z.string().optional(),
  id: z.number().optional(),
  port: z.number().optional(),
  name: z.string().optional(),
});

const InstanceControlSchema = InstanceControlBaseSchema
  .refine(
    (v) => {
      const provided = [
        v.identifier !== undefined,
        v.id !== undefined,
        v.port !== undefined,
        v.name !== undefined,
      ].filter(Boolean).length;
      return provided === 1;
    },
    { message: "Provide exactly one of: identifier, id, port, or name." }
  );

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

async function runTaskExCli(args: string[]): Promise<string> {
  const taskexRootPath = resolveTaskExRootPath();
  const pythonPath = resolveTaskExPythonPath(taskexRootPath);
  const mainPyPath = join(taskexRootPath, "main.py");

  if (!existsSync(mainPyPath)) {
    throw new Error(`TaskEX main.py not found at: ${mainPyPath}`);
  }

  const result = await execFilePromise(
    pythonPath,
    [mainPyPath, ...args],
    { cwd: taskexRootPath, encoding: "utf8", maxBuffer: 10 * 1024 * 1024 }
  );

  return ((result.stdout as string) || "").trim() || ((result.stderr as string) || "").trim();
}

function resolveInstanceIdentifier(v: z.infer<typeof InstanceControlBaseSchema>): string {
  if (v.identifier !== undefined) return v.identifier;
  if (v.id !== undefined) return String(v.id);
  if (v.port !== undefined) return String(v.port);
  return v.name as string;
}

export async function registerListInstances(server: McpServerInterface): Promise<void> {
  server.tool(
    "taskex_list_instances",
    ListInstancesSchema.shape,
    async (args: unknown) => {
      ListInstancesSchema.parse(args);
      try {
        const output = await runTaskExCli(["--list-instances"]);
        return { content: [{ type: "text" as const, text: output || "No output." }] };
      } catch (error) {
        return {
          content: [{ type: "text" as const, text: `Error: ${error instanceof Error ? error.message : String(error)}` }],
          isError: true,
        };
      }
    },
    {
      description:
        "List registered TaskEX instances from the local database (ID, name, port, profile). " +
        "Uses TaskEX CLI and returns plain text table output.",
    }
  );
}

export async function registerInstanceControl(server: McpServerInterface): Promise<void> {
  server.tool(
    "taskex_instance_control",
    InstanceControlBaseSchema.shape,
    async (args: unknown) => {
      const v = InstanceControlSchema.parse(args);
      const identifier = resolveInstanceIdentifier(v);

      try {
        const cliArgs = v.action === "start"
          ? ["--start-instance", identifier]
          : ["--stop-instance", identifier];

        const output = await runTaskExCli(cliArgs);
        return { content: [{ type: "text" as const, text: output || "OK" }] };
      } catch (error) {
        return {
          content: [{ type: "text" as const, text: `Error: ${error instanceof Error ? error.message : String(error)}` }],
          isError: true,
        };
      }
    },
    {
      description:
        "Start or stop Evony for a registered TaskEX instance by identifier, id, port, or name. " +
        "Exactly one selector must be provided.",
    }
  );
}
