const BACKEND_URL = window.CANVAS_NOTIFIER_BACKEND_URL || window.location.origin;
const USER_ID_KEY = "canvasNotifier.userId";
const USER_NAME_KEY = "canvasNotifier.userName";

const els = {
  setupForm: document.getElementById("setup-form"),
  name: document.getElementById("name"),
  canvasUrl: document.getElementById("canvas-url"),
  canvasToken: document.getElementById("canvas-token"),
  setupStatus: document.getElementById("setup-status"),
  setupCard: document.getElementById("setup-card"),
  dashCard: document.getElementById("dashboard-card"),
  greeting: document.getElementById("greeting"),
  enableBtn: document.getElementById("enable-notifications"),
  notifStatus: document.getElementById("notif-status"),
  refreshBtn: document.getElementById("refresh-list"),
  list: document.getElementById("assignment-list"),
  switchUserBtn: document.getElementById("switch-user"),
};

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = atob(base64);
  return Uint8Array.from(rawData, (c) => c.charCodeAt(0));
}

async function api(path, options) {
  const res = await fetch(BACKEND_URL + path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Request failed (${res.status})`);
  }
  return data;
}

function getStoredUser() {
  const id = localStorage.getItem(USER_ID_KEY);
  const name = localStorage.getItem(USER_NAME_KEY);
  return id ? { id: Number(id), name } : null;
}

function storeUser(id, name) {
  localStorage.setItem(USER_ID_KEY, id);
  localStorage.setItem(USER_NAME_KEY, name);
}

function clearStoredUser() {
  localStorage.removeItem(USER_ID_KEY);
  localStorage.removeItem(USER_NAME_KEY);
}

function showDashboard(user) {
  els.setupCard.hidden = true;
  els.dashCard.hidden = false;
  els.greeting.textContent = `Hi ${user.name}, here's what's coming up.`;
  loadAssignments(user.id);
}

function showSetup() {
  els.dashCard.hidden = true;
  els.setupCard.hidden = false;
}

function formatDue(dueAtIso) {
  const due = new Date(dueAtIso);
  return due.toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function renderAssignments(items) {
  els.list.innerHTML = "";
  if (items.length === 0) {
    els.list.innerHTML = '<li class="empty">Nothing due soon. Nice.</li>';
    return;
  }
  for (const item of items) {
    const li = document.createElement("li");
    li.className = `item ${item.type}`;
    li.innerHTML = `
      <span class="item-kind">${item.type === "test" ? "Test" : "Assignment"}</span>
      <span class="item-name">${item.name}</span>
      <span class="item-course">${item.course}</span>
      <span class="item-due">${formatDue(item.due_at)}</span>
    `;
    els.list.appendChild(li);
  }
}

async function loadAssignments(userId) {
  els.list.innerHTML = '<li class="empty">Loading...</li>';
  try {
    const data = await api(`/api/assignments/${userId}`);
    renderAssignments(data.items);
  } catch (err) {
    els.list.innerHTML = `<li class="empty error">${err.message}</li>`;
  }
}

async function registerUser(event) {
  event.preventDefault();
  els.setupStatus.textContent = "Checking your Canvas credentials...";
  els.setupStatus.className = "status";
  try {
    const data = await api("/api/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: els.name.value.trim(),
        canvas_url: els.canvasUrl.value.trim(),
        canvas_token: els.canvasToken.value.trim(),
      }),
    });
    storeUser(data.user_id, els.name.value.trim());
    els.setupStatus.textContent = "";
    showDashboard({ id: data.user_id, name: els.name.value.trim() });
  } catch (err) {
    els.setupStatus.textContent = err.message;
    els.setupStatus.className = "status error";
  }
}

async function enableNotifications() {
  const user = getStoredUser();
  if (!user) return;

  if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
    els.notifStatus.textContent = "This browser doesn't support push notifications.";
    els.notifStatus.className = "status error";
    return;
  }

  els.notifStatus.textContent = "Requesting permission...";
  els.notifStatus.className = "status";

  try {
    const permission = await Notification.requestPermission();
    if (permission !== "granted") {
      els.notifStatus.textContent = "Notifications were not allowed.";
      els.notifStatus.className = "status error";
      return;
    }

    const registration = await navigator.serviceWorker.register("sw.js");
    await navigator.serviceWorker.ready;

    const { key } = await api("/api/vapid-public-key");
    let subscription = await registration.pushManager.getSubscription();
    if (!subscription) {
      subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(key),
      });
    }

    const raw = subscription.toJSON();
    await api("/api/push/subscribe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: user.id,
        endpoint: raw.endpoint,
        p256dh: raw.keys.p256dh,
        auth: raw.keys.auth,
      }),
    });

    els.notifStatus.textContent = "Notifications enabled on this device.";
    els.notifStatus.className = "status ok";
  } catch (err) {
    els.notifStatus.textContent = err.message;
    els.notifStatus.className = "status error";
  }
}

els.setupForm.addEventListener("submit", registerUser);
els.enableBtn.addEventListener("click", enableNotifications);
els.refreshBtn.addEventListener("click", () => {
  const user = getStoredUser();
  if (user) loadAssignments(user.id);
});
els.switchUserBtn.addEventListener("click", () => {
  clearStoredUser();
  showSetup();
});

const existingUser = getStoredUser();
if (existingUser) {
  showDashboard(existingUser);
} else {
  showSetup();
}
