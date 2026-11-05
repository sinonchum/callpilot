export type PanelEvent = {
  type: string;
  text?: string;
  utterance_id?: string;
  event?: {
    time?: string;
    date?: string;
    title?: string;
    location?: string;
    status?: string;
    stability?: string;
  };
  reminder?: { title?: string; time?: string; date?: string };
  note?: { text?: string };
  tool?: string;
  pixel?: { x: number; y: number };
  step_index?: number;
  matched?: boolean;
  kind?: string;
  items?: { label: string; summary: string }[];
  decision?: string;
  actions?: { kind: string }[];
  row?: { title?: string; dtstart?: number };
};

export type Line = { id: string; text: string; final: boolean };

export type ViewState = {
  lines: Line[];
  time: string;
  date: string;
  title: string;
  location: string;
  status: string;
  reminder: string;
  note: string;
  steps: string[];
  plans: string[];
  card: { label: string; summary: string }[] | null;
  verifies: string[];
  decision: string;
};

export function initialView(): ViewState {
  return {
    lines: [],
    time: "—",
    date: "",
    title: "",
    location: "",
    status: "",
    reminder: "",
    note: "",
    steps: [],
    plans: [],
    card: null,
    verifies: [],
    decision: "",
  };
}

export function parseJsonl(text: string): PanelEvent[] {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .map((line) => JSON.parse(line) as PanelEvent);
}

export function applyEvent(state: ViewState, event: PanelEvent): ViewState {
  if (event.type === "transcript.partial" || event.type === "transcript.final") {
    const id = event.utterance_id ?? `line-${state.lines.length}`;
    const line: Line = {
      id,
      text: event.text ?? "",
      final: event.type === "transcript.final",
    };
    return { ...state, lines: [...state.lines.filter((item) => item.id !== id), line] };
  }
  if (event.type === "intent.snapshot" && event.event) {
    const reminder = event.reminder;
    return {
      ...state,
      time: event.event.time || state.time,
      date: event.event.date || state.date,
      title: event.event.title || state.title,
      location: event.event.location || state.location,
      status: event.event.status || state.status,
      reminder: reminder ? `${reminder.date ?? ""} ${reminder.time ?? ""} ${reminder.title ?? ""}`.trim() : state.reminder,
      note: event.note?.text || state.note,
    };
  }
  if (event.type === "plan.created") {
    const label = (event.actions ?? []).map((action) => action.kind).join(", ");
    return { ...state, plans: [...state.plans, label] };
  }
  if (event.type === "agent.step") {
    const pixel = event.pixel ? ` (${event.pixel.x}, ${event.pixel.y})` : "";
    return { ...state, steps: [...state.steps, `${event.step_index ?? state.steps.length} ${event.tool ?? "step"}${pixel}`] };
  }
  if (event.type === "verify.result") {
    const title = event.row?.title ?? event.kind ?? "check";
    return { ...state, verifies: [...state.verifies, `${title} ${event.matched ? "matched" : "miss"}`] };
  }
  if (event.type === "confirm.request") {
    return { ...state, card: event.items ?? [] };
  }
  if (event.type === "confirm.decision") {
    return { ...state, decision: event.decision ?? "" };
  }
  return state;
}

export function applyAll(events: PanelEvent[]): ViewState {
  return events.reduce(applyEvent, initialView());
}
