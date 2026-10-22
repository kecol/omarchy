import { appendFileSync } from "node:fs";
import { createAssistantMessageEventStream } from "@earendil-works/pi-ai/compat";

// Offline-only fake provider. No HTTP client, credentials, or real model calls.
export default function (pi: any) {
  pi.registerProvider("recovery-fixture", {
    api: "openai-completions",
    baseUrl: "http://127.0.0.1:9/unused",
    apiKey: "synthetic-fixture-key",
    models: [{ id: "available-model", name: "Available fixture", reasoning: false,
      input: ["text"], contextWindow: 8192, maxTokens: 1024,
      cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 } }],
    streamSimple: (model: any) => {
      appendFileSync(process.env.MODEL_RECOVERY_CALLS!, "called\n");
      const stream = createAssistantMessageEventStream();
      queueMicrotask(() => {
        const error = { role: "assistant", content: [], api: model.api, provider: model.provider,
          model: model.id, stopReason: "error", errorMessage: "model_not_found: synthetic rejection",
          timestamp: Date.now(), usage: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0,
            totalTokens: 0, cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 } } };
        stream.push({ type: "error", reason: "error", error } as any);
        stream.end();
      });
      return stream;
    },
  });
}
