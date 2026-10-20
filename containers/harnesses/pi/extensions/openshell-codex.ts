import { spawn } from "node:child_process";
import { promises as fs } from "node:fs";
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
	type TranscriptContext,
} from "@earendil-works/pi-ai/compat";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const PROVIDER = "openshell-codex";
const BASE_URL = "https://chatgpt.com/backend-api";
const RESPONSES_URL = `${BASE_URL}/codex/responses`;

const MODELS = [
	{
		id: "gpt-5.5",
		name: "GPT-5.5 (OpenShell Codex)",
		reasoning: true,
		input: ["text", "image"],
		cost: { input: 5, output: 30, cacheRead: 0.5, cacheWrite: 0 },
		contextWindow: 272000,
		maxTokens: 128000,
	},
	{
		id: "gpt-5.6-sol",
		name: "GPT-5.6 Sol (OpenShell Codex)",
		reasoning: true,
		input: ["text", "image"],
		cost: { input: 5, output: 30, cacheRead: 0.5, cacheWrite: 0 },
		contextWindow: 272000,
		maxTokens: 128000,
	},
];

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

function toResponsesInput(context: TranscriptContext) {
	const transcript = collapseSystemMessages(context);
	return transcript.messages
		.filter((message) => message.role === "user" || message.role === "assistant")
		.map((message) => ({
			role: message.role,
			content: [{ type: message.role === "assistant" ? "output_text" : "input_text", text: textFromContent((message as any).content) }],
		}));
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
	const toolCalls = new Map<string, { id: string; call_id: string; name: string; arguments: string }>();

	await new Promise<void>((resolve, reject) => {
		const child = spawn("curl", [
			"-N",
			"-sS",
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
		signal?.addEventListener("abort", () => child.kill("SIGTERM"), { once: true });
		child.stdin.end(JSON.stringify(payload));
		child.stderr.on("data", (chunk) => {
			stderr += chunk.toString();
		});
		child.stdout.on("data", (chunk) => {
			sseBuffer += chunk.toString();
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
					usage = event.response?.usage ?? null;
				} else if (event.type === "error") {
					reject(new Error(JSON.stringify(event)));
				}
			}
		});
		child.on("error", reject);
		child.on("close", (code) => {
			if (code === 0) resolve();
			else reject(new Error(`curl exited with ${code}${stderr ? `: ${stderr}` : ""}`));
		});
	});

	return { text, usage, toolCalls: [...toolCalls.values()] };
}

async function executeTool(name: string, args: any): Promise<string> {
	if (name === "bash") {
		return await new Promise((resolve) => {
			const child = spawn("bash", ["-lc", String(args.command ?? "")], { cwd: process.cwd() });
			let stdout = "";
			let stderr = "";
			const timeout = typeof args.timeout === "number" ? setTimeout(() => child.kill("SIGTERM"), args.timeout * 1000) : null;
			child.stdout.on("data", (chunk) => (stdout += chunk.toString()));
			child.stderr.on("data", (chunk) => (stderr += chunk.toString()));
			child.on("close", (code) => {
				if (timeout) clearTimeout(timeout);
				resolve(`${stdout}${stderr ? `\n[stderr]\n${stderr}` : ""}${code ? `\n[exit ${code}]` : ""}`);
			});
		});
	}
	if (name === "read") {
		const data = await fs.readFile(String(args.path), "utf8");
		const lines = data.split(/\r?\n/);
		const start = Math.max(0, Number(args.offset ?? 1) - 1);
		const end = args.limit == null ? lines.length : start + Number(args.limit);
		return lines.slice(start, end).join("\n");
	}
	if (name === "write") {
		await fs.mkdir(String(args.path).split("/").slice(0, -1).join("/") || ".", { recursive: true });
		await fs.writeFile(String(args.path), String(args.content ?? ""));
		return `Wrote ${args.path}`;
	}
	if (name === "edit") {
		const path = String(args.path);
		let content = await fs.readFile(path, "utf8");
		for (const edit of args.edits ?? []) {
			const oldText = String(edit.oldText ?? "");
			const newText = String(edit.newText ?? "");
			const first = content.indexOf(oldText);
			if (first < 0) throw new Error(`edit target not found in ${path}`);
			if (content.indexOf(oldText, first + oldText.length) >= 0) throw new Error(`edit target is not unique in ${path}`);
			content = content.slice(0, first) + newText + content.slice(first + oldText.length);
		}
		await fs.writeFile(path, content);
		return `Edited ${path}`;
	}
	return `Tool ${name} is not implemented by the OpenShell Codex bridge yet.`;
}

function streamOpenShellCodex(model: Model<Api>, context: TranscriptContext, options?: SimpleStreamOptions): AssistantMessageEventStream {
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

			stream.push({ type: "start", partial: output });
			let finalText = "";
			let finalUsage: any = null;
			for (let turn = 0; turn < 6; turn++) {
				const result = await curlResponses(accessToken, payload, options?.signal);
				finalUsage = result.usage ?? finalUsage;
				if (result.toolCalls.length === 0) {
					finalText = result.text;
					break;
				}
				for (const call of result.toolCalls) {
					payload.input.push({ type: "function_call", id: call.id, call_id: call.call_id, name: call.name, arguments: call.arguments });
					let toolOutput: string;
					try {
						toolOutput = await executeTool(call.name, JSON.parse(call.arguments || "{}"));
					} catch (error) {
						toolOutput = error instanceof Error ? error.message : String(error);
					}
					payload.input.push({ type: "function_call_output", call_id: call.call_id, output: toolOutput });
				}
			}

			(output.content as TextContent[]).push({ type: "text", text: "" });
			stream.push({ type: "text_start", contentIndex: 0, partial: output });
			(output.content[0] as TextContent).text = finalText;
			stream.push({ type: "text_delta", contentIndex: 0, delta: finalText, partial: output });
			stream.push({ type: "text_end", contentIndex: 0, content: finalText, partial: output });
			if (finalUsage) {
				output.usage.input = finalUsage.input_tokens ?? 0;
				output.usage.output = finalUsage.output_tokens ?? 0;
				output.usage.cacheRead = finalUsage.input_tokens_details?.cached_tokens ?? 0;
				output.usage.cacheWrite = finalUsage.input_tokens_details?.cache_write_tokens ?? 0;
				output.usage.totalTokens = finalUsage.total_tokens ?? output.usage.input + output.usage.output;
				calculateCost(model, output.usage);
			}
			output.stopReason = "stop";
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
		models: MODELS,
		streamSimple: streamOpenShellCodex,
	});
}
