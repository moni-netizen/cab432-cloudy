import "./styles.css";
import { API_BASE } from "./config";
import { drawDonut } from "./donut";

type Me = { username?: string; steamId?: string | null };

async function guard(): Promise<Me | null> {
  try {
    const token = sessionStorage.getItem("token");
    if (!token) throw new Error("Not signed in");

    const res = await fetch(`${API_BASE}/dashboard`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error("Not signed in");

    const me = (await res.json()) as Me;
    document.documentElement.classList.remove("checking");
    return me;
  } catch (err) {
    console.error("Guard failed:", err);
    window.location.replace("/");
    return null;
  }
}

async function loadCharts(steamId: string): Promise<void> {
  const token = sessionStorage.getItem("token");
  const res = await fetch(`${API_BASE}/games/${steamId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) { console.error("games fetch failed", res.status); return; }
  const data = await res.json();
  console.log("games data", data);
  drawDonut("allGamesChart", data.all_games);
  drawDonut("recentGamesChart", data.recent_games);
}

async function init(): Promise<void> {
  const me = await guard();
  if (!me) return;
  if (!me.steamId) {
    console.warn("No Steam ID stored for this user");
    return;
  }
  await loadCharts(me.steamId);
}

document.getElementById("logout")?.addEventListener("click", () => {
  sessionStorage.removeItem("token");
  window.location.replace("/");
});

window.addEventListener("pageshow", (event) => {
  if (event.persisted) void init();
});

void init();