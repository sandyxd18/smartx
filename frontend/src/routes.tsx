import type { RouteObject } from "react-router";
import { Layout } from "./components/Layout";
import { ComingSoon, NotFound } from "./pages/ComingSoon";
import { Dashboard } from "./pages/Dashboard";

export const routes: RouteObject[] = [
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: "latihan", element: <ComingSoon title="Latihan" phase={1} /> },
      { path: "workspace", element: <ComingSoon title="Workspace" phase={2} /> },
      { path: "proyek", element: <ComingSoon title="Proyek" phase={4} /> },
      { path: "tapeout", element: <ComingSoon title="Tapeout" phase={6} /> },
      { path: "*", element: <NotFound /> },
    ],
  },
];
