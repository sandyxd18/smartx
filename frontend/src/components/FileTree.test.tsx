import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ProjectEntry } from "../api/client";
import { FileTree, type FileTreeProps } from "./FileTree";

const ENTRIES: ProjectEntry[] = [
  { path: "README.md", kind: "file" },
  { path: "smartx.yaml", kind: "file" },
  { path: "src", kind: "dir" },
  { path: "src/counter.v", kind: "file" },
  { path: "src/lib", kind: "dir" },
  { path: "test", kind: "dir" },
  { path: "test/test_counter.py", kind: "file" },
];

function setup(overrides: Partial<FileTreeProps> = {}) {
  const props: FileTreeProps = {
    entries: ENTRIES,
    selected: null,
    onSelect: vi.fn(),
    onCreate: vi.fn(() => Promise.resolve(true)),
    onRename: vi.fn(() => Promise.resolve(true)),
    onDelete: vi.fn(),
    ...overrides,
  };
  render(<FileTree {...props} />);
  return props;
}

function row(name: string) {
  return screen.getByRole("button", { name });
}

describe("FileTree", () => {
  it("shows folders before files, nested by depth", () => {
    setup();
    const tree = screen.getByRole("list", { name: "File proyek" });
    const names = within(tree)
      .getAllByRole("button", { name: /^(?!Ganti nama|Hapus)/ })
      .map((b) => b.textContent);
    expect(names).toEqual([
      "▾ src",
      "▾ lib",
      "counter.v",
      "▾ test",
      "test_counter.py",
      "README.md",
      "smartx.yaml",
    ]);
  });

  it("opens a file and collapses a folder", async () => {
    const props = setup();
    await userEvent.click(row("counter.v"));
    expect(props.onSelect).toHaveBeenCalledWith({ path: "src/counter.v", kind: "file" });

    await userEvent.click(row("▾ src"));
    expect(screen.queryByRole("button", { name: "counter.v" })).not.toBeInTheDocument();
    expect(props.onSelect).toHaveBeenCalledWith({ path: "src", kind: "dir" });
  });

  it("creates a file in the folder of the selected file", async () => {
    const props = setup({ selected: "src/counter.v" });

    await userEvent.click(screen.getByRole("button", { name: "File baru" }));
    await userEvent.type(screen.getByRole("textbox", { name: "Nama file baru" }), "alu.v{Enter}");

    expect(props.onCreate).toHaveBeenCalledWith("file", "src/alu.v");
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });

  it("creates a folder at the root when nothing is selected, and Escape cancels", async () => {
    const props = setup();

    await userEvent.click(screen.getByRole("button", { name: "Folder baru" }));
    await userEvent.type(screen.getByRole("textbox", { name: "Nama folder baru" }), "docs{Escape}");
    expect(props.onCreate).not.toHaveBeenCalled();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Folder baru" }));
    await userEvent.type(screen.getByRole("textbox", { name: "Nama folder baru" }), "docs{Enter}");
    expect(props.onCreate).toHaveBeenCalledWith("dir", "docs");
  });

  it("keeps the input open when the parent rejects the name", async () => {
    setup({ selected: "src", onCreate: vi.fn(() => Promise.resolve(false)) });

    await userEvent.click(screen.getByRole("button", { name: "File baru" }));
    await userEvent.type(screen.getByRole("textbox", { name: "Nama file baru" }), "counter.v{Enter}");

    expect(screen.getByRole("textbox", { name: "Nama file baru" })).toHaveValue("counter.v");
  });

  it("renames in place, keeping the folder", async () => {
    const props = setup();

    await userEvent.click(screen.getByRole("button", { name: "Ganti nama src/counter.v" }));
    const input = screen.getByRole("textbox", { name: "Nama baru" });
    expect(input).toHaveValue("counter.v");
    await userEvent.clear(input);
    await userEvent.type(input, "up_counter.v{Enter}");

    expect(props.onRename).toHaveBeenCalledWith("src/counter.v", "src/up_counter.v");
  });

  it("does not call rename when the name is unchanged", async () => {
    const props = setup();
    await userEvent.click(screen.getByRole("button", { name: "Ganti nama test" }));
    await userEvent.type(screen.getByRole("textbox", { name: "Nama baru" }), "{Enter}");
    expect(props.onRename).not.toHaveBeenCalled();
  });

  it("asks the parent to delete", async () => {
    const props = setup();
    await userEvent.click(screen.getByRole("button", { name: "Hapus src" }));
    expect(props.onDelete).toHaveBeenCalledWith({ path: "src", kind: "dir" });
  });

  it("marks the selected entry", () => {
    setup({ selected: "src/counter.v" });
    expect(row("counter.v")).toHaveAttribute("aria-current", "true");
    expect(row("smartx.yaml")).not.toHaveAttribute("aria-current");
  });
});
