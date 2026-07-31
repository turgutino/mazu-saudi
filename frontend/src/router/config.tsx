import type { RouteObject } from "react-router-dom";
import NotFound from "../pages/NotFound";
import Dashboard from "../pages/home/page";
import Workspace from "../pages/workspace/page";
import PredictionDetail from "../pages/prediction/page";
import KnowledgeGraph from "../pages/graph/page";
import MonitorPage from "../pages/monitor/page";

const routes: RouteObject[] = [
  {
    path: "/",
    element: <Dashboard />,
  },
  {
    path: "/workspace",
    element: <Workspace />,
  },
  {
    path: "/monitor",
    element: <MonitorPage />,
  },
  {
    path: "/prediction/:id",
    element: <PredictionDetail />,
  },
  {
    path: "/prediction/:id/graph",
    element: <KnowledgeGraph />,
  },
  {
    path: "*",
    element: <NotFound />,
  },
];

export default routes;