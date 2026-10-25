import { useCallback, useEffect, useState } from "react";
import { api, type ConfigRead, type ProjectConfig } from "../api/client";
import { apiErrorMessage, UNREACHABLE } from "../api/errors";
import { type SaveFn, useAutosave } from "../hooks/useAutosave";
import { CodeEditor } from "./CodeEditor";
import type { EditorDiagnostic } from "./codeEditorTypes";
import { SaveIndicator } from "./SaveIndicator";

export interface ConfigEditorProps {
  projectId: number;
  /** smartx.yaml as the page holds it (the YAML editor's content). */
  text: string;
  /** Python files in the project, offered as testbenches. */
  pyFiles: string[];
  /** YAML typed in the editor; the page autosaves it like any file. */
  onEdit: (text: string) => void;
  /** The form saved smartx.yaml; the page shows this text without saving it again. */
  onSaved: (text: string) => void;
  /** Wait for the page's pending YAML save, so the form never races it. */
  settleText: () => Promise<void>;
  /** Give the page a way to wait for a pending form save (null on unmount). */
  registerSettle: (settle: (() => Promise<void>) | null) => void;
}

type Mode = "form" | "yaml";

interface Row {
  name: string;
  value: string;
}

interface FormState {
  top: string;
  sources: string[];
  tests: string[];
  simulator: ProjectConfig["simulator"];
  parameters: Row[];
  defines: Row[];
  // Edited on the FPGA page, not in this form; carried along so saving keeps it.
  fpga: ProjectConfig["fpga"];
}

function toRows(values: Record<string, number | string>): Row[] {
  return Object.entries(values).map(([name, value]) => ({ name, value: String(value) }));
}

function fromRows(rows: Row[]): Record<string, number | string> {
  const values: Record<string, number | string> = {};
  for (const { name, value } of rows) {
    if (name.trim()) values[name.trim()] = /^-?\d+$/.test(value.trim()) ? Number(value) : value;
  }
  return values;
}

function toForm(config: ProjectConfig): FormState {
  return {
    top: config.top,
    sources: [...config.sources],
    tests: [...config.tests],
    simulator: config.simulator,
    parameters: toRows(config.parameters),
    defines: toRows(config.defines),
    fpga: config.fpga,
  };
}

function toConfig(form: FormState): ProjectConfig {
  return {
    top: form.top.trim(),
    sources: form.sources.map((s) => s.trim()).filter(Boolean),
    tests: form.tests,
    simulator: form.simulator,
    parameters: fromRows(form.parameters),
    defines: fromRows(form.defines),
    fpga: form.fpga,
  };
}

export function ConfigEditor(props: ConfigEditorProps) {
  const { projectId, text, settleText, onSaved, registerSettle } = props;
  const [mode, setMode] = useState<Mode | null>(null);
  const [analysis, setAnalysis] = useState<ConfigRead | null>(null);
  const [form, setForm] = useState<FormState | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const check = useCallback(
    async (yaml: string): Promise<ConfigRead | null> => {
      try {
        const { data } = await api.POST("/api/projects/{project_id}/config/check", {
          params: { path: { project_id: projectId } },
          body: { text: yaml },
        });
        return data ?? null;
      } catch {
        return null;
      }
    },
    [projectId],
  );

  const saveForm = useCallback<SaveFn<ProjectConfig>>(
    async (config, { keepalive }) => {
      await settleText();
      let result;
      try {
        result = await api.PUT("/api/projects/{project_id}/config", {
          params: { path: { project_id: projectId } },
          body: config,
          keepalive,
        });
      } catch {
        setFormError(UNREACHABLE);
        throw new Error(UNREACHABLE);
      }
      const { data, error, response } = result;
      if (!data) {
        const message = apiErrorMessage(error, response.status);
        setFormError(message);
        throw new Error(message);
      }
      setFormError(null);
      setAnalysis(data);
      onSaved(data.text);
    },
    [projectId, settleText, onSaved],
  );
  const formSave = useAutosave(saveForm, 600);
  const { settle: settleForm } = formSave;

  useEffect(() => {
    registerSettle(settleForm);
    return () => registerSettle(null);
  }, [registerSettle, settleForm]);

  // Outside the form, check the YAML as it is typed (it is not saved by this).
  useEffect(() => {
    if (mode === "form") return;
    let cancelled = false;
    const timer = setTimeout(() => {
      void check(text).then((result) => {
        if (cancelled || !result) return;
        setAnalysis(result);
        if (mode === null) {
          // First look: the form if the file is valid, otherwise the YAML to fix it.
          setMode(result.config ? "form" : "yaml");
          if (result.config) setForm(toForm(result.config));
        }
      });
    }, 300);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [mode, text, check]);

  async function showForm() {
    await settleText();
    const result = await check(text);
    if (result) setAnalysis(result);
    setForm(result?.config ? toForm(result.config) : null);
    setMode("form");
  }

  async function showYaml() {
    await settleForm();
    setMode("yaml");
  }

  function editForm(next: FormState) {
    setForm(next);
    formSave.schedule(toConfig(next));
  }

  if (mode === null) return <p className="p-4 text-sm text-slate-500">Membaca smartx.yaml…</p>;

  const problems = analysis?.problems ?? [];
  const markers: EditorDiagnostic[] = problems.flatMap((p) =>
    p.line === null || p.line === undefined
      ? []
      : [{ line: p.line, severity: p.severity, message: p.message }],
  );

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center gap-3 border-b border-slate-200 px-3 py-1.5">
        <span className="font-mono text-xs text-slate-600">smartx.yaml</span>
        <div role="tablist" aria-label="Mode konfigurasi" className="flex gap-1">
          {(["form", "yaml"] as const).map((m) => (
            <button
              key={m}
              type="button"
              role="tab"
              aria-selected={mode === m}
              onClick={() => void (m === "form" ? showForm() : showYaml())}
              className={`rounded px-2 py-0.5 text-xs ${
                mode === m ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              {m === "form" ? "Form" : "YAML"}
            </button>
          ))}
        </div>
        {mode === "form" && <SaveIndicator status={formSave.status} />}
      </div>

      <div className="min-h-0 flex-1 overflow-auto">
        {mode === "yaml" ? (
          <div className="h-full min-h-64">
            <CodeEditor
              value={text}
              onChange={props.onEdit}
              language="yaml"
              diagnostics={markers}
            />
          </div>
        ) : form ? (
          <ConfigForm
            form={form}
            onChange={editForm}
            pyFiles={props.pyFiles}
            sources={analysis?.sources ?? []}
            error={formError}
          />
        ) : (
          <p className="p-4 text-sm text-red-700">
            smartx.yaml belum valid. Perbaiki error di mode YAML, lalu buka form lagi.
          </p>
        )}
      </div>

      {problems.length > 0 && (
        <ul
          aria-label="Masalah konfigurasi"
          className="max-h-32 space-y-0.5 overflow-auto border-t border-slate-200 px-3 py-2 text-xs"
        >
          {problems.map((p, i) => (
            <li key={i} className={p.severity === "error" ? "text-red-700" : "text-amber-800"}>
              {p.line ? `Baris ${p.line}: ` : ""}
              {p.message}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

const INPUT = "rounded-md border border-slate-300 px-2 py-1 font-mono text-xs";
const SMALL_BUTTON = "rounded border border-slate-300 px-2 py-0.5 text-xs";

function ConfigForm(props: {
  form: FormState;
  onChange: (form: FormState) => void;
  pyFiles: string[];
  sources: string[];
  error: string | null;
}) {
  const { form, onChange } = props;
  // Focus a row the user just added (not the rows that were there on load).
  const [addedSource, setAddedSource] = useState(false);
  const testChoices = [...new Set([...props.pyFiles, ...form.tests])].sort();

  return (
    <div className="flex max-w-2xl flex-col gap-5 p-4 text-sm">
      {props.error && <p className="text-red-700">Belum tersimpan: {props.error}</p>}

      <label className="flex flex-col gap-1">
        <span className="font-medium">Modul top</span>
        <input
          aria-label="Modul top"
          value={form.top}
          onChange={(e) => onChange({ ...form, top: e.target.value })}
          className={`${INPUT} max-w-64`}
        />
      </label>

      <fieldset className="flex flex-col gap-1">
        <legend className="font-medium">Simulator</legend>
        <div className="flex gap-4">
          {(["icarus", "verilator"] as const).map((sim) => (
            <label key={sim} className="flex items-center gap-1">
              <input
                type="radio"
                name="simulator"
                checked={form.simulator === sim}
                onChange={() => onChange({ ...form, simulator: sim })}
              />
              {sim === "icarus" ? "Icarus" : "Verilator"}
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset className="flex flex-col gap-1">
        <legend className="font-medium">File sumber (pola glob)</legend>
        {form.sources.map((pattern, i) => (
          <div key={i} className="flex gap-2">
            <input
              aria-label={`Pola sumber ${i + 1}`}
              autoFocus={addedSource && i === form.sources.length - 1}
              value={pattern}
              onChange={(e) =>
                onChange({
                  ...form,
                  sources: form.sources.map((p, j) => (j === i ? e.target.value : p)),
                })
              }
              className={`${INPUT} flex-1`}
            />
            <button
              type="button"
              aria-label={`Hapus pola sumber ${i + 1}`}
              disabled={form.sources.length === 1}
              onClick={() => onChange({ ...form, sources: form.sources.filter((_, j) => j !== i) })}
              className={SMALL_BUTTON}
            >
              ✕
            </button>
          </div>
        ))}
        <div>
          <button
            type="button"
            onClick={() => {
              setAddedSource(true);
              onChange({ ...form, sources: [...form.sources, ""] });
            }}
            className={SMALL_BUTTON}
          >
            Tambah pola
          </button>
        </div>
        <p className="text-xs text-slate-500">
          <code>*</code> dalam satu folder, <code>**</code> lintas folder. Cocok (
          {props.sources.length}):{" "}
          {props.sources.length ? props.sources.join(", ") : "tidak ada"}
        </p>
      </fieldset>

      <fieldset className="flex flex-col gap-1">
        <legend className="font-medium">Testbench cocotb</legend>
        {testChoices.length === 0 && (
          <p className="text-xs text-slate-500">Belum ada file .py di proyek.</p>
        )}
        {testChoices.map((path) => (
          <label key={path} className="flex items-center gap-2 font-mono text-xs">
            <input
              type="checkbox"
              checked={form.tests.includes(path)}
              onChange={(e) =>
                onChange({
                  ...form,
                  tests: e.target.checked
                    ? [...form.tests, path]
                    : form.tests.filter((t) => t !== path),
                })
              }
            />
            {path}
            {!props.pyFiles.includes(path) && <span className="text-amber-800">(tidak ada)</span>}
          </label>
        ))}
      </fieldset>

      <RowsEditor
        kind="parameter"
        title="Parameter modul top"
        hint="Nilai angka dikirim sebagai angka; selain itu apa adanya, misalnya 8'hFF."
        rows={form.parameters}
        onChange={(parameters) => onChange({ ...form, parameters })}
      />
      <RowsEditor
        kind="define"
        title="Define (`define)"
        hint="Setara dengan -DNAMA=nilai. Untuk penanda tanpa nilai, isi 1."
        rows={form.defines}
        onChange={(defines) => onChange({ ...form, defines })}
      />
    </div>
  );
}

function RowsEditor(props: {
  kind: "parameter" | "define";
  title: string;
  hint: string;
  rows: Row[];
  onChange: (rows: Row[]) => void;
}) {
  const { kind, rows, onChange } = props;
  const [added, setAdded] = useState(false);
  const update = (i: number, patch: Partial<Row>) =>
    onChange(rows.map((row, j) => (j === i ? { ...row, ...patch } : row)));
  return (
    <fieldset className="flex flex-col gap-1">
      <legend className="font-medium">{props.title}</legend>
      {rows.map((row, i) => (
        <div key={i} className="flex gap-2">
          <input
            aria-label={`Nama ${kind} ${i + 1}`}
            autoFocus={added && i === rows.length - 1}
            placeholder="NAMA"
            value={row.name}
            onChange={(e) => update(i, { name: e.target.value })}
            className={`${INPUT} w-40`}
          />
          <input
            aria-label={`Nilai ${kind} ${i + 1}`}
            placeholder="nilai"
            value={row.value}
            onChange={(e) => update(i, { value: e.target.value })}
            className={`${INPUT} flex-1`}
          />
          <button
            type="button"
            aria-label={`Hapus ${kind} ${i + 1}`}
            onClick={() => onChange(rows.filter((_, j) => j !== i))}
            className={SMALL_BUTTON}
          >
            ✕
          </button>
        </div>
      ))}
      <div>
        <button
          type="button"
          aria-label={`Tambah ${kind}`}
          onClick={() => {
            setAdded(true);
            onChange([...rows, { name: "", value: "" }]);
          }}
          className={SMALL_BUTTON}
        >
          Tambah
        </button>
      </div>
      <p className="text-xs text-slate-500">{props.hint}</p>
    </fieldset>
  );
}
