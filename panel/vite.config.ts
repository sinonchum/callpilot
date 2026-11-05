import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig, type Plugin } from "vitest/config";

const here = dirname(fileURLToPath(import.meta.url));
const replayPath = resolve(here, "../laptop/fixtures/panel_replay.jsonl");

function replayFixture(): Plugin {
  return {
    name: "callpilot-replay",
    configureServer(server) {
      server.middlewares.use("/fixtures/panel_replay.jsonl", (_req, res) => {
        res.setHeader("Content-Type", "application/x-ndjson");
        res.end(readFileSync(replayPath));
      });
    },
    generateBundle() {
      this.emitFile({
        type: "asset",
        fileName: "fixtures/panel_replay.jsonl",
        source: readFileSync(replayPath),
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), replayFixture()],
  server: {
    host: "127.0.0.1",
    port: 5173,
  },
  test: {
    environment: "node",
  },
});
