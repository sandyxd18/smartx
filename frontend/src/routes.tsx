import type { RouteObject } from "react-router";
import { Layout } from "./components/Layout";
import { ComingSoon, NotFound } from "./pages/ComingSoon";
import { Dashboard } from "./pages/Dashboard";
import { ExerciseList } from "./pages/ExerciseList";
import { WorkspaceList } from "./pages/WorkspaceList";

export const routes: RouteObject[] = [
  {
    path: "/",
    element: <Layout />,
    // Opening a lazy route by URL (e.g. a refresh on /latihan/:id) renders this until the
    // route's code has loaded, instead of a blank page.
    hydrateFallbackElement: <p className="p-8 text-sm text-slate-500">Memuat halaman…</p>,
    children: [
      { index: true, element: <Dashboard /> },
      { path: "latihan", element: <ExerciseList /> },
      {
        path: "latihan/:exerciseId",
        // Monaco is large; load the page (and the editor) only when an exercise is opened.
        lazy: async () => ({ Component: (await import("./pages/ExercisePage")).ExercisePage }),
      },
      { path: "workspace", element: <WorkspaceList /> },
      {
        path: "workspace/:projectId",
        lazy: async () => ({ Component: (await import("./pages/ProjectPage")).ProjectPage }),
      },
      { path: "proyek", element: <ComingSoon title="Proyek" phase={4} /> },
      { path: "tapeout", element: <ComingSoon title="Tapeout" phase={6} /> },
      { path: "*", element: <NotFound /> },
    ],
  },
];
