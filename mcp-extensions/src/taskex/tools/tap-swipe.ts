import { z } from "zod";
import { execFile } from "child_process";
import { promisify } from "util";
import { retryWithBackoff, scaleCoordinates, ADB_BINARY } from "../utils";
import { getConfig } from "../config";
import { McpServerInterface } from "../../extension";

const execFilePromise = promisify(execFile);

const TapSchema = z.object({
  x: z.number(),
  y: z.number(),
  device: z.string().optional(),
  scaled: z.boolean().optional()
});

const SwipeSchema = z.object({
  x1: z.number(),
  y1: z.number(),
  x2: z.number(),
  y2: z.number(),
  device: z.string().optional(),
  duration: z.number().optional(),
  scaled: z.boolean().optional()
});

export async function registerTap(server: McpServerInterface): Promise<void> {
  server.tool(
    "taskex_tap",
    TapSchema.shape,
    async (args: unknown) => {
      const v = TapSchema.parse(args);
      try {
        const config = getConfig();
        const deviceArgs = v.device ? ["-s", v.device] : [];
        const { x, y } = v.scaled
          ? scaleCoordinates(v.x, v.y, config.coordinateScaleX, config.coordinateScaleY)
          : { x: v.x, y: v.y };

        await retryWithBackoff(() =>
          execFilePromise(ADB_BINARY, [...deviceArgs, "shell", "input", "tap", String(x), String(y)])
        , 3, 500);

        return { content: [{ type: "text" as const, text: `Tapped at (${x}, ${y})` }] };
      } catch (error) {
        return {
          content: [{ type: "text" as const, text: `Error: ${error instanceof Error ? error.message : String(error)}` }],
          isError: true
        };
      }
    },
    {
      description:
        "Perform a tap (click) on the device screen at specified coordinates. " +
        "Retries up to 3 times with exponential backoff. Use scaled=true to apply coordinate scaling."
    }
  );
}

export async function registerSwipe(server: McpServerInterface): Promise<void> {
  server.tool(
    "taskex_swipe",
    SwipeSchema.shape,
    async (args: unknown) => {
      const v = SwipeSchema.parse(args);
      try {
        const config = getConfig();
        const deviceArgs = v.device ? ["-s", v.device] : [];
        const duration = v.duration || 500;

        const { x: x1, y: y1 } = v.scaled
          ? scaleCoordinates(v.x1, v.y1, config.coordinateScaleX, config.coordinateScaleY)
          : { x: v.x1, y: v.y1 };
        const { x: x2, y: y2 } = v.scaled
          ? scaleCoordinates(v.x2, v.y2, config.coordinateScaleX, config.coordinateScaleY)
          : { x: v.x2, y: v.y2 };

        await retryWithBackoff(() =>
          execFilePromise(ADB_BINARY, [...deviceArgs, "shell", "input", "swipe",
            String(x1), String(y1), String(x2), String(y2), String(duration)])
        , 3, 500);

        return { content: [{ type: "text" as const, text: `Swiped from (${x1}, ${y1}) to (${x2}, ${y2}) over ${duration}ms` }] };
      } catch (error) {
        return {
          content: [{ type: "text" as const, text: `Error: ${error instanceof Error ? error.message : String(error)}` }],
          isError: true
        };
      }
    },
    {
      description:
        "Perform a swipe on the device screen from one point to another. " +
        "Retries up to 3 times. Specify duration in ms to control speed. Use scaled=true for coordinate scaling."
    }
  );
}
