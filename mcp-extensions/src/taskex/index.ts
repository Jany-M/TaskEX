/**
 * TaskEX MCP Extension
 *
 * Entry point for registering all TaskEX-specific tools with adb-mcp.
 * Lives in the TaskEX project — loaded by adb-mcp via EXTENSIONS_DIR env var.
 */

import { Extension, McpServerInterface } from "../extension";
import { registerSelectDeviceByPort } from "./tools/select-device-by-port";
import { registerScreenshot } from "./tools/screenshot";
import { registerTap, registerSwipe } from "./tools/tap-swipe";
import { registerEvonyControl } from "./tools/evony-app";
import { registerKeyEvent } from "./tools/keyevent";
import { registerWaitForScreen } from "./tools/wait-for-screen";
import { registerDebugBundle } from "./tools/debug-bundle";
import { registerListInstances, registerInstanceControl } from "./tools/instance-control";
import { registerTemplateMatch, registerScreenRegion } from "./tools/vision";
import { registerFindAndTap } from "./tools/find-and-tap";

export class TaskExExtension extends Extension {
  readonly name = "TaskEX";

  async register(server: McpServerInterface): Promise<void> {
    console.error("[TaskEX Extension] Registering TaskEX tools...");

    await registerSelectDeviceByPort(server);
    await registerScreenshot(server);
    await registerTap(server);
    await registerSwipe(server);
    await registerEvonyControl(server);
    await registerKeyEvent(server);
    await registerWaitForScreen(server);
    await registerDebugBundle(server);
    await registerListInstances(server);
    await registerInstanceControl(server);
    await registerTemplateMatch(server);
    await registerScreenRegion(server);
    await registerFindAndTap(server);

    console.error("[TaskEX Extension] All TaskEX tools registered successfully");
  }
}

export default TaskExExtension;
