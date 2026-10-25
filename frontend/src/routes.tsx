import type { RouteObject } from "react-router";
import { Layout } from "./components/Layout";
import { ComingSoon, NotFound } from "./pages/ComingSoon";
import { Dashboard } from "./pages/Dashboard";
import { ExerciseList } from "./pages/ExerciseList";
import { ExercisePlaceholder } from "./pages/ExercisePlaceholder";

export const routes: RouteObject[] = [
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: "latihan", element: <ExerciseList /> },
      { path: "latihan/:exerciseId", element: <ExercisePlaceholder /> },
      { path: "workspace", element: <ComingSoon title="Workspace" phase={2} /> },
      { path: "proyek", element: <ComingSoon title="Proyek" phase={4} /> },
      { path: "tapeout", element: <ComingSoon title="Tapeout" phase={6} /> },
      { path: "*", element: <NotFound /> },
    ],
  },
];
