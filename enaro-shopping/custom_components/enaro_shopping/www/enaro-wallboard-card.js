class EnaroWallboardCard extends HTMLElement {
  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error("Enaro wallboard card requires a summary sensor entity");
    }
    this.config = config;
    this.attachShadow({ mode: "open" });
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return this.config && this.config.compact ? 2 : 8;
  }

  _render() {
    if (!this.shadowRoot || !this._hass || !this.config) return;
    const state = this._hass.states[this.config.entity];
    if (!state) {
      this.shadowRoot.innerHTML = this._styles() + this._message("Enaro wird geladen ...");
      return;
    }
    const data = state.attributes || {};
    if (this.config.compact) {
      this._renderCompact(data);
      return;
    }
    this._renderFull(data);
  }

  _renderCompact(data) {
    const total = (data.tasks || []).length;
    const overdue = Number(data.overdue_count || 0);
    const rotation = (data.tasks || []).find(
      (task) => task.assignment_mode === "rotating"
    );
    this.shadowRoot.innerHTML = `${this._styles()}
      <ha-card class="compact" tabindex="0">
        <div class="compact-title"><ha-icon icon="mdi:clipboard-check-outline"></ha-icon> Enaro</div>
        <div class="compact-metrics">
          <span><strong>${total}</strong> offen</span>
          <span class="${overdue ? "danger" : ""}"><strong>${overdue}</strong> ueberfaellig</span>
        </div>
        <div class="compact-rotation">${rotation
          ? `Rotation: ${this._escape(rotation.rotation_current_member_name || "nicht zugewiesen")}`
          : "Keine aktive Rotation"}</div>
      </ha-card>`;
    const card = this.shadowRoot.querySelector("ha-card");
    card.addEventListener("click", () => this._navigate());
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") this._navigate();
    });
  }

  _renderFull(data) {
    const members = data.members || [];
    const tasks = data.tasks || [];
    const online = data.online !== false;
    const memberSections = members
      .map((member) => this._memberSection(member, tasks, online))
      .join("");
    const projects = (data.projects || [])
      .map(
        (item) => `<li><strong>${this._escape(item.title)}</strong>${
          item.kind === "step" ? ` <small>${this._escape(item.project_title)}</small>` : ""
        }</li>`
      )
      .join("");
    const events = (data.events || [])
      .map(
        (item) => `<li><span>${this._time(item.starts_at)}</span><strong>${this._escape(
          item.title
        )}</strong>${item.is_meal ? '<em class="meal">Mahlzeit</em>' : ""}</li>`
      )
      .join("");
    const lastSync = data.last_successful_at
      ? this._dateTime(data.last_successful_at)
      : "noch nicht synchronisiert";

    this.shadowRoot.innerHTML = `${this._styles()}
      <ha-card class="wallboard">
        <header>
          <div>
            <p class="eyebrow">${this._escape(data.household_name || "Enaro")}</p>
            <h1>${this._day(data.day)}</h1>
          </div>
          <div class="sync ${online ? "online" : "offline"}">
            <ha-icon icon="${online ? "mdi:cloud-check-outline" : "mdi:cloud-off-outline"}"></ha-icon>
            <span>${online ? "Aktuell" : `Offline-Stand: ${lastSync}`}</span>
          </div>
        </header>
        <section class="metrics">
          ${this._metric(data.open_today_count, "Heute", "today")}
          ${this._metric(data.overdue_count, "Ueberfaellig", "overdue")}
          ${this._metric(data.important_count, "Wichtig", "important")}
          ${this._metric(data.rotation_count, "Rotationen", "rotation")}
        </section>
        <div class="layout">
          <main>
            ${memberSections || this._empty("Noch keine Personen fuer das Wanddisplay freigegeben.")}
          </main>
          <aside>
            ${this._sideSection("Termine & Mahlzeiten", events, "Heute keine Termine.")}
            ${this._sideSection("Projekte", projects, "Keine faelligen Projekte.")}
            <section class="side-card shopping">
              <h2>Einkauf</h2>
              <div class="shopping-count">${Number(data.shopping?.open_count || 0)}</div>
              <p>offene Artikel${Number(data.shopping?.important_count || 0)
                ? `, davon ${Number(data.shopping.important_count)} wichtig`
                : ""}</p>
            </section>
          </aside>
        </div>
      </ha-card>`;
    this._bindActions(online);
  }

  _memberSection(member, tasks, online) {
    const memberTasks = tasks.filter((task) =>
      (task.member_ids || []).includes(member.member_id)
    );
    if (!memberTasks.length) return "";
    return `<section class="person">
      <div class="person-head">
        <h2>${this._escape(member.display_name)}</h2>
        ${member.is_virtual ? '<span class="badge virtual">Fiktiv</span>' : ""}
        <span class="count">${memberTasks.length}</span>
      </div>
      <div class="task-list">${memberTasks
        .map((task) => this._task(task, member.member_id, online))
        .join("")}</div>
    </section>`;
  }

  _task(task, memberId, online) {
    const dueLabel = {
      overdue: "Ueberfaellig",
      today: "Heute",
      important: "Wichtig",
      rotation: "Rotation",
    }[task.due_state] || "Offen";
    const rotation = task.assignment_mode === "rotating"
      ? `<p class="rotation-line">${this._escape(task.rotation_current_member_name || "-")} <span>-&gt;</span> ${this._escape(task.rotation_next_member_name || "-")}</p>`
      : "";
    return `<article class="task ${this._escape(task.due_state)}">
      <div class="task-copy">
        <div class="task-title"><span>${this._escape(task.icon || "")}</span><strong>${this._escape(task.title)}</strong></div>
        <div class="task-meta"><span class="badge">${dueLabel}</span>${
          task.important ? '<span class="badge important">Wichtig</span>' : ""
        }${task.points ? `<span>${Number(task.points)} Punkte</span>` : ""}</div>
        ${rotation}
      </div>
      <div class="actions">
        <button data-action="complete" data-task="${this._escape(task.id)}" data-member="${this._escape(memberId)}" ${online ? "" : "disabled"} title="Erledigen"><ha-icon icon="mdi:check"></ha-icon></button>
        <button data-action="tomorrow" data-task="${this._escape(task.id)}" data-member="${this._escape(memberId)}" ${online ? "" : "disabled"} title="Bis morgen"><ha-icon icon="mdi:weather-sunset-up"></ha-icon></button>
        <button data-action="week" data-task="${this._escape(task.id)}" data-member="${this._escape(memberId)}" ${online ? "" : "disabled"} title="Eine Woche"><ha-icon icon="mdi:calendar-arrow-right"></ha-icon></button>
      </div>
    </article>`;
  }

  _bindActions(online) {
    if (!online) return;
    this.shadowRoot.querySelectorAll("button[data-action]").forEach((button) => {
      button.addEventListener("click", async () => {
        const action = button.dataset.action;
        const taskId = button.dataset.task;
        const memberId = button.dataset.member;
        if (action === "complete") {
          await this._complete(taskId, memberId);
        } else {
          await this._snooze(taskId, memberId, action === "week" ? "week" : "tomorrow");
        }
      });
    });
  }

  async _complete(taskId, preferredMemberId) {
    const state = this._hass.states[this.config.entity];
    const task = (state?.attributes?.tasks || []).find((item) => item.id === taskId);
    if (!task) return;
    const members = state.attributes.members || [];
    let memberId = preferredMemberId;
    const eligible = task.completion_member_ids || [];
    if (eligible.length > 1) {
      const choices = eligible.map((id, index) => {
        const member = members.find((item) => item.member_id === id);
        return `${index + 1}: ${member?.display_name || id}`;
      });
      const selected = window.prompt(`Wer hat die Aufgabe erledigt?\n${choices.join("\n")}`, "1");
      if (selected === null) return;
      const index = Number(selected) - 1;
      if (!Number.isInteger(index) || !eligible[index]) {
        window.alert("Bitte eine gueltige Nummer waehlen.");
        return;
      }
      memberId = eligible[index];
    }
    const member = members.find((item) => item.member_id === memberId);
    if (!window.confirm(`"${task.title}" fuer ${member?.display_name || "die Person"} als erledigt markieren?`)) return;
    const entityId = this._todoEntity(state.attributes.household_id, memberId);
    if (!entityId) {
      window.alert("Die passende Enaro-Aufgabenentitaet wurde nicht gefunden.");
      return;
    }
    await this._hass.callService("todo", "update_item", {
      entity_id: entityId,
      item: taskId,
      status: "completed",
    });
  }

  async _snooze(taskId, memberId, preset) {
    const state = this._hass.states[this.config.entity];
    const task = (state?.attributes?.tasks || []).find((item) => item.id === taskId);
    if (!task) return;
    const label = preset === "week" ? "eine Woche" : "bis morgen";
    if (!window.confirm(`"${task.title}" ${label} ausblenden?`)) return;
    const entityId = this._todoEntity(state.attributes.household_id, memberId);
    if (!entityId) {
      window.alert("Die passende Enaro-Aufgabenentitaet wurde nicht gefunden.");
      return;
    }
    await this._hass.callService("enaro_shopping", "snooze_task", {
      entity_id: entityId,
      uid: taskId,
      preset,
    });
  }

  _todoEntity(householdId, memberId) {
    return Object.entries(this._hass.states).find(([, state]) =>
      state.entity_id.startsWith("todo.") &&
      state.attributes.enaro_household_id === householdId &&
      state.attributes.enaro_member_id === memberId
    )?.[0];
  }

  _navigate() {
    const path = this.config.navigation_path || "/flur-display/enaro";
    history.pushState(null, "", path);
    window.dispatchEvent(new Event("location-changed"));
  }

  _metric(value, label, className) {
    return `<div class="metric ${className}"><strong>${Number(value || 0)}</strong><span>${label}</span></div>`;
  }

  _sideSection(title, content, empty) {
    return `<section class="side-card"><h2>${title}</h2>${content ? `<ul>${content}</ul>` : `<p>${empty}</p>`}</section>`;
  }

  _empty(message) {
    return `<section class="empty"><ha-icon icon="mdi:check-circle-outline"></ha-icon><p>${message}</p></section>`;
  }

  _message(message) {
    return `<ha-card class="message">${message}</ha-card>`;
  }

  _time(value) {
    if (!value) return "";
    return new Intl.DateTimeFormat("de-DE", { hour: "2-digit", minute: "2-digit" }).format(new Date(value));
  }

  _dateTime(value) {
    return new Intl.DateTimeFormat("de-DE", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
  }

  _day(value) {
    const date = value ? new Date(`${value}T12:00:00`) : new Date();
    return new Intl.DateTimeFormat("de-DE", { weekday: "long", day: "2-digit", month: "long" }).format(date);
  }

  _escape(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  _styles() {
    return `<style>
      :host { --enaro: #087f72; --today: #d4a017; --danger: #cf3f3f; display: block; }
      ha-card { border-radius: 8px; overflow: hidden; }
      .wallboard { padding: 22px; background: var(--ha-card-background, var(--card-background-color)); }
      header { display:flex; align-items:center; justify-content:space-between; gap:18px; margin-bottom:18px; }
      h1,h2,p { margin:0; } h1 { font-size: clamp(26px, 3vw, 42px); letter-spacing:0; }
      .eyebrow { color:var(--secondary-text-color); font-weight:700; margin-bottom:3px; }
      .sync { display:flex; align-items:center; gap:8px; min-height:48px; padding:0 14px; border-radius:8px; background:color-mix(in srgb, var(--enaro) 12%, transparent); }
      .sync.offline { color:var(--warning-color, #b26a00); }
      .metrics { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin-bottom:18px; }
      .metric { min-height:84px; border:1px solid var(--divider-color); border-left:5px solid var(--enaro); border-radius:8px; padding:12px 16px; display:flex; flex-direction:column; justify-content:center; }
      .metric strong { font-size:28px; }.metric span { color:var(--secondary-text-color); font-weight:600; }
      .metric.overdue { border-left-color:var(--danger); }.metric.today { border-left-color:var(--today); }
      .layout { display:grid; grid-template-columns:minmax(0,2fr) minmax(290px,1fr); gap:18px; align-items:start; }
      main,aside { display:grid; gap:14px; }.person,.side-card,.empty { border:1px solid var(--divider-color); border-radius:8px; padding:14px; }
      .person-head { display:flex; align-items:center; gap:10px; margin-bottom:10px; }.person-head h2 { font-size:20px; }.count { margin-left:auto; background:var(--secondary-background-color); border-radius:999px; padding:4px 9px; }
      .task-list { display:grid; gap:9px; }.task { display:flex; align-items:center; gap:12px; min-height:72px; border-left:4px solid var(--enaro); background:var(--secondary-background-color); border-radius:6px; padding:10px 10px 10px 14px; }
      .task.overdue { border-left-color:var(--danger); }.task.today { border-left-color:var(--today); }.task-copy { min-width:0; flex:1; }.task-title { display:flex; align-items:center; gap:8px; font-size:16px; }.task-title strong { overflow-wrap:anywhere; }
      .task-meta { display:flex; flex-wrap:wrap; align-items:center; gap:7px; color:var(--secondary-text-color); margin-top:5px; font-size:13px; }.badge { border-radius:999px; padding:3px 8px; background:color-mix(in srgb, var(--enaro) 13%, transparent); font-style:normal; }.badge.important { background:color-mix(in srgb, var(--danger) 15%, transparent); }.badge.virtual { background:var(--secondary-background-color); }
      .rotation-line { margin-top:6px; color:var(--secondary-text-color); }.rotation-line span { color:var(--enaro); font-weight:800; }
      .actions { display:flex; gap:7px; }.actions button { width:48px; height:48px; border:1px solid var(--divider-color); border-radius:8px; color:var(--primary-text-color); background:var(--card-background-color); cursor:pointer; }.actions button:first-child { color:var(--enaro); }.actions button:disabled { opacity:.45; cursor:not-allowed; }
      .side-card h2 { font-size:18px; margin-bottom:10px; }.side-card ul { list-style:none; padding:0; margin:0; display:grid; gap:10px; }.side-card li { display:grid; grid-template-columns:auto 1fr auto; gap:9px; align-items:center; }.side-card small { color:var(--secondary-text-color); }.meal { color:var(--enaro); font-size:12px; }
      .shopping-count { font-size:36px; font-weight:800; color:var(--enaro); }.side-card p,.empty p { color:var(--secondary-text-color); }.empty { min-height:130px; display:grid; place-items:center; text-align:center; }.empty ha-icon { color:var(--enaro); --mdc-icon-size:36px; }
      .compact { padding:14px 16px; cursor:pointer; min-height:120px; }.compact-title { display:flex; gap:8px; align-items:center; font-weight:800; font-size:18px; }.compact-metrics { display:flex; gap:20px; margin:12px 0 7px; }.compact-metrics span { display:flex; gap:5px; }.compact-metrics .danger { color:var(--danger); }.compact-rotation { color:var(--secondary-text-color); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }.message { padding:20px; }
      @media (max-width: 900px) { .wallboard { padding:14px; }.metrics { grid-template-columns:repeat(2,1fr); }.layout { grid-template-columns:1fr; }.task { align-items:flex-start; }.actions { flex-direction:column; } }
      @media (max-width: 520px) { header { align-items:flex-start; flex-direction:column; }.sync { width:100%; box-sizing:border-box; }.task { flex-direction:column; }.actions { width:100%; flex-direction:row; }.actions button { flex:1; }.metrics { gap:8px; }.metric { min-height:70px; padding:9px; } }
    </style>`;
  }
}

customElements.define("enaro-wallboard-card", EnaroWallboardCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "enaro-wallboard-card",
  name: "Enaro Wanddisplay",
  description: "Gemeinsame Aufgaben, Rotationen, Termine und Einkauf aus Enaro.",
  preview: true,
});
