import { useEffect, useState } from "react";
import "./index.css";
import AdminPortal from "./components/AdminPortal";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8081/api/v1/ml-agri";
const USER_APP_URL = import.meta.env.VITE_USER_APP_URL || "http://127.0.0.1:8080";

export default function App() {
  const [theme, setTheme] = useState(() => {
    const saved = window.localStorage.getItem("nongtri_admin_theme");
    if (saved === "dark" || saved === "light") return saved;
    return "light";
  });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    window.localStorage.setItem("nongtri_admin_theme", theme);
  }, [theme]);

  function toggleTheme() {
    setTheme((current) => (current === "dark" ? "light" : "dark"));
  }

  return <AdminPortal apiBase={API_BASE} userAppUrl={USER_APP_URL} theme={theme} onToggleTheme={toggleTheme} />;
}
