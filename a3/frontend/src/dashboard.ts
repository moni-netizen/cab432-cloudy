import "./styles.css";
import { API_BASE } from "./config";

async function guard(): Promise<void> {
  try {
    const token = sessionStorage.getItem("token");
    if (!token) throw new Error("Not signed in");

    const res = await fetch(`${API_BASE}/dashboard`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error("Not signed in");

    const data = await res.json(); // dashboard content from your Lambda
    console.log(data);             // render this into the page
    document.documentElement.classList.remove("checking");
  } catch {
    window.location.replace("/");
  }
}

document.getElementById("logout")?.addEventListener("click", () => {
  sessionStorage.removeItem("auth_token");
  window.location.replace("/");
});

window.addEventListener("pageshow", (event) => {
  if (event.persisted) void guard();
});

void guard();