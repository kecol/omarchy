import { spawn } from "node:child_process";
import { readFileSync } from "node:fs";
import { StringDecoder } from "node:string_decoder";
import {
	type Api,
	type AssistantMessage,
	type AssistantMessageEventStream,
	calculateCost,
	collapseSystemMessages,
	createAssistantMessageEventStream,
	getCurrentSystemPrompt,
	getCurrentTools,
	type Model,
	type SimpleStreamOptions,
	type TextContent,
	type ToolCall,
	type TranscriptContext,
} from "@earendil-works/pi-ai/compat";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const PROVIDER = "openshell-codex";
const BASE_URL = "https://chatgpt.com/backend-api";
const RESPONSES_URL = `${BASE_URL}/codex/responses`;

// Catalog contents are non-secret metadata, passed from the host without mounting
// its config directory. The bundled catalog also supports standalone image use.
function loadModels() {
	const raw = process.env.OMARCHY_OPEN_SHELL_MODELS_JSON ??
		readFileSync(new URL("./openshell-codex-models.json", import.meta.url), "utf8");
	const models = JSON.parse(raw);
	if (!Array.isArray(models) || models.length === 0) throw new Error("OpenShell model catalog must be a nonempty array");
	const ids = new Set<string>();
	for (const model of models) {
		if (typeof model.id !== "string" || !model.id || ids.has(model.id) ||
			typeof model.name !== "string" || typeof model.reasoning !== "boolean" ||
			JSON.stringify(model.input) !== '["text"]' ||
			!Number.isInteger(model.contextWindow) || model.contextWindow <= 0 ||
			!Number.isInteger(model.maxTokens) || model.maxTokens <= 0 ||
			!["input", "output", "cacheRead", "cacheWrite"].every((key) =>
				typeof model.cost?.[key] === "number" && Number.isFinite(model.cost[key]) && model.cost[key] >= 0)) {
			throw new Error("Invalid OpenShell model catalog entry (unique ID, text input, limits and costs required)");
		}
		ids.add(model.id);
	}
	return models;
}

function textFromContent(content: any): string {
	if (typeof content === "string") return content;
	if (!Array.isArray(content)) return "";
	return content
		.map((part) => {
			if (part?.type === "text") return part.text ?? "";
			if (part?.type === "toolResult") return part.content ?? "";
			return "";
		})
		.filter(Boolean)
		.join("\n");
}

export function toResponsesInput(context: TranscriptContext) {
	const input: any[] = [];
	for (const message of collapseSystemMessages(context).messages) {
		if (message.role === "toolResult") {
			// Tool results are messages, not content blocks in user messages.
			const [callId] = message.toolCallId.split("|");
			input.push({ type: "function_call_output", call_id: callId, output: textFromContent(message.content) });
		} else if (message.role === "user") {
			input.push({ role: "user", content: [{ type: "input_text", text: textFromContent(message.content) }] });
		} else if (message.role === "assistant") {
			for (const part of message.content) {
				if (part.type === "text" && part.text) {
					input.push({ role: "assistant", content: [{ type: "output_text", text: part.text }] });
				} else if (part.type === "toolCall") {
					const [callId, itemId] = part.id.split("|");
					input.push({ type: "function_call", ...(itemId ? { id: itemId } : {}),
						call_id: callId, name: part.name, arguments: JSON.stringify(part.arguments) });
				}
			}
		}
	}
	return input;
}

function strictSchema(schema: any): any {
	if (!schema || typeof schema !== "object" || Array.isArray(schema)) return schema;
	const copy: any = { ...schema };
	if (copy.type === "object" || copy.properties) {
		copy.type = copy.type ?? "object";
		copy.additionalProperties = false;
		copy.properties = Object.fromEntries(Object.entries(copy.properties ?? {}).map(([key, value]) => [key, strictSchema(value)]));
		copy.required = Object.keys(copy.properties);
	}
	if (Array.isArray(copy.anyOf)) copy.anyOf = copy.anyOf.map(strictSchema);
	if (copy.items) copy.items = strictSchema(copy.items);
	return copy;
}

function toResponsesTools(tools: any[]) {
	return tools.map((tool) => ({
		type: "function",
		name: tool.name,
		description: tool.description,
		parameters: strictSchema(tool.parameters),
		strict: true,
	}));
}

function parseSseBuffer(buffer: string): { events: any[]; rest: string } {
	const events: any[] = [];
	let boundary;
	while ((boundary = buffer.indexOf("\n\n")) >= 0) {
		const raw = buffer.slice(0, boundary);
		buffer = buffer.slice(boundary + 2);
		const data = raw
			.split("\n")
			.filter((line) => line.startsWith("data:"))
			.map((line) => line.slice(5).trimStart())
			.join("\n");
		if (!data || data === "[DONE]") continue;
		try {
			events.push(JSON.parse(data));
		} catch {}
	}
	return { events, rest: buffer };
}

async function curlResponses(accessToken: string, payload: any, signal?: AbortSignal) {
	let stderr = "";
	let sseBuffer = "";
	let text = "";
	let usage: any = null;
	let completed = false;
	const decoder = new StringDecoder("utf8");
	if (signal?.aborted) throw new Error("Request was aborted");
	const toolCalls = new Map<string, { id: string; call_id: string; name: string; arguments: string }>();

	await new Promise<void>((resolve, reject) => {
		const child = spawn("curl", [
			"-N",
			"-sS",
			"--fail",
			"--max-time", "120",
			"-H",
			`Authorization: Bearer ${accessToken}`,
			"-H",
			"Content-Type: application/json",
			"-H",
			"Accept: text/event-stream",
			RESPONSES_URL,
			"-d",
			"@-",
		]);
		const abort = () => child.kill("SIGTERM");
		signal?.addEventListener("abort", abort, { once: true });
		if (signal?.aborted) abort();
		child.stdin.on("error", reject);
		child.stdin.end(JSON.stringify(payload));
		child.stderr.on("data", (chunk) => {
			stderr += chunk.toString();
		});
		child.stdout.on("data", (chunk) => {
			sseBuffer += decoder.write(chunk).replace(/\r\n/g, "\n");
			const parsed = parseSseBuffer(sseBuffer);
			sseBuffer = parsed.rest;
			for (const event of parsed.events) {
				if (event.type === "response.output_item.added" && event.item?.type === "function_call") {
					toolCalls.set(event.item.id, { id: event.item.id, call_id: event.item.call_id, name: event.item.name, arguments: "" });
				} else if (event.type === "response.function_call_arguments.delta") {
					const call = toolCalls.get(event.item_id);
					if (call) call.arguments += event.delta ?? "";
				} else if (event.type === "response.function_call_arguments.done") {
					const call = toolCalls.get(event.item_id);
					if (call) call.arguments = event.arguments ?? call.arguments;
				} else if (event.type === "response.output_item.done" && event.item?.type === "function_call") {
					toolCalls.set(event.item.id, {
						id: event.item.id,
						call_id: event.item.call_id,
						name: event.item.name,
						arguments: event.item.arguments ?? toolCalls.get(event.item.id)?.arguments ?? "{}",
					});
				} else if (event.type === "response.output_text.delta") {
					text += event.delta ?? "";
				} else if (event.type === "response.completed") {
					completed = true;
					usage = event.response?.usage ?? null;
				} else if (event.type === "error") {
					reject(new Error(JSON.stringify(event)));
				}
			}
		});
		child.on("error", reject);
		child.on("close", (code) => {
			signal?.removeEventListener("abort", abort);
			if (signal?.aborted) reject(new Error("Request was aborted"));
			else if (code === 0) resolve();
			else reject(new Error(`curl exited with ${code}${stderr ? `: ${stderr}` : ""}`));
		});
	});

	if (!completed) throw new Error("OpenShell Codex response ended without response.completed");
	return { text, usage, toolCalls: [...toolCalls.values()] };
}

export function streamOpenShellCodex(model: Model<Api>, context: TranscriptContext, options?: SimpleStreamOptions): AssistantMessageEventStream {
	const stream = createAssistantMessageEventStream();

	(async () => {
		const output: AssistantMessage = {
			role: "assistant",
			content: [],
			api: model.api,
			provider: model.provider,
			model: model.id,
			usage: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, totalTokens: 0, cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 } },
			stopReason: "pending",
			timestamp: Date.now(),
		};

		try {
			const accessToken = process.env.OPENSHELL_CODEX_AUTH_ACCESS_TOKEN ?? process.env.CODEX_AUTH_ACCESS_TOKEN;
			if (!accessToken) throw new Error("OpenShell Codex credential is missing from the sandbox environment");
			if (!accessToken.startsWith("openshell:resolve:env:")) throw new Error("OpenShell Codex expected an OpenShell opaque credential handle, not a raw token");

			const transcript = collapseSystemMessages(context);
			const tools = getCurrentTools(transcript.messages);
			const payload: any = {
				model: model.id,
				store: false,
				stream: true,
				instructions: getCurrentSystemPrompt(transcript.messages) ?? "You are a concise assistant.",
				input: toResponsesInput(context),
				text: { verbosity: "low" },
				include: ["reasoning.encrypted_content"],
				tool_choice: "auto",
				parallel_tool_calls: true,
				reasoning: { effort: options?.reasoning ?? "medium", summary: "auto" },
			};
			if (tools.length > 0) payload.tools = toResponsesTools(tools);

			// One model request per stream. Pi, not this provider, owns tool
			// execution, validation, permission hooks and continuation turns.
			const replacement = await options?.onPayload?.(payload, model);
			const result = await curlResponses(accessToken, replacement ?? payload, options?.signal);
			if (options?.signal?.aborted) throw new Error("Request was aborted");
			stream.push({ type: "start", partial: output });
			if (result.text) {
				(output.content as TextContent[]).push({ type: "text", text: "" });
				stream.push({ type: "text_start", contentIndex: 0, partial: output });
				(output.content[0] as TextContent).text = result.text;
				stream.push({ type: "text_delta", contentIndex: 0, delta: result.text, partial: output });
				stream.push({ type: "text_end", contentIndex: 0, content: result.text, partial: output });
			}
			for (const call of result.toolCalls) {
				const args = JSON.parse(call.arguments || "{}");
				const block: ToolCall = { type: "toolCall", id: `${call.call_id}|${call.id}`, name: call.name, arguments: args };
				output.content.push(block);
				const contentIndex = output.content.length - 1;
				stream.push({ type: "toolcall_start", contentIndex, partial: output });
				stream.push({ type: "toolcall_delta", contentIndex, delta: call.arguments, partial: output });
				stream.push({ type: "toolcall_end", contentIndex, toolCall: block, partial: output });
			}
			const finalUsage = result.usage;
			if (finalUsage) {
				output.usage.input = finalUsage.input_tokens ?? 0;
				output.usage.output = finalUsage.output_tokens ?? 0;
				output.usage.cacheRead = finalUsage.input_tokens_details?.cached_tokens ?? 0;
				output.usage.cacheWrite = finalUsage.input_tokens_details?.cache_write_tokens ?? 0;
				output.usage.totalTokens = finalUsage.total_tokens ?? output.usage.input + output.usage.output;
				calculateCost(model, output.usage);
			}
			output.stopReason = result.toolCalls.length > 0 ? "toolUse" : "stop";
			stream.push({ type: "done", reason: output.stopReason, message: output });
			stream.end();
		} catch (error) {
			output.stopReason = options?.signal?.aborted ? "aborted" : "error";
			output.errorMessage = error instanceof Error ? error.message : String(error);
			stream.push({ type: "error", reason: output.stopReason, error: output });
			stream.end();
		}
	})();

	return stream;
}

export default function (pi: ExtensionAPI) {
	pi.registerProvider(PROVIDER, {
		baseUrl: BASE_URL,
		apiKey: "$OPENSHELL_CODEX_AUTH_ACCESS_TOKEN",
		api: "openshell-codex-responses",
		models: loadModels(),
		streamSimple: streamOpenShellCodex,
	});
}
