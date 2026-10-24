import "./styles.css";
import { API_BASE, DASHBOARD_URL } from "./config";

type AuthResponse = {
  message?: string;
  token?: string;
  user?: {
    userId: string;
    username: string;
    email: string;
    createdAt: string;
    updatedAt: string;
  };
};

async function readJson<T>(res: Response): Promise<T | null> {
  try {
    return (await res.json()) as T;
  } catch {
    return null; // body wasn't JSON
  }
}

type Mode = "login" | "register";

const copy = {
  login: {
    title: "Welcome back!",
    action: "Log in",
    switchText: "Register",
    path: "/auth/login",
    autocomplete: "current-password",
  },
  register: {
    title: "Register user",
    action: "Register",
    switchText: "Have an account? Login",
    path: "/auth/register",
    autocomplete: "new-password",
  },
} as const;

function el<T extends HTMLElement>(id: string): T {
  const node = document.getElementById(id);
  if (!node) throw new Error(`Missing element #${id}`);
  return node as T;
}

const form = el<HTMLFormElement>("auth-form");
const title = el<HTMLElement>("auth-title");
const username = el<HTMLInputElement>("username");
const email = el<HTMLInputElement>("email");
const emailField = el<HTMLElement>("email-field");
const password = el<HTMLInputElement>("password");
const message = el<HTMLElement>("auth-message");
const submit = el<HTMLButtonElement>("auth-submit");
const switcher = el<HTMLButtonElement>("auth-switch");

// Steam ID field: clone the email field so it inherits the same markup and styling
const steamField = emailField.cloneNode(true) as HTMLElement;
steamField.id = "steam-field";
steamField.querySelectorAll("[for]").forEach((n) => n.setAttribute("for", "steamId"));
if (steamField.hasAttribute("for")) steamField.setAttribute("for", "steamId");
const steamLabel = steamField.querySelector(".sr-only");
if (steamLabel) steamLabel.textContent = "Steam ID";

const steamInput = steamField.querySelector("input") as HTMLInputElement;
steamInput.id = "steamId";
steamInput.name = "steamId";
steamInput.type = "text";
steamInput.value = "";
steamInput.placeholder = "Steam ID (17 digits)";
steamInput.inputMode = "numeric";
steamInput.maxLength = 17;
steamInput.autocomplete = "off";
steamInput.required = false;          // validated in the submit handler instead

emailField.after(steamField);         // sits between email and password

let mode: Mode = "login";

function showMessage(text: string, kind: "error" | "ok" | "" = ""): void {
  message.textContent = text;
  message.dataset.kind = kind;
}

function setMode(next: Mode): void {
  mode = next;
  const c = copy[mode];
  document.body.dataset.mode = mode;
  document.title = c.action;
  title.textContent = c.title;
  submit.textContent = c.action;
  switcher.textContent = c.switchText;
  password.autocomplete = c.autocomplete;
  emailField.hidden = mode !== "register";
  steamField.hidden = mode !== "register";
  showMessage("");
}

async function messageFrom(res: Response): Promise<string | null> {
  try {
    const body = (await res.json()) as { message?: string };
    return body.message ?? null;
  } catch {
    return null; // body wasn't JSON
  }
}

async function errorFrom(res: Response): Promise<string> {
  return (
    (await messageFrom(res)) ??
    (mode === "login"
      ? "Login failed. Check your details and try again."
      : "Registration failed. Try a different username.")
  );
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const isRegister = mode === "register";
  const steamId = steamInput.value.trim();
  const steamOk = /^7656119\d{10}$/.test(steamId);
  if (
    !username.value.trim() ||
    !password.value ||
    (isRegister && (!email.value.trim() || !email.checkValidity() || !steamOk))
  ) {
    showMessage(
      isRegister ? "Enter a username, a valid email, a Steam ID and a password." : "Enter a username and password.",
      "error",
    );
    return;
  }

  submit.disabled = true;
  showMessage("");

  try {
    const payload = isRegister
      ? { username: username.value.trim(), email: email.value.trim(), steamId, password: password.value }
      : { username: username.value.trim(), password: password.value };

    const res = await fetch(`${API_BASE}${copy[mode].path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      showMessage(await errorFrom(res), "error");
      return;
    }

    const data = await readJson<AuthResponse>(res);
    if (data?.token) {
      sessionStorage.setItem("token", data.token);
    }

    window.location.assign(DASHBOARD_URL);
  } catch {
    showMessage("Could not reach the server. Try again in a moment.", "error");
  } finally {
    submit.disabled = false;
  }
});

switcher.addEventListener("click", () => setMode(mode === "login" ? "register" : "login"));

setMode("login");
