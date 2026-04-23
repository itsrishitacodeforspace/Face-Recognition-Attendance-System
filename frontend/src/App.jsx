import { Component, useEffect, useState } from "react";
import { NavLink, Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import HeatmapPage from "./pages/HeatmapPage";
import TrendsPage from "./pages/TrendsPage";
import PersonsPage from "./pages/PersonsPage";
import AttendancePage from "./pages/AttendancePage";
import LiveRecognitionPage from "./pages/LiveRecognitionPage";
import TrainingPage from "./pages/TrainingPage";
import Login from "./pages/Login";
import { authApi } from "./services/api";

const links = [
  { to: "/", label: "Dashboard" },
  { to: "/heatmap", label: "Heatmap" },
  { to: "/trends", label: "Trends" },
  { to: "/persons", label: "Persons" },
  { to: "/attendance", label: "Attendance" },
  { to: "/live", label: "Live" },
  { to: "/training", label: "Training" },
];

/**
 * Error Boundary component to catch and handle React component errors.
 * Prevents entire app from crashing if a single component fails.
 */
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("Error caught by error boundary:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center p-4">
          <div className="card bg-red-50 border-red-200 max-w-md w-full">
            <h2 className="text-xl font-bold text-red-900 mb-2">Something went wrong</h2>
            <p className="text-red-800 mb-4">
              An unexpected error occurred. Please try refreshing the page.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-red-900 text-white rounded hover:bg-red-800"
            >
              Refresh Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

function Layout() {
  return (
    <div className="min-h-screen p-4 md:p-6">
      <header className="card mb-4">
        <h1 className="font-display text-2xl">Face Recognition Attendance</h1>
        <nav className="mt-3 flex flex-wrap gap-2">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                `px-3 py-2 rounded-lg text-sm ${isActive ? "bg-ink text-white" : "bg-white border border-slate-200"}`
              }
            >
              {link.label}
            </NavLink>
          ))}
          <button
            className="px-3 py-2 rounded-lg bg-white border border-slate-200 text-sm"
            onClick={async () => {
              try {
                await authApi.logout();
              } catch (_err) {
                // Best effort logout.
              }
              sessionStorage.removeItem("is_authed");
              window.location.href = "/login";
            }}
          >
            Logout
          </button>
        </nav>
      </header>
      <ErrorBoundary>
        <Outlet />
      </ErrorBoundary>
    </div>
  );
}

export default function App() {
  const location = useLocation();
  const [isAuthed, setIsAuthed] = useState(sessionStorage.getItem("is_authed") === "1");
  const [checkingAuth, setCheckingAuth] = useState(true);

  useEffect(() => {
    if (location.pathname === "/login") {
      setCheckingAuth(false);
      return;
    }

    let active = true;
    authApi
      .me()
      .then(() => {
        if (!active) return;
        sessionStorage.setItem("is_authed", "1");
        setIsAuthed(true);
      })
      .catch(() => {
        if (!active) return;
        sessionStorage.removeItem("is_authed");
        setIsAuthed(false);
      })
      .finally(() => {
        if (!active) return;
        setCheckingAuth(false);
      });
    return () => {
      active = false;
    };
  }, [location.pathname]);

  if (checkingAuth) {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  }

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={isAuthed ? <Layout /> : <Navigate to="/login" replace />}
      >
        <Route index element={<Dashboard />} />
        <Route path="heatmap" element={<HeatmapPage />} />
        <Route path="trends" element={<TrendsPage />} />
        <Route path="persons" element={<PersonsPage />} />
        <Route path="attendance" element={<AttendancePage />} />
        <Route path="live" element={<LiveRecognitionPage />} />
        <Route path="training" element={<TrainingPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
