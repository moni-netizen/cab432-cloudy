import "./styles.css";
import { API_BASE } from "./config";
import { drawDonut } from "./donut";

type Me = { username?: string; steamId?: string | null };

type Game = { appid: number; name: string; last_modified: number; image: string };
type GamesResponse = { games: Game[]; cache?: string };

const authHeaders = () => ({
  Authorization: `Bearer ${sessionStorage.getItem("token")}`,
});

async function guard(): Promise<Me | null> {
  try {
    const token = sessionStorage.getItem("token");
    if (!token) throw new Error("Not signed in");

    const res = await fetch(`${API_BASE}/dashboard`, { headers: authHeaders() });
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

function renderProfile(me: Me): void {
  const name = document.getElementById("profileName");
  const steam = document.getElementById("profileSteam");
  if (name) name.textContent = `name: ${me.username ?? ""}`;
  if (steam) steam.textContent = `steam ID: ${me.steamId ?? "not yet implemented"}`;
  const hello = document.getElementById("hello");
  if (hello) hello.textContent = `hello, ${me.username ?? "user"}!`;
}

async function loadCharts(steamId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/games/${steamId}`, { headers: authHeaders() });
  if (!res.ok) { console.error("games fetch failed", res.status); return; }
  const data = await res.json();
  drawDonut("allGamesChart", data.all_games);
  drawDonut("recentGamesChart", data.recent_games);
}

function renderGames(games: Game[]): void {
  const track = document.getElementById("gamesTrack");
  if (!track) return;
  track.replaceChildren();

  if (games.length === 0) {
    const p = document.createElement("p");
    p.textContent = "no games updated this week";
    track.appendChild(p);
    return;
  }

  for (const g of games) {
    const card = document.createElement("div");
    card.className = "game-card";

    const img = document.createElement("img");
    img.src = g.image;
    img.alt = g.name;
    img.loading = "lazy";
    // fall back to a plain placeholder if a header image fails to load
    img.addEventListener("error", () => { img.style.visibility = "hidden"; }, { once: true });

    const title = document.createElement("p");
    title.className = "game-name";
    title.textContent = g.name;
    title.title = `${g.name}\nupdated ${new Date(g.last_modified * 1000).toLocaleString()}`;

    card.append(img, title);
    track.appendChild(card);
  }
}

async function loadRecentlyUpdated(): Promise<void> {
  const res = await fetch(`${API_BASE}/games`, { headers: authHeaders() });
  if (!res.ok) { console.error("updated games fetch failed", res.status); return; }
  const data = (await res.json()) as GamesResponse;
  renderGames(Array.isArray(data.games) ? data.games : []);
}

function setupWheelScroll(): void {
  const track = document.getElementById("gamesTrack");
  if (!track) return;

  track.addEventListener(
    "wheel",
    (e) => {
      // let trackpad sideways swipes scroll natively
      if (Math.abs(e.deltaX) > Math.abs(e.deltaY)) return;

      const atStart = track.scrollLeft <= 0;
      const atEnd = track.scrollLeft + track.clientWidth >= track.scrollWidth - 1;
      // at either end, let the page scroll normally instead of trapping the wheel
      if ((e.deltaY < 0 && atStart) || (e.deltaY > 0 && atEnd)) return;

      e.preventDefault();
      track.scrollLeft += e.deltaY;
    },
    { passive: false }
  );
}

async function init(): Promise<void> {
  const me = await guard();
  if (!me) return;
  renderProfile(me);

  const tasks: Promise<void>[] = [loadRecentlyUpdated()];
  if (me.steamId) tasks.push(loadCharts(me.steamId));
  else console.warn("No Steam ID stored for this user");
  await Promise.all(tasks);
}

document.getElementById("logout")?.addEventListener("click", () => {
  sessionStorage.removeItem("token");
  window.location.replace("/");
});

window.addEventListener("pageshow", (event) => {
  if (event.persisted) void init();
});

setupWheelScroll();
void init();