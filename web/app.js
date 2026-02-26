const API = {
  get: async (path) => {
    let res;
    try {
      res = await fetch(path);
    } catch (_err) {
      throw new Error(`Failed to fetch ${path}. Start server with: python3 server.py and open http://127.0.0.1:8787`);
    }
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  post: async (path, body = {}) => {
    let res;
    try {
      res = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
    } catch (_err) {
      throw new Error(`Failed to fetch ${path}. Start server with: python3 server.py and open http://127.0.0.1:8787`);
    }
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  patch: async (path, body = {}) => {
    let res;
    try {
      res = await fetch(path, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
    } catch (_err) {
      throw new Error(`Failed to fetch ${path}. Start server with: python3 server.py and open http://127.0.0.1:8787`);
    }
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  delete: async (path) => {
    let res;
    try {
      res = await fetch(path, { method: "DELETE" });
    } catch (_err) {
      throw new Error(`Failed to fetch ${path}. Start server with: python3 server.py and open http://127.0.0.1:8787`);
    }
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }
};

const QUICK_PROMPTS = [
  "Where do I edit my to-dos?",
  "Where are docs for Docker setup?",
  "What phase of onboarding am I in right now?",
  "Who is in charge of cloud permissions?"
];

function setActiveNav() {
  const page = location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll(".top-nav a").forEach((a) => {
    if (a.getAttribute("href") === page) a.classList.add("active");
  });
}

function setupGlobalSearch(inputId = "globalSearch") {
  const input = document.getElementById(inputId);
  if (!input) return;

  input.value = new URLSearchParams(location.search).get("q") || "";
  input.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    window.location.href = `docs.html?q=${encodeURIComponent(input.value.trim())}`;
  });
}

function qs(name) {
  return new URLSearchParams(location.search).get(name) || "";
}

function esc(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function phaseOptions() {
  return ["Complete training", "Unlock all accesses", "Debug codebase", "Commit to GitHub", "Goals complete", "General"];
}

async function loadDashboard() {
  const root = document.getElementById("milestoneList");
  if (!root) return;

  const milestoneList = document.getElementById("milestoneList");
  const progressFill = document.getElementById("progressFill");
  const todoList = document.getElementById("todoList");
  const docList = document.getElementById("docList");
  const quickPrompts = document.getElementById("quickPrompts");
  const chatMessages = document.getElementById("chatMessages");
  const chatForm = document.getElementById("chatForm");
  const chatInput = document.getElementById("chatInput");
  const dashboardTaskForm = document.getElementById("dashboardTaskForm");
  const dashboardTaskInput = document.getElementById("dashboardTaskInput");
  const dashboardTaskPriority = document.getElementById("dashboardTaskPriority");

  const [mData, pData, tData, dData] = await Promise.all([
    API.get("/api/milestones"),
    API.get("/api/progress"),
    API.get("/api/tasks"),
    API.get("/api/documents")
  ]);

  milestoneList.innerHTML = "";
  for (const m of mData.milestones) {
    const item = document.createElement("label");
    item.className = "milestone";
    item.innerHTML = `<input type="checkbox" ${m.done ? "checked" : ""}><span>${esc(m.label)}</span>`;
    item.querySelector("input").addEventListener("change", async (e) => {
      await API.patch(`/api/milestones/${m.id}`, { done: e.target.checked });
      await loadDashboard();
    });
    milestoneList.appendChild(item);
  }

  progressFill.style.width = `${pData.progress}%`;

  todoList.innerHTML = "";
  for (const t of tData.tasks.slice(0, 4)) {
    const li = document.createElement("li");
    li.className = `item ${t.done ? "done" : ""}`;
    li.innerHTML = `<div><div class="title">${esc(t.text)}</div><div class="meta">${esc(t.phase_label)} | Priority: ${esc(t.priority)}${!t.unlocked && !t.done ? " | Locked" : ""}</div></div>`;
    todoList.appendChild(li);
  }
  if (!todoList.children.length) {
    todoList.innerHTML = `<li class="empty-state">No tasks yet. Add one here or open To-Do page.</li>`;
  }

  docList.innerHTML = "";
  const docs = dData.documents.filter((d) => pData.phase === "Goals complete" || d.phase === pData.phase).slice(0, 4);
  for (const d of docs) {
    const anchor = (d.anchors && d.anchors[0]) || { page: 1, paragraph: 1, note: "overview" };
    const li = document.createElement("li");
    li.className = "item";
    li.innerHTML = `
      <div>
        <div class="title">${esc(d.title)}</div>
        <div class="meta">${esc(d.phase)} | read count: ${esc(d.read_count || 0)} | start at page ${esc(anchor.page)} para ${esc(anchor.paragraph)}</div>
      </div>
      <div class="row">
        <button class="ghost" data-action="read">Mark Read</button>
        <button class="ghost" data-action="ask">Find in KB</button>
      </div>
    `;

    li.querySelector('[data-action="read"]').addEventListener("click", async () => {
      await API.post("/api/documents/mark_read", { doc_id: d.id });
      await loadDashboard();
    });
    li.querySelector('[data-action="ask"]').addEventListener("click", () => {
      window.location.href = `docs.html?q=${encodeURIComponent(d.title)}`;
    });

    docList.appendChild(li);
  }
  if (!docList.children.length) {
    docList.innerHTML = `<li class="empty-state">No docs for current phase. Open Docs AI page for guided lookup.</li>`;
  }

  chatMessages.innerHTML = `<div class="message bot">Ask on Docs AI for summary + page/paragraph guidance, or Assistant for conversational Q&A.</div>`;
  quickPrompts.innerHTML = "";
  QUICK_PROMPTS.forEach((prompt) => {
    const b = document.createElement("button");
    b.className = "chip";
    b.type = "button";
    b.textContent = prompt;
    b.addEventListener("click", () => {
      window.location.href = `assistant.html?q=${encodeURIComponent(prompt)}`;
    });
    quickPrompts.appendChild(b);
  });

  chatForm.onsubmit = (e) => {
    e.preventDefault();
    const question = chatInput.value.trim();
    if (!question) return;
    window.location.href = `assistant.html?q=${encodeURIComponent(question)}`;
  };

  dashboardTaskForm.onsubmit = async (e) => {
    e.preventDefault();
    const text = dashboardTaskInput.value.trim();
    if (!text) return;
    await API.post("/api/tasks", {
      text,
      priority: dashboardTaskPriority.value,
      phase_rank: tData.unlocked_phase_rank
    });
    dashboardTaskInput.value = "";
    await loadDashboard();
  };
}

async function loadProgressPage() {
  const root = document.getElementById("progressPage");
  if (!root) return;

  const milestonesEl = document.getElementById("milestonesList");
  const progressFill = document.getElementById("progressFill");
  const progressLabel = document.getElementById("progressLabel");
  const componentsEl = document.getElementById("progressComponents");
  const weeklyPlanList = document.getElementById("weeklyPlanList");
  const weeklyPlanForm = document.getElementById("weeklyPlanForm");
  const weekLabelInput = document.getElementById("weekLabelInput");
  const weekPlanInput = document.getElementById("weekPlanInput");
  const calendarBody = document.getElementById("calendarTableBody");

  async function render() {
    const [mData, pData] = await Promise.all([API.get("/api/milestones"), API.get("/api/progress")]);

    progressFill.style.width = `${pData.progress}%`;
    progressLabel.textContent = `${pData.progress}% complete | current phase: ${pData.phase}`;
    componentsEl.textContent = `Progress mix: milestones ${Math.round(pData.components.milestones * 100)}%, tasks ${Math.round(
      pData.components.tasks * 100
    )}%, docs-read ${Math.round(pData.components.docs_read * 100)}%, weekly plans ${Math.round(pData.components.weekly_plans * 100)}%`;

    milestonesEl.innerHTML = "";
    for (const m of mData.milestones) {
      const li = document.createElement("li");
      li.className = "item";
      li.innerHTML = `<div><div class="title">${esc(m.label)}</div><div class="meta">Rank ${m.rank + 1}</div></div>`;
      const btn = document.createElement("button");
      btn.className = m.done ? "warn" : "primary";
      btn.textContent = m.done ? "Mark Pending" : "Mark Done";
      btn.onclick = async () => {
        await API.patch(`/api/milestones/${m.id}`, { done: !m.done });
        await render();
      };
      li.appendChild(btn);
      milestonesEl.appendChild(li);
    }

    weeklyPlanList.innerHTML = "";
    for (const plan of pData.weekly_plans) {
      const li = document.createElement("li");
      li.className = `item ${plan.done ? "done" : ""}`;
      li.innerHTML = `
        <div>
          <div class="title">${esc(plan.week_label)}</div>
          <div class="meta">${esc(plan.plan_text)}</div>
        </div>
        <div class="row">
          <button class="ghost" data-action="toggle">${plan.done ? "Reopen" : "Done"}</button>
          <button class="danger" data-action="delete">Delete</button>
        </div>
      `;
      li.querySelector('[data-action="toggle"]').onclick = async () => {
        await API.patch(`/api/weekly_plans/${plan.id}`, { done: !plan.done });
        await render();
      };
      li.querySelector('[data-action="delete"]').onclick = async () => {
        await API.delete(`/api/weekly_plans/${plan.id}`);
        await render();
      };
      weeklyPlanList.appendChild(li);
    }

    calendarBody.innerHTML = "";
    for (const row of pData.calendar) {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${esc(row.day)}</td><td>${esc(row.tasks_done || 0)}</td><td>${esc(row.docs_read || 0)}</td>`;
      calendarBody.appendChild(tr);
    }
    if (!calendarBody.children.length) {
      calendarBody.innerHTML = `<tr><td colspan="3">No activity yet</td></tr>`;
    }
  }

  weeklyPlanForm.onsubmit = async (e) => {
    e.preventDefault();
    const weekLabel = weekLabelInput.value.trim();
    const planText = weekPlanInput.value.trim();
    if (!weekLabel || !planText) return;
    await API.post("/api/weekly_plans", { week_label: weekLabel, plan_text: planText });
    weekLabelInput.value = "";
    weekPlanInput.value = "";
    await render();
  };

  await render();
}

async function loadTasksPage() {
  const root = document.getElementById("tasksPage");
  if (!root) return;

  const form = document.getElementById("taskForm");
  const input = document.getElementById("taskInput");
  const priority = document.getElementById("taskPriority");
  const search = document.getElementById("taskSearch");
  const list = document.getElementById("taskList");

  async function render() {
    const data = await API.get(`/api/tasks?search=${encodeURIComponent(search.value.trim())}`);
    list.innerHTML = "";

    for (const t of data.tasks) {
      const li = document.createElement("li");
      li.className = `item ${t.done ? "done" : ""}`;
      li.innerHTML = `
        <div>
          <div class="title">${esc(t.text)}</div>
          <div class="meta">Phase: ${esc(t.phase_label)} | Priority: ${esc(t.priority)} | Created: ${esc(t.created_at)}${t.completed_at ? ` | Done: ${esc(t.completed_at)}` : ""}</div>
          ${!t.unlocked && !t.done ? `<div class="meta">Locked until ${esc(data.unlocked_phase_label)} tasks are complete.</div>` : ""}
        </div>
        <div class="row">
          <button class="ghost" data-action="toggle" ${!t.unlocked && !t.done ? "disabled" : ""}>${t.done ? "Reopen" : "Done"}</button>
          <button class="ghost" data-action="edit">Edit</button>
          <button class="danger" data-action="delete">Delete</button>
        </div>
      `;

      li.querySelector('[data-action="toggle"]').onclick = async () => {
        try {
          await API.patch(`/api/tasks/${t.id}`, { done: !t.done });
          await render();
        } catch (err) {
          alert(String(err.message).slice(0, 260));
        }
      };
      li.querySelector('[data-action="edit"]').onclick = async () => {
        const next = prompt("Update task", t.text);
        if (!next) return;
        await API.patch(`/api/tasks/${t.id}`, { text: next });
        await render();
      };
      li.querySelector('[data-action="delete"]').onclick = async () => {
        await API.delete(`/api/tasks/${t.id}`);
        await API.post("/api/milestones/sync_from_tasks");
        await render();
      };
      list.appendChild(li);
    }

    const unlockInfo = document.createElement("li");
    unlockInfo.className = "empty-state";
    unlockInfo.textContent = `Current unlocked phase: ${data.unlocked_phase_label}. Complete all tasks in this phase to unlock the next phase.`;
    list.prepend(unlockInfo);

    if (!list.children.length) list.innerHTML = `<li class="empty-state">No tasks match this search.</li>`;
  }

  form.onsubmit = async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    const data = await API.get("/api/tasks");
    await API.post("/api/tasks", { text, priority: priority.value, phase_rank: data.unlocked_phase_rank });
    input.value = "";
    await render();
  };
  search.oninput = render;
  await render();
}

async function loadDocsPage() {
  const root = document.getElementById("docsPage");
  if (!root) return;

  const q = qs("q");
  const status = document.getElementById("docsStatus");
  const search = document.getElementById("docSearch");
  const phaseFilter = document.getElementById("docPhase");
  const docList = document.getElementById("docList");
  const linkTable = document.getElementById("linkTableBody");
  const kbLookupForm = document.getElementById("kbLookupForm");
  const kbQuestion = document.getElementById("kbQuestion");
  const kbSummary = document.getElementById("kbSummary");
  const kbGuide = document.getElementById("kbGuide");

  search.value = q;
  if (q) kbQuestion.value = q;

  async function renderDocs() {
    const data = await API.get(`/api/documents?search=${encodeURIComponent(search.value.trim())}&phase=${encodeURIComponent(phaseFilter.value)}`);

    docList.innerHTML = "";
    for (const d of data.documents) {
      const firstAnchor = (d.anchors && d.anchors[0]) || { page: 1, paragraph: 1, note: "overview" };
      const li = document.createElement("li");
      li.className = "item";
      li.innerHTML = `
        <div>
          <div class="title">${esc(d.title)}</div>
          <div class="meta">${esc(d.phase)} | ${esc(d.kind)} | reads: ${esc(d.read_count || 0)}</div>
          <div class="muted">Primary lookup: page ${esc(firstAnchor.page)} para ${esc(firstAnchor.paragraph)} (${esc(firstAnchor.note)})</div>
        </div>
        <div class="row">
          <button class="ghost" data-action="read">Mark Read</button>
          <button class="ghost" data-action="ask">Ask from this</button>
        </div>
      `;
      li.querySelector('[data-action="read"]').onclick = async () => {
        await API.post("/api/documents/mark_read", { doc_id: d.id });
        status.textContent = `Marked read: ${d.title}`;
        await renderDocs();
      };
      li.querySelector('[data-action="ask"]').onclick = async () => {
        kbQuestion.value = `In ${d.title}, where is guidance for ${search.value || "setup"}?`;
        await runLookup();
      };
      docList.appendChild(li);
    }
    if (!docList.children.length) docList.innerHTML = `<li class="empty-state">No KB documents match your filter.</li>`;

    linkTable.innerHTML = "";
    data.links.slice(0, 80).forEach((link) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${esc(link.from_title)}</td><td>${esc(link.to_title)}</td><td>${esc(link.score)}</td><td>${esc(link.reason)}</td>`;
      linkTable.appendChild(tr);
    });
  }

  async function runLookup() {
    const question = kbQuestion.value.trim();
    if (!question) return;

    const res = await API.post("/api/kb/lookup", { question });
    kbSummary.style.display = "block";
    kbGuide.style.display = "block";

    kbSummary.innerHTML = `<h3 style="margin-top:0">AI Summary</h3><p>${esc(res.summary)}</p>`;

    const steps = res.guide_steps
      .map(
        (step) =>
          `<li>Step ${step.step}: ${esc(step.doc_title)} -> page ${esc(step.page)}, paragraph ${esc(step.paragraph)} (${esc(step.note)}; relevance ${esc(step.score)})</li>`
      )
      .join("");

    kbGuide.innerHTML = `
      <h3 style="margin-top:0">Where to Look</h3>
      <p>${esc(res.guide_text)}</p>
      <ol>${steps}</ol>
    `;
    status.textContent = "Lookup complete.";
  }

  kbLookupForm.onsubmit = async (e) => {
    e.preventDefault();
    await runLookup();
  };
  search.oninput = renderDocs;
  phaseFilter.onchange = renderDocs;

  if (q) await runLookup();
  await renderDocs();
}

async function loadAssistantPage() {
  const root = document.getElementById("assistantPage");
  if (!root) return;

  const chatMessages = document.getElementById("chatMessages");
  const form = document.getElementById("assistantForm");
  const input = document.getElementById("assistantInput");
  const modelSelect = document.getElementById("modelSelect");
  const topK = document.getElementById("topK");
  const temp = document.getElementById("temperature");
  const prompts = document.getElementById("quickPrompts");

  const prefill = qs("q");
  if (prefill) input.value = prefill;

  function pushMessage(sender, text, citations = []) {
    const wrap = document.createElement("div");
    wrap.className = `message ${sender === "user" ? "user" : "bot"}`;
    wrap.innerHTML = `<div>${esc(text)}</div>`;
    if (citations.length) {
      const c = document.createElement("div");
      c.className = "citations";
      c.innerHTML = `Citations: ${citations.map((x) => `${esc(x.title)} (${esc(x.phase)}, score ${esc(x.score)})`).join("; ")}`;
      wrap.appendChild(c);
    }
    chatMessages.appendChild(wrap);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  const modelData = await API.get("/api/models");
  modelSelect.innerHTML = `<option value="">No LLM (local retriever only)</option>`;
  modelData.models.forEach((model) => {
    const option = document.createElement("option");
    option.value = model;
    option.textContent = model;
    modelSelect.appendChild(option);
  });

  const history = await API.get("/api/chat");
  if (!history.messages.length) {
    pushMessage("assistant", "I am your onboarding AI assistant. Ask questions and I will respond with citations.");
  } else {
    history.messages.slice(-20).forEach((m) => pushMessage(m.sender, m.message));
  }

  prompts.innerHTML = "";
  QUICK_PROMPTS.forEach((prompt) => {
    const b = document.createElement("button");
    b.className = "chip";
    b.type = "button";
    b.textContent = prompt;
    b.onclick = () => {
      input.value = prompt;
      input.focus();
    };
    prompts.appendChild(b);
  });

  form.onsubmit = async (e) => {
    e.preventDefault();
    const question = input.value.trim();
    if (!question) return;

    pushMessage("user", question);
    input.value = "";

    const res = await API.post("/api/ask", {
      question,
      model: modelSelect.value,
      top_k: Number(topK.value || "4"),
      temperature: Number(temp.value || "0.2")
    });

    pushMessage("assistant", `${res.answer}\n\n(source: ${res.source}${res.model ? `, model: ${res.model}` : ""})`, res.citations);
  };

  if (prefill) form.dispatchEvent(new Event("submit", { cancelable: true }));
}

async function boot() {
  setActiveNav();
  setupGlobalSearch();
  await Promise.all([loadDashboard(), loadProgressPage(), loadTasksPage(), loadDocsPage(), loadAssistantPage()]);
}

boot().catch((err) => {
  console.error(err);
  const errorBox = document.getElementById("globalError");
  if (errorBox) errorBox.textContent = `Error: ${err.message}`;
});
