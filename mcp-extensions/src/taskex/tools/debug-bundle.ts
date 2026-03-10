import { z } from "zod";
import { execFile } from "child_process";
import { promisify } from "util";
import { getConfig } from "../config";
import { McpServerInterface } from "../../extension";
import { ADB_BINARY } from "../utils";

const execFilePromise = promisify(execFile);

const DebugBundleSchema = z.object({
  device: z.string().optional(),
  includeScreenshot: z.boolean().optional(),
  includeUiDump: z.boolean().optional(),
  logcatLines: z.number().optional()
});

export async function registerDebugBundle(server: McpServerInterface): Promise<void> {
  server.tool(
    "taskex_debug_bundle",
    DebugBundleSchema.shape,
    async (args: unknown) => {
      const v = DebugBundleSchema.parse(args);
      try {
        const config = getConfig();
        const deviceArgs = v.device ? ["-s", v.device] : [];
        const includeScreenshot = v.includeScreenshot !== false;
        const includeUiDump = v.includeUiDump !== false;
        const maxLines = v.logcatLines || config.logRetentionLines;

        const bundle: Record<string, unknown> = {
          timestamp: new Date().toISOString(),
          device: v.device || "default"
        };

        try {
          const { stdout } = await execFilePromise(ADB_BINARY, [...deviceArgs, "shell", "getprop"]);
          bundle.deviceProperties = (stdout as string).split("\n").slice(0, 10).join("\n");
        } catch (e) { bundle.devicePropertiesError = String(e); }

        try {
          const result = await execFilePromise(ADB_BINARY, [...deviceArgs, "logcat", "-d"],
            { encoding: "utf8", maxBuffer: 10 * 1024 * 1024 });
          const lines = ((result.stdout as string) || "").split("\n");
          bundle.logcat = lines.slice(-maxLines).join("\n");
        } catch (e) { bundle.logcatError = String(e); }

        if (includeUiDump) {
          try {
            const result = await execFilePromise(ADB_BINARY, [...deviceArgs, "shell", "dumpsys", "window", "dump"],
              { encoding: "utf8", maxBuffer: 10 * 1024 * 1024 });
            bundle.uiHierarchy = ((result.stdout as string) || "").substring(0, 50000);
          } catch (e) { bundle.uiHierarchyError = String(e); }
        }

        if (includeScreenshot) {
          try {
            await execFilePromise(ADB_BINARY, [...deviceArgs, "shell", "screencap", "-p", "/sdcard/debug.png"]);
            bundle.screenshotStatus = "Screenshot captured at /sdcard/debug.png on device";
          } catch (e) { bundle.screenshotError = String(e); }
        }

        return { content: [{ type: "text" as const, text: JSON.stringify(bundle, null, 2) }] };
      } catch (error) {
        return {
          content: [{ type: "text" as const, text: `Error: ${error instanceof Error ? error.message : String(error)}` }],
          isError: true
        };
      }
    },
    {
      description:
        "Collect comprehensive device debug information including device properties, logcat, UI hierarchy, and screenshot status. " +
        "Returns a JSON bundle. Large UI dumps are truncated to ~50KB."
    }
  );
}
