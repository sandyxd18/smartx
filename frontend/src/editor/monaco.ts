// Self-hosted Monaco (no CDN, so the editor works offline): the editor features plus
// Monaco's own Monarch grammars for Verilog/SystemVerilog, Python (cocotb), YAML and
// Markdown (project files). The TypeScript/CSS/HTML/JSON
// language services that monaco-editor's main entry pulls in are left out on purpose.
import { loader } from "@monaco-editor/react";
import * as monaco from "monaco-editor/editor/editor.api";
import "monaco-editor/features/register.all";
import "monaco-editor/languages/definitions/systemverilog/register";
import "monaco-editor/languages/definitions/python/register";
import "monaco-editor/languages/definitions/yaml/register";
import "monaco-editor/languages/definitions/markdown/register";
import EditorWorker from "monaco-editor/editor/editor.worker?worker";

self.MonacoEnvironment = { getWorker: () => new EditorWorker() };
loader.config({ monaco });

export { monaco };
