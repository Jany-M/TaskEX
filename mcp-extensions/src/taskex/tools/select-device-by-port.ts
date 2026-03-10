import { z } from "zod";
import { selectDeviceByPort } from "../utils";
import { McpServerInterface } from "../../extension";

const SelectDeviceByPortSchema = z.object({
  port: z.number()
});

export async function registerSelectDeviceByPort(server: McpServerInterface): Promise<void> {
  server.tool(
    "taskex_select_device_by_port",
    SelectDeviceByPortSchema.shape,
    async (args: unknown) => {
      const validated = SelectDeviceByPortSchema.parse(args);
      try {
        const deviceSerial = await selectDeviceByPort(validated.port);
        if (!deviceSerial) {
          return {
            content: [{ type: "text" as const, text: `No device found on port ${validated.port}.` }],
            isError: true
          };
        }
        return { content: [{ type: "text" as const, text: deviceSerial }] };
      } catch (error) {
        return {
          content: [{ type: "text" as const, text: `Error: ${error instanceof Error ? error.message : String(error)}` }],
          isError: true
        };
      }
    },
    {
      description:
        "Find the ADB device serial for a BlueStacks instance running on a specific port. " +
        "Returns the device serial (e.g., '127.0.0.1:5555') if found."
    }
  );
}
