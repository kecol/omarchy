// Metadata-only export: no session, model requests, or credential reads.
import { getModels } from "@earendil-works/pi-ai/compat";
import { writeFileSync } from "node:fs";

export default function () {
	const destination = process.env.OMARCHY_OPEN_SHELL_MODEL_EXPORT;
	if (!destination) throw new Error("Missing model export destination");
	writeFileSync(destination, JSON.stringify(getModels("openai-codex")));
}
