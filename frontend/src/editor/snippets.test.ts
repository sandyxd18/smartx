import { describe, expect, it } from "vitest";
import type { Snippet } from "../api/client";
import { applySnippet } from "./snippets";

function snippet(imports: string[], body: string): Snippet {
  return {
    id: "s",
    title: "S",
    description: "",
    language: "python",
    imports,
    body,
  };
}

describe("applySnippet", () => {
  it("adds missing imports after the existing ones and the body at the end", () => {
    const content =
      "import cocotb\nfrom cocotb.triggers import Timer\n\n\nasync def helper():\n    pass\n";
    const result = applySnippet(
      content,
      snippet(
        ["import cocotb", "from collections import deque"],
        "class A:\n    pass\n",
      ),
    );

    expect(result.content).toBe(
      "import cocotb\n" +
        "from cocotb.triggers import Timer\n" +
        "from collections import deque\n" +
        "\n\nasync def helper():\n    pass\n" +
        "\n\nclass A:\n    pass\n",
    );
    // 1-based line where the body starts, to move the cursor there.
    expect(result.line).toBe(10);
  });

  it("puts imports after a module docstring when there are none yet", () => {
    const content = '"""Testbench.\n\nPenjelasan.\n"""\n\nx = 1\n';
    const result = applySnippet(content, snippet(["import random"], "y = 2\n"));

    expect(result.content).toBe(
      '"""Testbench.\n\nPenjelasan.\n"""\nimport random\n\nx = 1\n\n\ny = 2\n',
    );
  });

  it("works on an empty file", () => {
    const result = applySnippet("", snippet(["import cocotb"], "z = 3\n"));
    expect(result.content).toBe("import cocotb\n\n\nz = 3\n");
    expect(result.line).toBe(4);
  });

  it("does not repeat imports that are already there", () => {
    const content = "import cocotb\n";
    const result = applySnippet(content, snippet(["import cocotb"], "z = 3\n"));
    expect(result.content).toBe("import cocotb\n\n\nz = 3\n");
  });
});
