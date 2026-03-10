import { z } from "zod";
import { execFile } from "child_process";
import { promisify } from "util";
import { join } from "path";
import { tmpdir } from "os";
import { readFile, unlink } from "fs";
import { McpServerInterface } from "../../extension";
import { ADB_BINARY } from "../utils";

const execFilePromise = promisify(execFile);
const readFilePromise = promisify(readFile);
const unlinkPromise = promisify(unlink);

const ScreenshotSchema = z.object({
  device: z.string().optional(),
  withTimestamp: z.boolean().optional(),
  asBase64: z.boolean().optional()
});

export async function registerScreenshot(server: McpServerInterface): Promise<void> {
  server.tool(
    "taskex_screenshot",
    ScreenshotSchema.shape,
    async (args: unknown) => {
      const validated = ScreenshotSchema.parse(args);
      const deviceArgs = validated.device ? ["-s", validated.device] : [];
      const tempFilePath = join(tmpdir(), `taskex-screenshot-${Date.now()}.png`);

      try {
        await execFilePromise(ADB_BINARY, [...deviceArgs, "shell", "screencap", "-p", "/sdcard/screenshot.png"]);
        await execFilePromise(ADB_BINARY, [...deviceArgs, "pull", "/sdcard/screenshot.png", tempFilePath]);

        if (validated.asBase64) {
          const fileData = await readFilePromise(tempFilePath);
          const base64Data = fileData.toString("base64");
          await unlinkPromise(tempFilePath);
          return { content: [{ type: "text" as const, text: base64Data }] };
        }

        const timestamp = validated.withTimestamp ? new Date().toISOString().replace(/[:.]/g, "-") : "";
        const filename = timestamp ? `taskex-screenshot-${timestamp}.png` : "taskex-screenshot.png";
        await unlinkPromise(tempFilePath);
        return { content: [{ type: "text" as const, text: `Screenshot captured: ${filename}` }] };
      } catch (error) {
        try { await unlinkPromise(tempFilePath); } catch (_) { /* ignore */ }
        return {
          content: [{ type: "text" as const, text: `Error: ${error instanceof Error ? error.message : String(error)}` }],
          isError: true
        };
      }
    },
    {
      description:
        "Capture the current screen of a connected Android device as a PNG screenshot. " +
        "Use asBase64=true to get the image as base64 data."
    }
  );
}
