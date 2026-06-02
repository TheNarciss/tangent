/**
 * Consume an SSE stream from a POST endpoint via fetch + ReadableStream.
 *
 * Native EventSource only supports GET — we POST to /reviews/generate, so
 * we parse the SSE format manually. Format expected (cf backend
 * routers/reviews.py):
 *
 *   data: {"chunk": "..."}\n\n          # incremental text chunk
 *   event: done\ndata: {}\n\n           # stream complete
 *   event: error\ndata: {"reason": "..."}\n\n   # mid-stream failure
 */

const API_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";

export type StreamingHandlers = {
  onChunk: (chunk: string) => void;
  onDone: () => void;
  onError: (reason: string) => void;
};

export async function streamReview(handlers: StreamingHandlers): Promise<void> {
  const resp = await fetch(`${API_URL}/reviews/generate`, {
    method: "POST",
    credentials: "include",
    headers: { Accept: "text/event-stream" },
  });

  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const body = await resp.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* no JSON body */
    }
    handlers.onError(detail);
    return;
  }

  if (!resp.body) {
    handlers.onError("Réponse sans corps (streaming non supporté ?)");
    return;
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE messages are separated by \n\n
      let sep: number;
      while ((sep = buffer.indexOf("\n\n")) >= 0) {
        const raw = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        if (!raw) continue;

        // Each event may have multiple fields (event:, data:). Parse them.
        let eventType = "message";
        let dataPayload = "";
        for (const line of raw.split("\n")) {
          if (line.startsWith("event: ")) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            dataPayload += line.slice(6);
          }
        }

        if (!dataPayload) continue;

        try {
          const parsed = JSON.parse(dataPayload);
          if (eventType === "done") {
            handlers.onDone();
            return;
          }
          if (eventType === "error") {
            handlers.onError(parsed.reason ?? "unknown");
            return;
          }
          // default: data: {"chunk": "..."}
          if (typeof parsed.chunk === "string") {
            handlers.onChunk(parsed.chunk);
          }
        } catch {
          /* ignore malformed event line */
        }
      }
    }
    handlers.onDone();
  } catch (err) {
    handlers.onError(err instanceof Error ? err.message : "stream interrupted");
  }
}
