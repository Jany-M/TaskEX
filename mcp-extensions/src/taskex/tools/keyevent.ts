import { z } from "zod";
import { execFile } from "child_process";
import { promisify } from "util";
import { McpServerInterface } from "../../extension";
import { ADB_BINARY } from "../utils";

const execFilePromise = promisify(execFile);

const KeyEventSchema = z.object({
  device: z.string().optional(),
  key: z.enum([
    "BACK", "HOME", "ENTER", "POWER",
    "VOLUME_UP", "VOLUME_DOWN",
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"
  ])
});

export async function registerKeyEvent(server: McpServerInterface): Promise<void> {
  server.tool(
    "taskex_keyevent",
    KeyEventSchema.shape,
    async (args: unknown) => {
      const v = KeyEventSchema.parse(args);
      try {
        const deviceArgs = v.device ? ["-s", v.device] : [];
        const keyCode = v.key.startsWith("KEYCODE_") ? v.key : `KEYCODE_${v.key}`;

        await execFilePromise(ADB_BINARY, [...deviceArgs, "shell", "input", "keyevent", keyCode]);

        return { content: [{ type: "text" as const, text: `Key event sent: ${v.key}` }] };
      } catch (error) {
        return {
          content: [{ type: "text" as const, text: `Error: ${error instanceof Error ? error.message : String(error)}` }],
          isError: true
        };
      }
    },
    {
      description:
        "Send an Android key event to the device (e.g., BACK, HOME, ENTER). " +
        "Supports BACK, HOME, ENTER, POWER, VOLUME_UP/DOWN, and digit keys."
    }
  );
}
