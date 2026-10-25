import { useState, type ReactNode } from "react";
import type { ProjectEntry } from "../api/client";

export interface FileTreeProps {
  entries: ProjectEntry[];
  /** Path of the open file or the selected folder. */
  selected: string | null;
  /** A file was clicked (open it) or a folder was clicked (select it; it also toggles). */
  onSelect: (entry: ProjectEntry) => void;
  /** Resolve true when done; false keeps the name input open (e.g. the name is taken). */
  onCreate: (kind: ProjectEntry["kind"], path: string) => Promise<boolean>;
  onRename: (from: string, to: string) => Promise<boolean>;
  /** The parent confirms and deletes. */
  onDelete: (entry: ProjectEntry) => void;
}

type Editing =
  | { mode: "create"; kind: ProjectEntry["kind"]; parent: string }
  | { mode: "rename"; entry: ProjectEntry };

function parentOf(path: string): string {
  const slash = path.lastIndexOf("/");
  return slash < 0 ? "" : path.slice(0, slash);
}

function nameOf(path: string): string {
  return path.slice(path.lastIndexOf("/") + 1);
}

function join(parent: string, name: string): string {
  return parent ? `${parent}/${name}` : name;
}

/** Folders first, then files; each group by name, ignoring case. */
function sortEntries(entries: ProjectEntry[]): ProjectEntry[] {
  return [...entries].sort((a, b) => {
    if (a.kind !== b.kind) return a.kind === "dir" ? -1 : 1;
    return nameOf(a.path).localeCompare(nameOf(b.path), undefined, { sensitivity: "base" });
  });
}

export function FileTree(props: FileTreeProps) {
  const { entries, selected } = props;
  const [collapsed, setCollapsed] = useState<ReadonlySet<string>>(new Set());
  const [editing, setEditing] = useState<Editing | null>(null);

  const children = new Map<string, ProjectEntry[]>();
  for (const entry of entries) {
    const parent = parentOf(entry.path);
    children.set(parent, [...(children.get(parent) ?? []), entry]);
  }
  const selectedEntry = entries.find((e) => e.path === selected);

  /** New entries go into the selected folder, or the folder of the selected file. */
  function targetFolder(): string {
    if (!selectedEntry) return "";
    return selectedEntry.kind === "dir" ? selectedEntry.path : parentOf(selectedEntry.path);
  }

  function startCreate(kind: ProjectEntry["kind"]) {
    const parent = targetFolder();
    if (parent) setCollapsed((c) => new Set([...c].filter((p) => p !== parent)));
    setEditing({ mode: "create", kind, parent });
  }

  function toggle(path: string) {
    setCollapsed((c) => {
      const next = new Set(c);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  }

  async function submit(name: string) {
    if (!editing) return;
    const trimmed = name.trim();
    if (editing.mode === "create") {
      if (!trimmed) return setEditing(null);
      if (await props.onCreate(editing.kind, join(editing.parent, trimmed))) setEditing(null);
      return;
    }
    const from = editing.entry.path;
    const to = join(parentOf(from), trimmed);
    if (!trimmed || to === from) return setEditing(null);
    if (await props.onRename(from, to)) setEditing(null);
  }

  function renderLevel(parent: string, depth: number): ReactNode[] {
    const rows: ReactNode[] = [];
    if (editing?.mode === "create" && editing.parent === parent) {
      rows.push(
        <li key="__new" style={{ paddingLeft: `${depth * 12}px` }}>
          <NameInput
            label={editing.kind === "dir" ? "Nama folder baru" : "Nama file baru"}
            initial=""
            onSubmit={submit}
            onCancel={() => setEditing(null)}
          />
        </li>,
      );
    }
    for (const entry of sortEntries(children.get(parent) ?? [])) {
      const isDir = entry.kind === "dir";
      const open = isDir && !collapsed.has(entry.path);
      const renaming = editing?.mode === "rename" && editing.entry.path === entry.path;
      rows.push(
        <li key={entry.path}>
          <div
            className={`group flex items-center gap-1 rounded ${
              entry.path === selected ? "bg-slate-200" : "hover:bg-slate-100"
            }`}
            style={{ paddingLeft: `${depth * 12}px` }}
          >
            {renaming ? (
              <NameInput
                label="Nama baru"
                initial={nameOf(entry.path)}
                onSubmit={submit}
                onCancel={() => setEditing(null)}
              />
            ) : (
              <>
                <button
                  type="button"
                  aria-current={entry.path === selected ? "true" : undefined}
                  onClick={() => {
                    if (isDir) toggle(entry.path);
                    props.onSelect(entry);
                  }}
                  className="min-w-0 flex-1 truncate px-1 py-0.5 text-left font-mono text-xs"
                >
                  {isDir ? `${open ? "▾" : "▸"} ${nameOf(entry.path)}` : nameOf(entry.path)}
                </button>
                <span className="flex shrink-0 gap-1 opacity-0 group-focus-within:opacity-100 group-hover:opacity-100">
                  <button
                    type="button"
                    aria-label={`Ganti nama ${entry.path}`}
                    title="Ganti nama"
                    onClick={() => setEditing({ mode: "rename", entry })}
                    className="px-1 text-xs text-slate-500 hover:text-slate-900"
                  >
                    ✎
                  </button>
                  <button
                    type="button"
                    aria-label={`Hapus ${entry.path}`}
                    title="Hapus"
                    onClick={() => props.onDelete(entry)}
                    className="px-1 text-xs text-slate-500 hover:text-red-700"
                  >
                    ✕
                  </button>
                </span>
              </>
            )}
          </div>
          {open && <ul>{renderLevel(entry.path, depth + 1)}</ul>}
        </li>,
      );
    }
    return rows;
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => startCreate("file")}
          className="rounded border border-slate-300 px-2 py-0.5 text-xs"
        >
          File baru
        </button>
        <button
          type="button"
          onClick={() => startCreate("dir")}
          className="rounded border border-slate-300 px-2 py-0.5 text-xs"
        >
          Folder baru
        </button>
      </div>
      <ul aria-label="File proyek">{renderLevel("", 0)}</ul>
    </div>
  );
}

function NameInput(props: {
  label: string;
  initial: string;
  onSubmit: (name: string) => Promise<void>;
  onCancel: () => void;
}) {
  const [value, setValue] = useState(props.initial);
  return (
    <input
      aria-label={props.label}
      autoFocus
      value={value}
      onChange={(e) => setValue(e.target.value)}
      onKeyDown={(e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          void props.onSubmit(value);
        } else if (e.key === "Escape") {
          props.onCancel();
        }
      }}
      className="w-full rounded border border-slate-400 px-1 py-0.5 font-mono text-xs"
    />
  );
}
