const state = {
  mode: "offline",
  activeView: "command",
  outreachStatus: "all",
  search: "",
  filters: {
    industry: "all",
    source: "all",
  },
};

const demoData = {
  prospects: [
    {
      name: "Acme Corp",
      industry: "B2B SaaS",
      size: "80 employees",
      location: "Boston, MA",
      website: "https://example.com/acme",
      decision_maker: "Jane Chen",
      decision_maker_title: "VP Sales",
      linkedin_url: "https://linkedin.com/company/acme-corp",
      description: "Pipeline analytics for mid-market revenue teams.",
      source: "fixture",
    },
    {
      name: "Meridian Ledger",
      industry: "Fintech",
      size: "140 employees",
      location: "Cambridge, MA",
      website: "https://example.com/meridian",
      decision_maker: "Priya Raman",
      decision_maker_title: "Head of Revenue Operations",
      linkedin_url: "https://linkedin.com/company/meridian-ledger",
      description: "Treasury workflows for distributed finance teams.",
      source: "fixture",
    },
    {
      name: "Northstar Revenue",
      industry: "Revenue Intelligence",
      size: "115 employees",
      location: "New York, NY",
      website: "https://example.com/northstar",
      decision_maker: "Marcus Lee",
      decision_maker_title: "Chief Revenue Officer",
      linkedin_url: "https://linkedin.com/company/northstar-revenue",
      description: "Forecast inspection and deal coaching for sales leaders.",
      source: "manual",
    },
  ],
  outreach: [
    {
      company_name: "Acme Corp",
      contact_name: "Jane Chen",
      channel: "email",
      date: "2026-06-27",
      subject: "Pipeline gaps before they hit forecast",
      status: "drafted",
      follow_up_due: "2026-06-30",
      message:
        "Jane, noticed Acme is scaling its mid-market motion. Teams at that stage often lose time reconciling rep notes, CRM fields, and forecast calls. Worth comparing notes for 15 minutes next week?",
    },
    {
      company_name: "Meridian Ledger",
      contact_name: "Priya Raman",
      channel: "linkedin",
      date: "2026-06-24",
      subject: "Quick thought on RevOps load",
      status: "followed_up",
      follow_up_due: "2026-06-28",
      message:
        "Priya, circling back with one useful benchmark: finance teams with distributed selling motions tend to spend 6 to 8 hours a week cleaning handoff context. Happy to share the checklist.",
    },
    {
      company_name: "Northstar Revenue",
      contact_name: "Marcus Lee",
      channel: "event",
      date: "2026-06-20",
      subject: "Coffee at SaaS GTM Summit",
      status: "meeting_booked",
      follow_up_due: null,
      message:
        "Marcus, saw Northstar will be at the SaaS GTM Summit. I am pulling together a few notes on forecast risk patterns and would enjoy comparing notes over coffee.",
    },
  ],
  meetings: [
    {
      client: "Northstar Revenue",
      date: "2026-06-22",
      raw_notes:
        "CRO wants better rep coaching visibility before Q3 pipeline review. Main concern is adoption friction.",
      extracted_insights:
        "Forecast inspection is urgent, but the buying committee will resist anything that creates another admin surface.",
      next_steps: "Send adoption-light pitch deck and schedule technical review.",
      action_items: ["Draft deck", "Send ROI notes", "Book technical review"],
    },
    {
      client: "Meridian Ledger",
      date: "2026-06-19",
      raw_notes:
        "RevOps is overwhelmed by CRM cleanup before board reporting. They want a lightweight process.",
      extracted_insights:
        "Strong pain around reporting accuracy. Buyer values practical workflow gains over broad automation claims.",
      next_steps: "Share follow-up checklist and ask for 20-minute discovery.",
      action_items: ["Share checklist", "Ask for discovery call"],
    },
  ],
  decks: [
    {
      company_name: "Northstar Revenue",
      created_date: "2026-06-27",
      slides: [
        {
          slide: 1,
          title: "Forecast confidence without more admin",
          content: "Help managers see deal risk earlier while reps keep selling.",
        },
        {
          slide: 2,
          title: "Their problem",
          content: "Pipeline reviews rely on stale notes and subjective rep updates.",
        },
        {
          slide: 3,
          title: "Cost of inaction",
          content: "Late-stage misses stay hidden until the quarter is already at risk.",
        },
        {
          slide: 4,
          title: "Our solution",
          content: "Turn deal activity, CRM state, and meeting context into review-ready signals.",
        },
      ],
      format: "markdown",
    },
  ],
};

const selectors = {
  navItems: document.querySelectorAll(".nav-item"),
  views: document.querySelectorAll(".view"),
  viewTitle: document.querySelector("#viewTitle"),
  globalSearch: document.querySelector("#globalSearch"),
  refreshData: document.querySelector("#refreshData"),
  taskInput: document.querySelector("#taskInput"),
  runTask: document.querySelector("#runTask"),
  clearTask: document.querySelector("#clearTask"),
  promptButtons: document.querySelectorAll("[data-prompt]"),
  traceIntent: document.querySelector("#traceIntent"),
  traceList: document.querySelector("#traceList"),
  resultStatus: document.querySelector("#resultStatus"),
  resultBody: document.querySelector("#resultBody"),
  prospectRows: document.querySelector("#prospectRows"),
  outreachCards: document.querySelector("#outreachCards"),
  meetingTimeline: document.querySelector("#meetingTimeline"),
  deckPreview: document.querySelector("#deckPreview"),
  industryFilter: document.querySelector("#industryFilter"),
  sourceFilter: document.querySelector("#sourceFilter"),
  metricProspects: document.querySelector("#metricProspects"),
  metricFollowups: document.querySelector("#metricFollowups"),
  metricMeetings: document.querySelector("#metricMeetings"),
  metricDecks: document.querySelector("#metricDecks"),
};

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function matchesSearch(item) {
  if (!state.search) return true;
  return JSON.stringify(item).toLowerCase().includes(state.search.toLowerCase());
}

function classifyTask(task) {
  const text = task.toLowerCase();
  if (text.includes("deck") || text.includes("slide") || text.includes("pitch")) return "deck";
  if (text.includes("meeting") || text.includes("brief") || text.includes("crm") || text.includes("notes")) return "meeting";
  if (text.includes("email") || text.includes("outreach") || text.includes("follow")) return "outreach";
  if (text.includes("event") || text.includes("conference") || text.includes("summit")) return "event";
  return "icp";
}

function getIntentLabel(intent) {
  const labels = {
    icp: "ICP Scout",
    event: "Event Scout",
    outreach: "Outreach",
    meeting: "Meeting Intel",
    deck: "Deck Builder",
  };
  return labels[intent] || "Orchestrator";
}

function setView(viewName) {
  state.activeView = viewName;
  selectors.navItems.forEach((item) => {
    item.classList.toggle("is-active", item.dataset.view === viewName);
  });
  selectors.views.forEach((view) => {
    const isVisible = view.id === `${viewName}View`;
    view.classList.toggle("is-visible", isVisible);
    if (isVisible) selectors.viewTitle.textContent = view.dataset.title;
  });
}

function populateFilters() {
  const industries = [...new Set(demoData.prospects.map((item) => item.industry))].sort();
  const sources = [...new Set(demoData.prospects.map((item) => item.source))].sort();
  selectors.industryFilter.innerHTML = [
    '<option value="all">All industries</option>',
    ...industries.map((item) => `<option value="${escapeHtml(item)}">${escapeHtml(item)}</option>`),
  ].join("");
  selectors.sourceFilter.innerHTML = [
    '<option value="all">All sources</option>',
    ...sources.map((item) => `<option value="${escapeHtml(item)}">${escapeHtml(item)}</option>`),
  ].join("");
}

function renderMetrics() {
  selectors.metricProspects.textContent = demoData.prospects.length;
  selectors.metricFollowups.textContent = demoData.outreach.filter((item) => item.follow_up_due).length;
  selectors.metricMeetings.textContent = demoData.meetings.length;
  selectors.metricDecks.textContent = demoData.decks.length;
}

function renderTrace(intent = "icp") {
  const steps = [
    ["Classify", `Intent detected as ${intent}`],
    ["Route", `${getIntentLabel(intent)} selected`],
    ["Assemble", "Output prepared for review"],
  ];
  selectors.traceIntent.textContent = intent;
  selectors.traceList.innerHTML = steps
    .map(
      ([title, detail], index) => `
        <li>
          <span class="trace-step">${index + 1}</span>
          <div>
            <div class="trace-title">${escapeHtml(title)}</div>
            <div class="trace-detail">${escapeHtml(detail)}</div>
          </div>
          <span class="result-meta">${index === 0 ? "0.4s" : index === 1 ? "1.8s" : "0.1s"}</span>
        </li>
      `,
    )
    .join("");
}

function renderProspects() {
  const rows = demoData.prospects
    .filter(matchesSearch)
    .filter((item) => state.filters.industry === "all" || item.industry === state.filters.industry)
    .filter((item) => state.filters.source === "all" || item.source === state.filters.source);

  selectors.prospectRows.innerHTML =
    rows
      .map(
        (item) => `
          <tr>
            <td>
              <div class="company-cell">
                <a href="${escapeHtml(item.website)}" target="_blank" rel="noreferrer">${escapeHtml(item.name)}</a>
                <span class="card-meta">${escapeHtml(item.description)}</span>
              </div>
            </td>
            <td>${escapeHtml(item.industry)}</td>
            <td>${escapeHtml(item.size)}</td>
            <td>${escapeHtml(item.location)}</td>
            <td>
              <strong>${escapeHtml(item.decision_maker)}</strong>
              <div class="card-meta">${escapeHtml(item.decision_maker_title)}</div>
            </td>
            <td><span class="pill muted">${escapeHtml(item.source)}</span></td>
          </tr>
        `,
      )
      .join("") || `<tr><td colspan="6"><div class="empty-state">No companies match the current filters.</div></td></tr>`;
}

function renderOutreach() {
  const cards = demoData.outreach
    .filter(matchesSearch)
    .filter((item) => state.outreachStatus === "all" || item.status === state.outreachStatus);

  selectors.outreachCards.innerHTML =
    cards
      .map(
        (item) => `
          <article class="message-card">
            <div class="status-row">
              <span class="pill">${escapeHtml(item.status.replaceAll("_", " "))}</span>
              <span class="card-meta">${escapeHtml(item.channel)}</span>
            </div>
            <div>
              <h3>${escapeHtml(item.company_name)}</h3>
              <div class="card-meta">${escapeHtml(item.contact_name)} · ${escapeHtml(item.date)}</div>
            </div>
            <div>
              <strong>${escapeHtml(item.subject)}</strong>
              <p class="message-body">${escapeHtml(item.message)}</p>
            </div>
            <div class="card-meta">Follow-up: ${escapeHtml(item.follow_up_due || "none")}</div>
          </article>
        `,
      )
      .join("") || `<div class="empty-state">No outreach records match this view.</div>`;
}

function renderMeetings() {
  const meetings = demoData.meetings.filter(matchesSearch);
  selectors.meetingTimeline.innerHTML =
    meetings
      .map(
        (item) => `
          <article class="timeline-item">
            <div class="timeline-date">${escapeHtml(item.date)}</div>
            <div>
              <h3>${escapeHtml(item.client)}</h3>
              <p>${escapeHtml(item.extracted_insights)}</p>
              <div class="card-meta">Next: ${escapeHtml(item.next_steps)}</div>
              <div class="action-list">
                ${item.action_items.map((action) => `<span>${escapeHtml(action)}</span>`).join("")}
              </div>
            </div>
          </article>
        `,
      )
      .join("") || `<div class="empty-state">No meeting notes match the current search.</div>`;

  const deck = demoData.decks[0];
  selectors.deckPreview.innerHTML = deck
    ? `
      <div class="card-meta">${escapeHtml(deck.company_name)} · ${escapeHtml(deck.created_date)}</div>
      ${deck.slides
        .map(
          (slide) => `
            <article class="deck-slide">
              <div class="slide-number">Slide ${escapeHtml(slide.slide)}</div>
              <h3>${escapeHtml(slide.title)}</h3>
              <p>${escapeHtml(slide.content)}</p>
            </article>
          `,
        )
        .join("")}
    `
    : `<div class="empty-state">No deck has been generated yet.</div>`;
}

function renderResult(intent, task) {
  const handlers = {
    icp: () =>
      demoData.prospects
        .slice(0, 3)
        .map(
          (item) => `
            <article class="result-card">
              <h3>${escapeHtml(item.name)}</h3>
              <div class="result-meta">${escapeHtml(item.industry)} · ${escapeHtml(item.size)} · ${escapeHtml(item.location)}</div>
              <p>${escapeHtml(item.decision_maker)} is the likely ${escapeHtml(item.decision_maker_title)} buyer.</p>
            </article>
          `,
        )
        .join(""),
    event: () => `
      <article class="result-card">
        <h3>Boston SaaS GTM Summit</h3>
        <p>Good fit for VP Sales and RevOps personas. Recommended action: prepare event-based outreach for target accounts.</p>
      </article>
    `,
    outreach: () => {
      const item = demoData.outreach[0];
      return `
        <article class="result-card">
          <h3>${escapeHtml(item.subject)}</h3>
          <p>${escapeHtml(item.message)}</p>
          <div class="result-meta">Saved as draft for ${escapeHtml(item.contact_name)}</div>
        </article>
      `;
    },
    meeting: () => {
      const item = demoData.meetings[0];
      return `
        <article class="result-card">
          <h3>${escapeHtml(item.client)} brief</h3>
          <p>${escapeHtml(item.extracted_insights)}</p>
          <div class="result-meta">Next step: ${escapeHtml(item.next_steps)}</div>
        </article>
      `;
    },
    deck: () => `
      <article class="result-card">
        <h3>Draft deck created</h3>
        <p>Built a 7-slide pitch narrative focused on forecast confidence, adoption friction, and one clear technical review ask.</p>
        <div class="result-meta">Preview available in Meetings.</div>
      </article>
    `,
  };

  selectors.resultStatus.textContent = "Complete";
  selectors.resultBody.innerHTML = `
    <div class="result-meta">Task: ${escapeHtml(task)}</div>
    ${handlers[intent] ? handlers[intent]() : handlers.icp()}
  `;
}

async function runApiTask(task) {
  const response = await fetch("/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task }),
  });
  if (!response.ok) throw new Error(`API returned ${response.status}`);
  return response.json();
}

async function runTask() {
  const task = selectors.taskInput.value.trim();
  if (!task) return;
  const intent = classifyTask(task);

  selectors.resultStatus.textContent = "Running";
  selectors.resultBody.innerHTML = `<div class="empty-state">Routing task through ${escapeHtml(getIntentLabel(intent))}...</div>`;
  renderTrace(intent);

  if (state.mode === "api") {
    try {
      const payload = await runApiTask(task);
      selectors.resultStatus.textContent = "Complete";
      selectors.resultBody.innerHTML = `
        <article class="result-card">
          <h3>${escapeHtml(payload.routed_to || intent)}</h3>
          <p>${escapeHtml(payload.final_output || payload.text || "API returned no final output.")}</p>
        </article>
      `;
      return;
    } catch (error) {
      selectors.resultStatus.textContent = "API unavailable";
      selectors.resultBody.innerHTML = `
        <article class="result-card">
          <h3>Falling back to offline preview</h3>
          <p>${escapeHtml(error.message)}</p>
        </article>
      `;
    }
  }

  window.setTimeout(() => renderResult(intent, task), 420);
}

function renderAll() {
  renderMetrics();
  renderTrace();
  renderProspects();
  renderOutreach();
  renderMeetings();
}

function bindEvents() {
  selectors.navItems.forEach((item) => {
    item.addEventListener("click", () => setView(item.dataset.view));
  });

  selectors.globalSearch.addEventListener("input", (event) => {
    state.search = event.target.value;
    renderProspects();
    renderOutreach();
    renderMeetings();
  });

  selectors.industryFilter.addEventListener("change", (event) => {
    state.filters.industry = event.target.value;
    renderProspects();
  });

  selectors.sourceFilter.addEventListener("change", (event) => {
    state.filters.source = event.target.value;
    renderProspects();
  });

  document.querySelectorAll("[data-mode]").forEach((button) => {
    button.addEventListener("click", () => {
      state.mode = button.dataset.mode;
      document.querySelectorAll("[data-mode]").forEach((item) => item.classList.remove("is-selected"));
      button.classList.add("is-selected");
    });
  });

  document.querySelectorAll("[data-status]").forEach((button) => {
    button.addEventListener("click", () => {
      state.outreachStatus = button.dataset.status;
      document.querySelectorAll("[data-status]").forEach((item) => item.classList.remove("is-selected"));
      button.classList.add("is-selected");
      renderOutreach();
    });
  });

  selectors.runTask.addEventListener("click", runTask);
  selectors.clearTask.addEventListener("click", () => {
    selectors.taskInput.value = "";
    selectors.taskInput.focus();
  });

  selectors.promptButtons.forEach((button) => {
    button.addEventListener("click", () => {
      selectors.taskInput.value = button.dataset.prompt;
      runTask();
    });
  });

  selectors.refreshData.addEventListener("click", renderAll);
}

function init() {
  populateFilters();
  bindEvents();
  renderAll();
  renderResult("icp", selectors.taskInput.value.trim());
}

init();
