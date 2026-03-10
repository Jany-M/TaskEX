import { z } from "zod";
import { execFile } from "child_process";
import { promisify } from "util";
import { waitForCondition, ADB_BINARY } from "../utils";
import { getConfig } from "../config";
import { McpServerInterface } from "../../extension";

const execFilePromise = promisify(execFile);

const WaitForScreenSchema = z.object({
  device: z.string().optional(),
  condition: z.enum(["contains", "not_contains"]),
  text: z.string(),
  timeoutMs: z.number().optional()
});

async function checkScreenForText(deviceArgs: string[], text: string): Promise<boolean> {
  const result = await execFilePromise(ADB_BINARY, [
    ...deviceArgs, "shell", "dumpsys", "window", "dump"
  ], { encoding: "utf8", maxBuffer: 10 * 1024 * 1024 });
  return ((result.stdout as string) || "").includes(text);
}

export async function registerWaitForScreen(server: McpServerInterface): Promise<void> {
  server.tool(
    "taskex_wait_for_screen",
    WaitForScreenSchema.shape,
    async (args: unknown) => {
      const v = WaitForScreenSchema.parse(args);
      try {
        const config = getConfig();
        const deviceArgs = v.device ? ["-s", v.device] : [];
        const timeoutMs = v.timeoutMs || config.screenStateTimeout;

        const conditionFn = v.condition === "contains"
          ? () => checkScreenForText(deviceArgs, v.text)
          : async () => !(await checkScreenForText(deviceArgs, v.text));

        const conditionMet = await waitForCondition(conditionFn, timeoutMs, 500);

        if (conditionMet) {
          return { content: [{ type: "text" as const, text: `Screen condition met: ${v.condition} "${v.text}"` }] };
        } else {
          return {
            content: [{ type: "text" as const, text: `Timeout waiting for screen condition: ${v.condition} "${v.text}"` }],
            isError: true
          };
        }
      } catch (error) {
        return {
          content: [{ type: "text" as const, text: `Error: ${error instanceof Error ? error.message : String(error)}` }],
          isError: true
        };
      }
    },
    {
      description:
        "Wait until a specific text appears on or disappears from the screen. " +
        "Polls the UI hierarchy at 500ms intervals. Useful for syncing with app state changes."
    }
  );
}
