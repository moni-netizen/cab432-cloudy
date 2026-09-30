import "./styles.css";
import { API_BASE } from "./config";

// Show the page only if the server accepts our session cookie.
async function guard(): Promise<void> {
  try {
    const res = await fetch(`${API_BASE}/me`, { credentials: "include" });
    if (!res.ok) throw new Error("Not signed in");
    document.documentElement.classList.remove("checking");
  } catch {
    window.location.replace("/");
  }
}

document.getElementById("logout")?.addEventListener("click", async () => {
  try {
    await fetch(`${API_BASE}/logout`, { method: "POST", credentials: "include" });
  } finally {
    window.location.replace("/");
  }
});

// Back/forward cache can restore this page after logout, so re-check.
window.addEventListener("pageshow", (event) => {
  if (event.persisted) void guard();
});

void guard();
