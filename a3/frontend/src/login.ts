import "./styles.css";
import { API_BASE, DASHBOARD_URL } from "./config";

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
    switchText: "have a user? login",
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
  if (
    !username.value.trim() ||
    !password.value ||
    (isRegister && (!email.value.trim() || !email.checkValidity()))
  ) {
    showMessage(
      isRegister ? "Enter a username, a valid email and a password." : "Enter a username and password.",
      "error",
    );
    return;
  }

  submit.disabled = true;
  showMessage("");

  try {
    const payload = isRegister
      ? { username: username.value.trim(), email: email.value.trim(), password: password.value }
      : { username: username.value.trim(), password: password.value };

    const res = await fetch(`${API_BASE}${copy[mode].path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include", // lets the server set its HttpOnly session cookie
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      showMessage(await errorFrom(res), "error");
      return;
    }

    if (mode === "login") {
      window.location.assign(DASHBOARD_URL);
    } else {
      const serverMessage = await messageFrom(res);
      password.value = "";
      email.value = "";
      setMode("login");
      showMessage(serverMessage ?? "User successfully created. Please check your email.", "ok");
}
  } catch {
    showMessage("Could not reach the server. Try again in a moment.", "error");
  } finally {
    submit.disabled = false;
  }
});

switcher.addEventListener("click", () => setMode(mode === "login" ? "register" : "login"));

setMode("login");
