// Composition Workspace & Coordination Console — frontend logic
const API = "";

const state = {
  currentUserId: null,
  documents: [],
  selectedDocId: null,
  tasks: [],
};

// ---------- Bootstrapping: ensure we have a "current user" ----------
async function bootstrapUser() {
  let userId = localStorage.getItem("cwcc_user_id");
  if (userId) {
    state.currentUserId = parseInt(userId, 10);
    return;
  }
  const users = await fetchJSON("/users");
  if (users.length > 0) {
    state.currentUserId = users[0].id;
  } else {
    const created = await fetchJSON("/users", {
      method: "POST",
      body: JSON.stringify({ name: "You", email: `you-${Date.now()}@local.workspace`, role: "writer" }),
    });
    state.currentUserId = created.id;
  }
  localStorage.setItem("cwcc_user_id", state.currentUserId);
}

async function fetchJSON(path, options = {}) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`${res.status}: ${errText}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

function timeAgo(iso) {
  const diff = (Date.now() - new Date(iso + "Z").getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

// ---------- Mode switching ----------
function switchMode(mode) {
  document.querySelectorAll(".mode-btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.mode === mode);
    b.setAttribute("aria-selected", b.dataset.mode === mode ? "true" : "false");
  });
  document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
  document.getElementById(`view-${mode}`).classList.add("active");
  if (mode === "console") loadConsole();
}

document.querySelectorAll(".mode-btn").forEach((btn) => {
  btn.addEventListener("click", () => switchMode(btn.dataset.mode));
});

// ================= WORKSPACE =================
async function loadDocuments() {
  const statusFilter = document.getElementById("statusFilter").value;
  const qs = statusFilter ? `?status=${statusFilter}` : "";
  state.documents = await fetchJSON(`/documents${qs}`);
  renderDocList();
}

function renderDocList() {
  const list = document.getElementById("docList");
  list.innerHTML = "";
  if (state.documents.length === 0) {
    list.innerHTML = `<li style="color:var(--text-dim); font-size:13px; padding:8px 0;">No manuscripts yet.</li>`;
    return;
  }
  for (const doc of state.documents) {
    const li = document.createElement("li");
    li.className = "doc-list-item" + (doc.id === state.selectedDocId ? " selected" : "");
    li.innerHTML = `
      <span class="title">${escapeHtml(doc.title || "Untitled")}</span>
      <span class="meta">
        <span class="status-badge status-${doc.status}">${doc.status.replace("_", " ")}</span>
        <span>v${doc.version}</span>
      </span>`;
    li.addEventListener("click", () => selectDocument(doc.id));
    list.appendChild(li);
  }
}

document.getElementById("statusFilter").addEventListener("change", loadDocuments);

document.getElementById("newDocBtn").addEventListener("click", async () => {
  const doc = await fetchJSON("/documents", {
    method: "POST",
    body: JSON.stringify({ title: "Untitled composition", content: "", owner_id: state.currentUserId }),
  });
  await loadDocuments();
  selectDocument(doc.id);
});

const STATUS_OPTIONS = ["draft", "in_review", "approved", "published"];

async function selectDocument(id) {
  state.selectedDocId = id;
  renderDocList();
  const doc = await fetchJSON(`/documents/${id}`);
  document.getElementById("editorEmpty").hidden = true;
  document.getElementById("editorFull").hidden = false;

  document.getElementById("docTitle").value = doc.title;
  document.getElementById("docContent").value = doc.content;
  document.getElementById("versionTag").textContent = `v${doc.version} · updated ${timeAgo(doc.updated_at)}`;

  const statusSelect = document.getElementById("docStatus");
  statusSelect.innerHTML = STATUS_OPTIONS.map(
    (s) => `<option value="${s}" ${s === doc.status ? "selected" : ""}>${s.replace("_", " ")}</option>`
  ).join("");

  await loadVersions(id);
  await loadComments(id);
}

document.getElementById("saveDocBtn").addEventListener("click", async () => {
  const id = state.selectedDocId;
  if (!id) return;
  const payload = {
    title: document.getElementById("docTitle").value,
    content: document.getElementById("docContent").value,
    status: document.getElementById("docStatus").value,
    editor_id: state.currentUserId,
  };
  await fetchJSON(`/documents/${id}`, { method: "PUT", body: JSON.stringify(payload) });
  await loadDocuments();
  await selectDocument(id);
});

document.getElementById("deleteDocBtn").addEventListener("click", async () => {
  const id = state.selectedDocId;
  if (!id) return;
  if (!confirm("Delete this manuscript permanently?")) return;
  await fetchJSON(`/documents/${id}`, { method: "DELETE" });
  state.selectedDocId = null;
  document.getElementById("editorEmpty").hidden = false;
  document.getElementById("editorFull").hidden = true;
  await loadDocuments();
});

async function loadVersions(docId) {
  const versions = await fetchJSON(`/documents/${docId}/versions`);
  const list = document.getElementById("versionList");
  list.innerHTML = versions
    .map(
      (v) =>
        `<li><span class="v-num">v${v.version_number}</span>${timeAgo(v.created_at)}
         — <a href="#" data-restore="${v.version_number}" style="color:var(--brass-dim);">restore</a></li>`
    )
    .join("") || `<li style="color:var(--paper-dim);">No versions yet.</li>`;

  list.querySelectorAll("[data-restore]").forEach((a) => {
    a.addEventListener("click", async (e) => {
      e.preventDefault();
      const versionNum = a.dataset.restore;
      await fetchJSON(`/documents/${docId}/versions/${versionNum}/restore`, { method: "POST" });
      await selectDocument(docId);
    });
  });
}

async function loadComments(docId) {
  const comments = await fetchJSON(`/documents/${docId}/comments`);
  const list = document.getElementById("commentList");
  list.innerHTML = comments
    .map(
      (c) =>
        `<li class="${c.resolved ? "resolved" : ""}" data-id="${c.id}">
          ${escapeHtml(c.text)}
          <div style="font-size:11px; color:var(--paper-dim); margin-top:2px;">
            ${timeAgo(c.created_at)} ${!c.resolved ? '· <a href="#" data-resolve="' + c.id + '" style="color:var(--brass-dim);">resolve</a>' : ""}
          </div>
        </li>`
    )
    .join("") || `<li style="color:var(--paper-dim);">No comments yet.</li>`;

  list.querySelectorAll("[data-resolve]").forEach((a) => {
    a.addEventListener("click", async (e) => {
      e.preventDefault();
      await fetchJSON(`/documents/comments/${a.dataset.resolve}/resolve`, { method: "PATCH" });
      await loadComments(docId);
    });
  });
}

document.getElementById("commentForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("commentInput");
  if (!input.value.trim()) return;
  await fetchJSON(`/documents/${state.selectedDocId}/comments`, {
    method: "POST",
    body: JSON.stringify({ author_id: state.currentUserId, text: input.value }),
  });
  input.value = "";
  await loadComments(state.selectedDocId);
});

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ================= CONSOLE =================
async function loadConsole() {
  await Promise.all([loadDashboardSummary(), loadTasks(), populateTaskDocumentSelect()]);
}

async function loadDashboardSummary() {
  const summary = await fetchJSON("/dashboard/summary");
  const stats = document.getElementById("consoleStats");
  stats.innerHTML = `
    <div class="stat-card">
      <div class="num">${summary.total_documents}</div>
      <div class="label">Documents</div>
    </div>
    <div class="stat-card">
      <div class="num">${summary.total_tasks}</div>
      <div class="label">Tasks</div>
    </div>
    <div class="stat-card ${summary.overdue_tasks > 0 ? "warn" : ""}">
      <div class="num">${summary.overdue_tasks}</div>
      <div class="label">Overdue</div>
    </div>
    <div class="stat-card">
      <div class="num">${summary.total_users}</div>
      <div class="label">Collaborators</div>
    </div>`;

  const feed = document.getElementById("activityFeed");
  feed.innerHTML = summary.recent_activity
    .map(
      (a) =>
        `<li><span class="action">${a.action.replace(/_/g, " ")}</span> — ${escapeHtml(a.details)} <time>${timeAgo(a.timestamp)}</time></li>`
    )
    .join("") || `<li>No activity yet.</li>`;
}

async function loadTasks() {
  state.tasks = await fetchJSON("/tasks");
  renderBoard();
}

function renderBoard() {
  const cols = { todo: [], in_progress: [], done: [] };
  for (const t of state.tasks) cols[t.status].push(t);

  for (const status of Object.keys(cols)) {
    const col = document.getElementById(`col-${status}`);
    col.innerHTML = cols[status]
      .map((t) => {
        const overdue =
          t.due_date && new Date(t.due_date + "Z") < new Date() && t.status !== "done";
        return `
        <li class="task-card ${overdue ? "overdue" : ""}" data-id="${t.id}">
          <span class="task-title">${escapeHtml(t.title)}</span>
          <div class="task-meta">
            <select data-task-status="${t.id}">
              <option value="todo" ${t.status === "todo" ? "selected" : ""}>To do</option>
              <option value="in_progress" ${t.status === "in_progress" ? "selected" : ""}>In progress</option>
              <option value="done" ${t.status === "done" ? "selected" : ""}>Done</option>
            </select>
            <span>${t.due_date ? t.due_date.split("T")[0] : "no due date"}</span>
            <a href="#" data-task-delete="${t.id}" class="task-delete" title="Delete task">✕</a>
          </div>
        </li>`;
      })
      .join("");
  }

  document.querySelectorAll("[data-task-status]").forEach((sel) => {
    sel.addEventListener("change", async () => {
      await fetchJSON(`/tasks/${sel.dataset.taskStatus}`, {
        method: "PATCH",
        body: JSON.stringify({ status: sel.value }),
      });
      await loadTasks();
      await loadDashboardSummary();
    });
  });

  document.querySelectorAll("[data-task-delete]").forEach((a) => {
    a.addEventListener("click", async (e) => {
      e.preventDefault();
      if (!confirm("Delete this task?")) return;
      await fetchJSON(`/tasks/${a.dataset.taskDelete}`, { method: "DELETE" });
      await loadTasks();
      await loadDashboardSummary();
    });
  });
}

async function populateTaskDocumentSelect() {
  const sel = document.getElementById("taskDocument");
  sel.innerHTML = `<option value="">— none —</option>` + state.documents
    .map((d) => `<option value="${d.id}">${escapeHtml(d.title)}</option>`)
    .join("");
}

async function openTaskModal() {
  await populateTaskDocumentSelect();
  document.getElementById("taskFileStatus").textContent = "";
  document.getElementById("taskFileInput").value = "";
  document.getElementById("taskModal").hidden = false;
}

document.getElementById("newTaskBtn").addEventListener("click", openTaskModal);
document.getElementById("newTaskBtnDashboard").addEventListener("click", openTaskModal);
document.getElementById("taskCancelBtn").addEventListener("click", () => {
  document.getElementById("taskModal").hidden = true;
});

// Browse & upload a file to create a linked document on the fly
document.getElementById("taskFileInput").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  const statusEl = document.getElementById("taskFileStatus");
  if (!file) return;
  statusEl.textContent = "Uploading...";
  try {
    const form = new FormData();
    form.append("file", file);
    form.append("owner_id", state.currentUserId);
    const res = await fetch("/documents/upload", { method: "POST", body: form });
    if (!res.ok) throw new Error(await res.text());
    const doc = await res.json();
    await loadDocuments();
    await populateTaskDocumentSelect();
    document.getElementById("taskDocument").value = String(doc.id);
    statusEl.textContent = `Attached "${doc.title}" as a new document.`;
  } catch (err) {
    statusEl.textContent = "Upload failed — only plain text files are supported.";
  }
});

document.getElementById("taskForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    title: document.getElementById("taskTitle").value,
    description: document.getElementById("taskDescription").value,
    document_id: document.getElementById("taskDocument").value || null,
    due_date: document.getElementById("taskDueDate").value
      ? document.getElementById("taskDueDate").value + "T00:00:00"
      : null,
    assignee_id: state.currentUserId,
  };
  try {
    await fetchJSON("/tasks", { method: "POST", body: JSON.stringify(payload) });
    document.getElementById("taskModal").hidden = true;
    document.getElementById("taskForm").reset();
    document.getElementById("taskFileStatus").textContent = "";
    await loadTasks();
    await loadDashboardSummary();
    switchMode("console");
  } catch (err) {
    alert("Couldn't create the task: " + err.message);
  }
});

// ================= INIT =================
(async function init() {
  await bootstrapUser();
  await loadDocuments();
})();
