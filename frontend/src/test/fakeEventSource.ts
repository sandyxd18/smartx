import { act } from "@testing-library/react";

type Listener = (event: MessageEvent<string>) => void;

/** Minimal EventSource stand-in: tests push events with emit(). jsdom has none. */
export class FakeEventSource {
  static instances: FakeEventSource[] = [];

  readonly url: string;
  closed = false;
  private listeners = new Map<string, Listener[]>();

  constructor(url: string | URL) {
    this.url = String(url);
    FakeEventSource.instances.push(this);
  }

  static last(): FakeEventSource {
    const source = FakeEventSource.instances.at(-1);
    if (!source) throw new Error("no EventSource was created");
    return source;
  }

  addEventListener(type: string, listener: Listener): void {
    this.listeners.set(type, [...(this.listeners.get(type) ?? []), listener]);
  }

  close(): void {
    this.closed = true;
  }

  emit(type: string, payload?: unknown): void {
    const event = new MessageEvent(type, { data: JSON.stringify(payload ?? {}) });
    act(() => {
      for (const listener of this.listeners.get(type) ?? []) listener(event);
    });
  }
}
