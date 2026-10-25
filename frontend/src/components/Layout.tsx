import { NavLink, Outlet } from "react-router";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard" },
  { to: "/latihan", label: "Latihan" },
  { to: "/workspace", label: "Workspace" },
  { to: "/proyek", label: "Proyek" },
  { to: "/tapeout", label: "Tapeout" },
] as const;

export function Layout() {
  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-900">
      <aside className="w-56 shrink-0 border-r border-slate-200 bg-white">
        <div className="px-5 py-4 text-lg font-semibold tracking-tight">SmartX</div>
        <nav aria-label="Navigasi utama" className="flex flex-col gap-1 px-3">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `rounded-md px-3 py-2 text-sm ${
                  isActive
                    ? "bg-slate-900 font-medium text-white"
                    : "text-slate-700 hover:bg-slate-100"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="min-w-0 flex-1 p-8">
        <Outlet />
      </main>
    </div>
  );
}
