import "./styles.css";
import "./forum.css";
import { API_BASE } from "./config";

type Msg = {
  messageId: string;
  createdAt: string;
  updatedAt?: string;
  userId: string;
  authorName?: string;
  message: string;
  images?: string[];
  referenceId?: string;
};

const MAX_LEN = 1000;
const MAX_IMAGES = 4;
const MAX_INDENT_DEPTH = 4;

const $ = <T extends HTMLElement>(id: string): T => {
  const n = document.getElementById(id);
  if (!n) throw new Error(`Missing #${id}`);
  return n as T;
};

const feed = $("feed");
const statusEl = $("status");
const composer = $("composer");
const replyingTo = $("replyingTo");
const textBox = $<HTMLTextAreaElement>("msgBody");
const imageRow = $("imageRow");
const imageUrl = $<HTMLInputElement>("imageUrl");
const imageList = $("imageList");
const writeBtn = $<HTMLButtonElement>("writeBtn");
const sendBtn = $<HTMLButtonElement>("send");
const loadMoreBtn = $<HTMLButtonElement>("loadMore");

let me: { userId?: string; username?: string } = {};
let messages: Msg[] = [];
let cursor: string | null = null;
let replyTo: Msg | null = null;
let pendingImages: string[] = [];

function headers(json = false): HeadersInit {
  const h: Record<string, string> = {
    Authorization: `Bearer ${sessionStorage.getItem("token") ?? ""}`,
  };
  if (json) h["Content-Type"] = "application/json";
  return h;
}

function showStatus(text: string, isError = false): void {
  statusEl.textContent = text;
  statusEl.dataset.kind = isError ? "error" : "ok";
}

function isSafeImage(url: string): boolean {
  try {
    return new URL(url).protocol === "https:";
  } catch {
    return false;
  }
}

const authorOf = (m: Msg) => m.authorName || m.userId?.slice(0, 8) || "user";

async function guard(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/dashboard`, { headers: headers() });
    if (!res.ok) throw new Error(String(res.status));
    me = await res.json();
    document.documentElement.classList.remove("checking");
    return true;
  } catch (err) {
    console.error("Guard failed:", err);
    window.location.replace("/");
    return false;
  }
}

async function loadMessages(more = false): Promise<void> {
  const qs = more && cursor ? `?cursor=${encodeURIComponent(cursor)}` : "";
  try {
    const res = await fetch(`${API_BASE}/forum${qs}`, { headers: headers() });
    if (!res.ok) {
      showStatus(`Could not load messages (${res.status}).`, true);
      return;
    }
    const data = await res.json();
    const list: Msg[] = Array.isArray(data) ? data : (data.messages ?? []);
    cursor = Array.isArray(data) ? null : (data.cursor ?? null);
    if (more) {
      const seen = new Set(messages.map((m) => m.messageId));
      messages = messages.concat(list.filter((m) => !seen.has(m.messageId)));
    } else {
      messages = list;
    }
    loadMoreBtn.hidden = !cursor;
    render();
  } catch {
    showStatus("Could not reach the server.", true);
  }
}

function closeMenus(): void {
  document.querySelectorAll<HTMLElement>(".menu-pop").forEach((p) => (p.hidden = true));
  document.querySelectorAll(".dots").forEach((d) => d.setAttribute("aria-expanded", "false"));
}
document.addEventListener("click", closeMenus);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeMenus();
});

// One place that turns backend status codes into messages
function explain(status: number, action: "edit" | "delete"): string {
  switch (status) {
    case 400: return "The server rejected that input.";
    case 401: return "Your session has expired. Please log in again.";
    case 403: return `You can only ${action} your own messages.`;
    case 404: return "That message no longer exists.";
    default:  return `Could not ${action} (${status}).`;
  }
}

function startEdit(m: Msg, textEl: HTMLElement): void {
  const box = document.createElement("div");
  box.className = "edit-box";

  const ta = document.createElement("textarea");
  ta.value = m.message;
  ta.rows = 3;
  ta.maxLength = MAX_LEN;

  const row = document.createElement("div");
  row.className = "row";
  const save = document.createElement("button");
  save.type = "button";
  save.className = "btn small";
  save.textContent = "Save";
  const cancel = document.createElement("button");
  cancel.type = "button";
  cancel.className = "btn small ghost";
  cancel.textContent = "Cancel";

  cancel.addEventListener("click", () => box.replaceWith(textEl));
  save.addEventListener("click", () => void editMessage(m, ta.value.trim(), save));

  row.append(save, cancel);
  box.append(ta, row);
  textEl.replaceWith(box);
  ta.focus();
}

async function editMessage(m: Msg, newText: string, btn: HTMLButtonElement): Promise<void> {
  if (!newText) return showStatus("A message can't be empty.", true);
  if (newText.length > MAX_LEN) return showStatus(`Keep it under ${MAX_LEN} characters.`, true);

  btn.disabled = true;
  try {
    const res = await fetch(`${API_BASE}/forum/${encodeURIComponent(m.messageId)}`, {
      method: "PUT",
      headers: headers(true),
      body: JSON.stringify({ message: newText, images: m.images ?? [] }),
    });
    if (!res.ok) {
      showStatus(explain(res.status, "edit"), true);
      if (res.status === 404) await loadMessages();   // it was deleted elsewhere, so refresh
      return;
    }
    showStatus("Saved.");
    await loadMessages();
  } catch {
    showStatus("Could not reach the server.", true);
  } finally {
    btn.disabled = false;
  }
}

function render(): void {
  const ids = new Set(messages.map((m) => m.messageId));
  const kids = new Map<string, Msg[]>();
  const roots: Msg[] = [];

  for (const m of messages) {
    if (m.referenceId && ids.has(m.referenceId)) {
      const arr = kids.get(m.referenceId) ?? [];
      arr.push(m);
      kids.set(m.referenceId, arr);
    } else {
      roots.push(m); // top-level, or a reply whose parent isn't loaded
    }
  }
  const byTime = (a: Msg, b: Msg) => a.createdAt.localeCompare(b.createdAt);
  roots.sort((a, b) => byTime(b, a)); // newest thread first
  kids.forEach((arr) => arr.sort(byTime)); // replies oldest first

  const build = (m: Msg, depth: number): HTMLElement => {
    const thread = document.createElement("div");
    thread.className = "thread";

    const card = document.createElement("article");
    card.className = depth === 0 ? "msg main" : "msg reply";

    const head = document.createElement("header");
    const who = document.createElement("span");
    who.className = "who";
    who.textContent = authorOf(m);
    const when = document.createElement("span");
    when.className = "when";
    const edited = m.updatedAt && m.updatedAt !== m.createdAt ? " (edited)" : "";
    when.textContent = new Date(m.createdAt).toLocaleString() + edited;
    head.append(who, when);

    const text = document.createElement("p");
    text.className = "text";
    text.textContent = m.message; // textContent, so posts can't inject HTML

    card.append(head, text);

    const safeImages = (m.images ?? []).filter(isSafeImage);
    if (safeImages.length) {
      const imgs = document.createElement("div");
      imgs.className = "imgs";
      for (const url of safeImages) {
        const img = document.createElement("img");
        img.src = url;
        img.alt = "attached image";
        img.loading = "lazy";
        img.referrerPolicy = "no-referrer";
        imgs.append(img);
      }
      card.append(imgs);
    }

        const actions = document.createElement("div");
    actions.className = "actions";
    const replyBtn = document.createElement("button");
    replyBtn.type = "button";
    replyBtn.className = "link";
    replyBtn.textContent = "Reply";
    replyBtn.addEventListener("click", () => openComposer(m));
    actions.append(replyBtn);

    // "..." menu with Edit / Delete (the backend decides who is allowed)
    const menu = document.createElement("div");
    menu.className = "menu";
    const dots = document.createElement("button");
    dots.type = "button";
    dots.className = "dots";
    dots.textContent = "…";
    dots.setAttribute("aria-label", "Message options");
    dots.setAttribute("aria-haspopup", "true");
    dots.setAttribute("aria-expanded", "false");

    const pop = document.createElement("div");
    pop.className = "menu-pop";
    pop.hidden = true;
    pop.setAttribute("role", "menu");

    const editBtn = document.createElement("button");
    editBtn.type = "button";
    editBtn.textContent = "Edit";
    editBtn.addEventListener("click", () => {
      closeMenus();
      startEdit(m, text);
    });

    const delBtn = document.createElement("button");
    delBtn.type = "button";
    delBtn.className = "danger";
    delBtn.textContent = "Delete";
    delBtn.addEventListener("click", () => {
      closeMenus();
      void deleteMessage(m);
    });

    dots.addEventListener("click", (e) => {
      e.stopPropagation();                 // so the outside-click handler doesn't close it at once
      const willOpen = pop.hidden;
      closeMenus();
      pop.hidden = !willOpen;
      dots.setAttribute("aria-expanded", String(willOpen));
    });

    pop.append(editBtn, delBtn);
    menu.append(dots, pop);
    card.append(menu, actions);
    thread.append(card);

    const children = kids.get(m.messageId) ?? [];
    if (children.length) {
      const box = document.createElement("div");
      box.className = depth >= MAX_INDENT_DEPTH ? "replies flat" : "replies";
      children.forEach((c) => box.append(build(c, depth + 1)));
      thread.append(box);
    }
    return thread;
  };

  if (!roots.length) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "No messages yet. Be the first to write one!";
    feed.replaceChildren(empty);
    return;
  }
  feed.replaceChildren(...roots.map((r) => build(r, 0)));
}

function renderChips(): void {
  imageList.replaceChildren(
    ...pendingImages.map((url, i) => {
      const chip = document.createElement("span");
      chip.className = "chip";
      chip.textContent = new URL(url).hostname + " ";
      const x = document.createElement("button");
      x.type = "button";
      x.textContent = "×";
      x.setAttribute("aria-label", "Remove image");
      x.addEventListener("click", () => {
        pendingImages.splice(i, 1);
        renderChips();
      });
      chip.append(x);
      return chip;
    }),
  );
}

function openComposer(target: Msg | null): void {
  replyTo = target;
  replyingTo.textContent = target
    ? `Replying to ${authorOf(target)}: "${target.message.slice(0, 60)}"`
    : "New message";
  composer.hidden = false;
  writeBtn.hidden = true;
  textBox.focus();
  composer.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function closeComposer(): void {
  composer.hidden = true;
  writeBtn.hidden = false;
  replyTo = null;
  pendingImages = [];
  textBox.value = "";
  imageUrl.value = "";
  imageRow.hidden = true;
  renderChips();
}

async function deleteMessage(m: Msg): Promise<void> {
  if (!confirm("Delete this message?")) return;
  try {
    const res = await fetch(`${API_BASE}/forum/${encodeURIComponent(m.messageId)}`, {
      method: "DELETE",
      headers: headers(),
    });
    if (!res.ok) {
      showStatus(res.status === 403 ? "You can only delete your own messages." : `Delete failed (${res.status}).`, true);
      return;
    }
    showStatus("Deleted.");
    await loadMessages();
  } catch {
    showStatus("Could not reach the server.", true);
  }
}

function addImage(): void {
  const url = imageUrl.value.trim();
  if (!isSafeImage(url)) return showStatus("Image URL must start with https://", true);
  if (pendingImages.length >= MAX_IMAGES) return showStatus(`Up to ${MAX_IMAGES} images.`, true);
  pendingImages.push(url);
  imageUrl.value = "";
  renderChips();
  showStatus("");
}

writeBtn.addEventListener("click", () => openComposer(null));
$("cancel").addEventListener("click", closeComposer);
$("addImage").addEventListener("click", () => {
  imageRow.hidden = !imageRow.hidden;
  if (!imageRow.hidden) imageUrl.focus();
});
$("addImageConfirm").addEventListener("click", addImage);
imageUrl.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    addImage();
  }
});
loadMoreBtn.addEventListener("click", () => void loadMessages(true));

sendBtn.addEventListener("click", async () => {
  const message = textBox.value.trim();
  if (!message) return showStatus("Write something first.", true);
  if (message.length > MAX_LEN) return showStatus(`Keep it under ${MAX_LEN} characters.`, true);

  sendBtn.disabled = true;
  try {
    const res = await fetch(`${API_BASE}/forum`, {
      method: "POST",
      headers: headers(true),
      // no userId here: the backend takes it from the verified token
      body: JSON.stringify({ message, images: pendingImages, referenceId: replyTo?.messageId ?? "" }),
    });
    if (!res.ok) {
      showStatus(`Could not send (${res.status}).`, true);
      return;
    }
    closeComposer();
    showStatus("Sent.");
    await loadMessages();
  } catch {
    showStatus("Could not reach the server.", true);
  } finally {
    sendBtn.disabled = false;
  }
});

async function init(): Promise<void> {
  if (await guard()) await loadMessages();
}
window.addEventListener("pageshow", (e) => {
  if (e.persisted) void init();
});
void init();