import "./styles.css";
import { API_BASE } from "./config";
import { drawDonut } from "./donut";

// TEMP: hardcode your own SteamID64 until it's stored per user
const STEAM_ID = "7656119XXXXXXXXXX";

async function guard(): Promise<boolean> {
  try {
    const token = sessionStorage.getItem("token");
    if (!token) throw new Error("Not signed in");

    const res = await fetch(`${API_BASE}/dashboard`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error("Not signed in");

    console.log(await res.json());
    document.documentElement.classList.remove("checking");
    return true;
  } catch (err) {
    console.error("Guard failed:", err);
    window.location.replace("/");
    return false;
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
  if (await guard()) await loadCharts(STEAM_ID);
}

document.getElementById("logout")?.addEventListener("click", () => {
  sessionStorage.removeItem("token");   // was "auth_token", which never matched
  window.location.replace("/");
});

window.addEventListener("pageshow", (event) => {
  if (event.persisted) void init();
});

void init();