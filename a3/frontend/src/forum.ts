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
    const res = await fetch(`${API_BASE}/forum/messages${qs}`, { headers: headers() });
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
    when.textContent = new Date(m.createdAt).toLocaleString();
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

    if (me.userId && m.userId === me.userId) {
      const del = document.createElement("button");
      del.type = "button";
      del.className = "link danger";
      del.textContent = "Delete";
      del.addEventListener("click", () => void deleteMessage(m));
      actions.append(del);
    }
    card.append(actions);
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
    const res = await fetch(`${API_BASE}/forum/messages/${encodeURIComponent(m.messageId)}`, {
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
    const res = await fetch(`${API_BASE}/forum/messages`, {
      method: "PUT",
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