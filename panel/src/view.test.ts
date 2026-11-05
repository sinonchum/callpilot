import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { applyAll, applyEvent, initialView, parseJsonl } from "./view";

const replayPath = resolve(dirname(fileURLToPath(import.meta.url)), "../../laptop/fixtures/panel_replay.jsonl");

describe("panel replay", () => {
  it("replaces a partial with the final of the same utterance", () => {
    const start = applyEvent(initialView(), {
      type: "transcript.partial",
      utterance_id: "u1",
      text: "à 15",
    });
    const next = applyEvent(start, {
      type: "transcript.final",
      utterance_id: "u1",
      text: "à 15h",
    });
    expect(next.lines).toEqual([{ id: "u1", text: "à 15h", final: true }]);
  });

  it("shows 16:00, the confirm card, and the undo decision from the recorded demo", () => {
    const view = applyAll(parseJsonl(readFileSync(replayPath, "utf8")));
    expect(view.time).toBe("16:00");
    expect(view.location).toBe("Station F");
    expect(view.title).toBe("POC");
    expect(view.status).toBe("corrected");
    expect(view.card?.map((item) => item.label)).toEqual(["日历", "提醒", "便签"]);
    expect(view.decision).toBe("undo_reminder");
    expect(view.steps.some((step) => step.includes("click"))).toBe(true);
    expect(view.verifies.some((line) => line.includes("matched"))).toBe(true);
  });
});
