/**
 * Extension interface for adb-mcp
 *
 * Minimal copy of adb-mcp's extension.ts — kept in sync manually.
 * Do NOT add logic here; this is types only.
 */

export interface McpServerInterface {
  tool(
    name: string,
    schema: Record<string, unknown>,
    handler: (args: unknown, extra: unknown) => Promise<unknown>,
    options?: { description?: string }
  ): void;
  resource(
    name: string,
    uri: string,
    handler: (uri: URL) => Promise<unknown>
  ): void;
}

export abstract class Extension {
  abstract readonly name: string;
  abstract register(server: McpServerInterface): Promise<void>;
}
