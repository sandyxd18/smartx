import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { routes } from "../routes";
import { mockFetch } from "../test/mockFetch";

function renderAt(path: string) {
  mockFetch({});
  render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: [path] })} />);
}

describe("Layout", () => {
  it("shows the main navigation in Indonesian", () => {
    renderAt("/");
    const nav = screen.getByRole("navigation", { name: "Navigasi utama" });
    const labels = Array.from(nav.querySelectorAll("a")).map((a) => a.textContent);
    expect(labels).toEqual(["Dashboard", "Latihan", "Workspace", "Proyek", "Tapeout"]);
  });

  it("navigates to a section", async () => {
    renderAt("/");
    await userEvent.click(screen.getByRole("link", { name: "Latihan" }));
    expect(screen.getByRole("heading", { name: "Latihan" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Latihan" })).toHaveAttribute("aria-current", "page");
  });

  it("shows a not-found page for unknown paths", () => {
    renderAt("/tidak-ada");
    expect(screen.getByRole("heading", { name: "Halaman tidak ditemukan" })).toBeInTheDocument();
  });
});
