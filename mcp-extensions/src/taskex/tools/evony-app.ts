import { z } from "zod";
import { execFile } from "child_process";
import { promisify } from "util";
import { getConfig } from "../config";
import { McpServerInterface } from "../../extension";
import { ADB_BINARY } from "../utils";

const execFilePromise = promisify(execFile);

const EvonyControlSchema = z.object({
  action: z.enum(["start", "stop"]),
  device: z.string().optional(),
  wait: z.boolean().optional()
});

export async function registerEvonyControl(server: McpServerInterface): Promise<void> {
  server.tool(
    "taskex_evony_control",
    EvonyControlSchema.shape,
    async (args: unknown) => {
      const v = EvonyControlSchema.parse(args);
      try {
        const config = getConfig();
        const deviceArgs = v.device ? ["-s", v.device] : [];

        if (v.action === "start") {
          await execFilePromise(ADB_BINARY, [...deviceArgs, "shell", "am", "start",
            "-n", `${config.evonyPackage}/${config.evonyActivity}`]);
          if (v.wait) await new Promise((resolve) => setTimeout(resolve, 2000));
          return { content: [{ type: "text" as const, text: "Evony started" }] };
        } else {
          await execFilePromise(ADB_BINARY, [...deviceArgs, "shell", "am", "force-stop", config.evonyPackage]);
          if (v.wait) await new Promise((resolve) => setTimeout(resolve, 1000));
          return { content: [{ type: "text" as const, text: "Evony stopped" }] };
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
        "Start or stop the Evony application on a connected device. " +
        "Action 'start' launches the app; 'stop' force-stops it."
    }
  );
}
