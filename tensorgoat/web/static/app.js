/* TensorGoat local web interface.
 *
 * No text for the player lives in this file: every label comes from the "ui"
 * section of the language catalogue (tensorgoat/locales/<lang>.yml) and is
 * looked up by its key with t(). Nothing is loaded from the internet.
 */
"use strict";

(() => {
  const TOKEN = window.TGOAT_TOKEN;
  const TABS = ["briefing", "files", "console", "hints", "flag", "defense"];
  const main = document.getElementById("main");

  const state = {
    overview: null,
    detail: null,
    tab: "briefing",
    busy: null, // name of the action in progress
    confirm: null, // name of the action waiting for a second click
    file: null, // {name, text} | {name, binary: true}
    flag: "",
    flagResult: null, // "correct" | "incorrect"
    request: { method: "GET", path: "/", body: "" },
    response: null, // {status, body} | {error}
    presets: null,
    defense: null, // {id, html} | {id, locked: true} | {id, missing: true}
  };
  let strings = {};

  // ------------------------------------------------------------------ texts
  function fmt(text, values = {}) {
    return String(text).replace(/\{\{|\}\}|\{(\w+)\}/g, (match, name) => {
      if (match === "{{") return "{";
      if (match === "}}") return "}";
      return name in values ? String(values[name]) : match;
    });
  }

  function t(key, values) {
    return fmt(key in strings ? strings[key] : key, values);
  }

  function esc(value) {
    return String(value).replace(
      /[&<>"']/g,
      (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char],
    );
  }

  function applyStaticTexts() {
    for (const node of document.querySelectorAll("[data-i18n]")) {
      node.textContent = t(node.dataset.i18n);
    }
    document.documentElement.lang = state.overview.lang;
  }

  // -------------------------------------------------------------------- api
  class ApiError extends Error {
    constructor(message, status, key) {
      super(message);
      this.status = status;
      this.key = key;
    }
  }

  async function api(method, path, body) {
    const headers = { "X-TGoat-Token": TOKEN };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    let response;
    try {
      response = await fetch("/api" + path, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch (error) {
      throw new ApiError(t("error_network"), 0, "network");
    }
    let data = null;
    try {
      data = await response.json();
    } catch (error) {
      data = null;
    }
    if (!response.ok) {
      const message = data && data.message ? data.message : "HTTP " + response.status;
      throw new ApiError(message, response.status, data && data.error);
    }
    return data;
  }

  function toast(message, kind = "info") {
    const node = document.createElement("div");
    node.className = "toast toast-" + kind;
    node.textContent = message;
    document.getElementById("toasts").append(node);
    setTimeout(() => node.classList.add("toast-out"), 4200);
    setTimeout(() => node.remove(), 4800);
  }

  // ---------------------------------------------------------------- routing
  function route() {
    const parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
    return { id: parts[0] || null, tab: TABS.includes(parts[1]) ? parts[1] : "briefing" };
  }

  function go(id, tab) {
    const target = id ? "#/" + id + (tab && tab !== "briefing" ? "/" + tab : "") : "#/";
    if (location.hash === target) onRoute();
    else location.hash = target;
  }

  async function onRoute() {
    const { id, tab } = route();
    state.confirm = null;
    if (!id) {
      state.detail = null;
      render();
      return;
    }
    const changed = !state.detail || state.detail.id !== id;
    state.tab = tab;
    if (changed) {
      state.file = null;
      state.flag = "";
      state.flagResult = null;
      state.response = null;
      state.presets = null;
      state.defense = null;
      state.request = { method: "GET", path: "/", body: "" };
      try {
        state.detail = await api("GET", "/scenarios/" + encodeURIComponent(id));
      } catch (error) {
        toast(error.message, "error");
        go(null);
        return;
      }
    }
    render();
    enterTab();
  }

  function enterTab() {
    if (state.tab === "console") loadPresets();
    if (state.tab === "defense") loadDefense(false);
  }

  // ---------------------------------------------------------------- loading
  async function loadOverview() {
    state.overview = await api("GET", "/overview");
    strings = state.overview.strings;
    applyStaticTexts();
    renderChrome();
  }

  async function refreshDetail() {
    if (!state.detail) return;
    state.detail = await api("GET", "/scenarios/" + state.detail.id);
  }

  async function loadPresets() {
    const detail = state.detail;
    if (!detail || !detail.service || !detail.service.running || state.presets) return;
    try {
      const answer = await api("POST", "/scenarios/" + detail.id + "/request", {
        method: "GET",
        path: "/",
      });
      const presets = [{ method: "GET", path: "/", body: null }];
      const endpoints = (answer.body && answer.body.endpoints) || {};
      for (const [name, example] of Object.entries(endpoints)) {
        const [method, path] = name.split(" ");
        if (method && path) presets.push({ method, path, body: example });
      }
      state.presets = presets;
      if (!state.response) state.response = answer;
      if (state.detail === detail && state.tab === "console") render();
    } catch (error) {
      state.presets = [{ method: "GET", path: "/", body: null }];
    }
  }

  async function loadDefense(reveal) {
    const detail = state.detail;
    if (!detail) return;
    if (state.defense && state.defense.id === detail.id && (state.defense.html || !reveal)) return;
    try {
      const query = reveal ? "?reveal=true" : "";
      const answer = await api("GET", "/scenarios/" + detail.id + "/walkthrough" + query);
      state.defense = { id: detail.id, html: answer.html };
    } catch (error) {
      if (error.status === 423) state.defense = { id: detail.id, locked: true };
      else state.defense = { id: detail.id, missing: true, message: error.message };
    }
    if (state.detail === detail && state.tab === "defense") render();
  }

  // ----------------------------------------------------------------- chrome
  function renderChrome() {
    const overview = state.overview;
    document.getElementById("version").textContent = "v" + overview.version;

    const progress = document.getElementById("progress");
    progress.hidden = false;
    const share = overview.total ? (100 * overview.solved) / overview.total : 0;
    document.getElementById("progress-fill").style.width = share + "%";
    document.getElementById("progress-text").textContent = t("progress", {
      solved: overview.solved,
      total: overview.total,
    });

    const switcher = document.getElementById("lang-switch");
    switcher.setAttribute("aria-label", t("lang_label"));
    switcher.innerHTML = overview.languages
      .map(
        (code) =>
          `<button type="button" class="lang-button" data-action="lang" data-lang="${esc(code)}"
             aria-pressed="${code === overview.lang}">${esc(code.toUpperCase())}</button>`,
      )
      .join("");

    const current = route().id;
    document.getElementById("nav-home").classList.toggle("is-active", !current);
    document.getElementById("scenario-list").innerHTML = overview.scenarios
      .map(
        (item) => `
        <li>
          <a class="scenario-link ${item.id === current ? "is-active" : ""}" href="#/${esc(item.id)}">
            <span class="scenario-number">${esc(item.number.slice(1))}</span>
            <span class="scenario-text">
              <span class="scenario-title">${esc(item.title)}</span>
              <span class="scenario-meta">${esc(item.difficulty_label)} · ${esc(
                t("minutes", { n: item.minutes }),
              )}</span>
            </span>
            <span class="dot dot-${esc(item.status)}" title="${esc(t("status_" + item.status))}"></span>
          </a>
        </li>`,
      )
      .join("");
  }

  // ------------------------------------------------------------------- home
  function renderHome() {
    const overview = state.overview;
    const next = overview.scenarios.find((item) => !item.solved);
    let cta = `<p class="all-solved">${esc(t("all_solved"))}</p>`;
    if (next) {
      const label =
        overview.solved === 0 && !next.created
          ? t("start_first", { title: next.title })
          : t("continue_with", { title: next.title });
      cta = `<a class="button button-primary button-large" href="#/${esc(next.id)}">${esc(label)}</a>`;
    }
    const steps = [1, 2, 3, 4]
      .map(
        (n) => `
        <li class="step">
          <span class="step-number">${n}</span>
          <div>
            <h3>${esc(t("how_" + n + "_title"))}</h3>
            <p>${esc(t("how_" + n + "_text"))}</p>
          </div>
        </li>`,
      )
      .join("");
    const cards = overview.scenarios
      .map(
        (item) => `
        <a class="card" href="#/${esc(item.id)}">
          <span class="card-top">
            <span class="card-number">${esc(item.number)}</span>
            <span class="status status-${esc(item.status)}">${esc(t("status_" + item.status))}</span>
          </span>
          <span class="card-title">${esc(item.title)}</span>
          <span class="card-summary">${esc(item.summary)}</span>
          <span class="chips">
            <span class="chip diff-${esc(item.difficulty)}">${esc(item.difficulty_label)}</span>
            <span class="chip">${esc(item.type_label)}</span>
            <span class="chip">${esc(t("minutes", { n: item.minutes }))}</span>
          </span>
        </a>`,
      )
      .join("");
    return `
      <section class="hero">
        <h1>${esc(t("welcome_title"))}</h1>
        <p class="lede">${esc(t("welcome_text"))}</p>
        ${cta}
      </section>
      <aside class="callout callout-warning">
        <strong>${esc(t("warning_title"))}</strong>
        <p>${esc(t("warning_text"))}</p>
      </aside>
      <section>
        <h2>${esc(t("how_title"))}</h2>
        <ol class="steps">${steps}</ol>
      </section>
      <aside class="callout">
        <strong>${esc(t("tools_title"))}</strong>
        <p>${esc(t("tools_text"))}</p>
      </aside>
      <section>
        <h2>${esc(t("scenarios"))}</h2>
        <div class="cards">${cards}</div>
      </section>`;
  }

  // --------------------------------------------------------------- scenario
  function copyButton(value) {
    return `<button type="button" class="button button-small" data-action="copy"
      data-value="${esc(value)}">${esc(t("copy"))}</button>`;
  }

  function renderControl(detail) {
    const busy = state.busy;
    if (!detail.created) {
      const hint = detail.service ? t("action_start_service_hint") : t("action_start_hint");
      return `
        <section class="control control-idle">
          <button type="button" class="button button-primary button-large" data-action="create"
            ${busy ? "disabled" : ""}>${esc(busy === "create" ? t("working_start") : t("action_start"))}</button>
          <p class="muted">${esc(hint)}</p>
        </section>`;
    }
    let serviceRow = "";
    if (detail.service) {
      const running = detail.service.running;
      serviceRow = `
        <div class="control-row">
          <span class="control-label">${esc(t("service"))}</span>
          <code class="control-value">${esc(detail.service.url || "")}</code>
          <span class="status status-${running ? "running" : "stopped"}">${esc(
            running ? t("service_running") : t("service_stopped"),
          )}</span>
          ${detail.service.url ? copyButton(detail.service.url) : ""}
        </div>
        ${running ? "" : `<p class="muted">${esc(t("service_stopped_tip"))}</p>`}`;
    }
    const destroyLabel =
      busy === "destroy"
        ? t("working_destroy")
        : state.confirm === "destroy"
          ? t("action_destroy_confirm")
          : t("action_destroy");
    return `
      <section class="control">
        <div class="control-row">
          <span class="control-label">${esc(t("workspace"))}</span>
          <code class="control-value">${esc(detail.workspace)}</code>
          ${copyButton(detail.workspace)}
        </div>
        ${serviceRow}
        <div class="control-actions">
          <button type="button" class="button" data-action="create" title="${esc(t("action_restart_title"))}"
            ${busy ? "disabled" : ""}>${esc(busy === "create" ? t("working_start") : t("action_restart"))}</button>
          <button type="button" class="button button-danger ${state.confirm === "destroy" ? "is-confirm" : ""}"
            data-action="destroy" ${busy ? "disabled" : ""}>${esc(destroyLabel)}</button>
        </div>
      </section>`;
  }

  function renderTabs(detail) {
    const labels = {
      briefing: t("tab_briefing"),
      files: t("tab_files") + (detail.files.length ? " (" + detail.files.length + ")" : ""),
      console: t("tab_console"),
      hints: t("tab_hints") + " (" + detail.hints.opened.length + "/" + detail.hints.total + ")",
      flag: t("tab_flag"),
      defense: t("tab_defense"),
    };
    return TABS.filter((name) => name !== "console" || detail.service)
      .map(
        (name) => `
        <a class="tab ${state.tab === name ? "is-active" : ""}" role="tab"
          aria-selected="${state.tab === name}" href="#/${esc(detail.id)}/${name}">${esc(labels[name])}</a>`,
      )
      .join("");
  }

  function list(title, items, code) {
    if (!items.length) return "";
    const rows = items.map((item) => `<li>${code ? `<code>${esc(item)}</code>` : esc(item)}</li>`);
    return `<section class="meta-block"><h3>${esc(title)}</h3><ul>${rows.join("")}</ul></section>`;
  }

  function panelBriefing(detail) {
    return `
      <div class="prose">${detail.briefing_html}</div>
      <div class="meta-grid">
        ${list(t("objectives"), detail.objectives)}
        ${list(t("categories"), detail.categories)}
        ${list(t("tools"), detail.tools)}
      </div>`;
  }

  function formatSize(bytes) {
    const lang = state.overview.lang;
    if (bytes < 1024) return bytes.toLocaleString(lang) + " B";
    const units = ["KB", "MB", "GB"];
    let value = bytes / 1024;
    let unit = 0;
    while (value >= 1024 && unit < units.length - 1) {
      value /= 1024;
      unit += 1;
    }
    return value.toLocaleString(lang, { maximumFractionDigits: 1 }) + " " + units[unit];
  }

  function panelFiles(detail) {
    if (!detail.created) return `<p class="empty">${esc(t("files_empty"))}</p>`;
    const rows = detail.files
      .map(
        (file) => `
        <li>
          <button type="button" class="file ${state.file && state.file.name === file.name ? "is-active" : ""}"
            data-action="file" data-name="${esc(file.name)}" data-viewable="${file.viewable}">
            <span class="file-name">${esc(file.name)}</span>
            <span class="file-size">${esc(formatSize(file.size))}</span>
          </button>
        </li>`,
      )
      .join("");
    let preview = `<p class="empty">${esc(t("files_select"))}</p>`;
    if (state.file && state.file.binary) preview = `<p class="empty">${esc(t("files_binary"))}</p>`;
    else if (state.file)
      preview = `<div class="preview-head"><code>${esc(state.file.name)}</code></div>
        <pre class="code">${esc(state.file.text)}</pre>`;
    return `
      <p class="muted">${esc(t("files_intro"))}</p>
      <div class="files">
        <ul class="file-list">${rows}</ul>
        <div class="preview">${preview}</div>
      </div>`;
  }

  function toPython(value, indent = "") {
    if (value === null) return "None";
    if (value === true) return "True";
    if (value === false) return "False";
    if (typeof value === "number") return String(value);
    if (typeof value === "string") return JSON.stringify(value);
    if (Array.isArray(value)) return "[" + value.map((item) => toPython(item, indent)).join(", ") + "]";
    const entries = Object.entries(value).map(
      ([key, item]) => JSON.stringify(key) + ": " + toPython(item, indent),
    );
    return "{" + entries.join(", ") + "}";
  }

  function pythonSnippet(detail) {
    const url = detail.service.url + state.request.path;
    if (state.request.method === "GET") return `import httpx\n\nprint(httpx.get(${JSON.stringify(url)}).json())`;
    let body;
    try {
      body = toPython(JSON.parse(state.request.body || "null"));
    } catch (error) {
      return "";
    }
    return `import httpx\n\nprint(httpx.post(${JSON.stringify(url)}, json=${body}).json())`;
  }

  function panelConsole(detail) {
    if (!detail.service.running) return `<p class="empty">${esc(t("console_not_running"))}</p>`;
    const request = state.request;
    const presets = (state.presets || [])
      .map(
        (preset, index) => `
        <button type="button" class="button button-small" data-action="preset" data-index="${index}">
          ${esc(preset.method + " " + preset.path)}</button>`,
      )
      .join("");
    let response = `<p class="empty">${esc(t("console_empty"))}</p>`;
    if (state.response && state.response.error) {
      response = `<p class="result result-bad">${esc(state.response.error)}</p>`;
    } else if (state.response) {
      const ok = state.response.status < 400;
      const text =
        typeof state.response.body === "string"
          ? state.response.body
          : JSON.stringify(state.response.body, null, 2);
      response = `
        <span class="status status-${ok ? "running" : "stopped"}">${esc(
          t("console_status", { status: state.response.status }),
        )}</span>
        <pre class="code">${esc(text)}</pre>`;
    }
    const snippet = pythonSnippet(detail);
    return `
      <p class="muted">${esc(t("console_intro"))}</p>
      ${presets ? `<div class="presets"><span class="control-label">${esc(t("console_examples"))}</span>${presets}</div>` : ""}
      <form class="console" data-form="console">
        <div class="console-line">
          <label class="field field-method">
            <span>${esc(t("console_method"))}</span>
            <select data-field="method">
              ${["GET", "POST"].map((m) => `<option ${m === request.method ? "selected" : ""}>${m}</option>`).join("")}
            </select>
          </label>
          <label class="field field-path">
            <span>${esc(t("console_path"))}</span>
            <input type="text" data-field="path" value="${esc(request.path)}" spellcheck="false" autocomplete="off">
          </label>
          <button type="submit" class="button button-primary" ${state.busy ? "disabled" : ""}>${esc(t("console_send"))}</button>
        </div>
        <label class="field" ${request.method === "GET" ? "hidden" : ""}>
          <span>${esc(t("console_body"))}</span>
          <textarea data-field="body" rows="6" spellcheck="false">${esc(request.body)}</textarea>
        </label>
      </form>
      <h3>${esc(t("console_response"))}</h3>
      <div class="response">${response}</div>
      ${
        snippet
          ? `<details class="snippet"><summary>${esc(t("console_python"))}</summary>
              <pre class="code">${esc(snippet)}</pre>${copyButton(snippet)}</details>`
          : ""
      }`;
  }

  function panelHints(detail) {
    const opened = detail.hints.opened;
    const cards = opened
      .map(
        (text, index) => `
        <li class="hint">
          <span class="hint-level">${esc(t("hints_level", { level: index + 1 }))}</span>
          <p>${esc(text)}</p>
        </li>`,
      )
      .join("");
    const next = opened.length + 1;
    const action =
      next <= detail.hints.total
        ? `<button type="button" class="button" data-action="hint" ${state.busy ? "disabled" : ""}>${esc(
            t("hints_show", { level: next, total: detail.hints.total }),
          )}</button>`
        : `<p class="muted">${esc(t("hints_done"))}</p>`;
    return `
      <p class="muted">${esc(t("hints_intro"))}</p>
      ${cards ? `<ol class="hints">${cards}</ol>` : `<p class="empty">${esc(t("hints_none"))}</p>`}
      ${action}`;
  }

  function panelFlag(detail) {
    let result = "";
    if (state.flagResult === "correct")
      result = `<p class="result result-good">${esc(t("flag_correct"))}</p>`;
    else if (state.flagResult === "incorrect")
      result = `<p class="result result-bad">${esc(t("flag_incorrect"))}</p>`;
    const solved = detail.solved
      ? `<div class="callout callout-success">
           <strong>${esc(t("flag_solved"))}</strong>
           <p><a class="button button-primary" href="#/${esc(detail.id)}/defense">${esc(t("flag_read_defense"))}</a></p>
         </div>`
      : "";
    return `
      ${solved}
      <form class="flag-form" data-form="flag">
        <label class="field">
          <span>${esc(t("flag_intro"))}</span>
          <input type="text" data-field="flag" value="${esc(state.flag)}" placeholder="${esc(t("flag_placeholder"))}"
            spellcheck="false" autocomplete="off" autocapitalize="off">
        </label>
        <button type="submit" class="button button-primary" ${state.busy ? "disabled" : ""}>${esc(t("flag_check"))}</button>
      </form>
      ${result}`;
  }

  function panelDefense(detail) {
    const defense = state.defense && state.defense.id === detail.id ? state.defense : null;
    if (!defense) return `<p class="loading">${esc(t("loading"))}</p>`;
    if (defense.missing) return `<p class="empty">${esc(defense.message)}</p>`;
    if (defense.locked) {
      const label = state.confirm === "reveal" ? t("defense_reveal_confirm") : t("defense_reveal");
      return `
        <div class="locked">
          <h3>${esc(t("defense_locked"))}</h3>
          <p class="muted">${esc(t("defense_locked_text"))}</p>
          <button type="button" class="button button-danger ${state.confirm === "reveal" ? "is-confirm" : ""}"
            data-action="reveal">${esc(label)}</button>
        </div>`;
    }
    return `<div class="prose">${defense.html}</div>`;
  }

  function renderScenario() {
    const detail = state.detail;
    const panels = {
      briefing: panelBriefing,
      files: panelFiles,
      console: panelConsole,
      hints: panelHints,
      flag: panelFlag,
      defense: panelDefense,
    };
    const tab = state.tab === "console" && !detail.service ? "briefing" : state.tab;
    const note = detail.fallback ? `<p class="fallback">${esc(t("fallback_note"))}</p>` : "";
    return `
      <article class="scenario">
        <header class="scenario-head">
          <div class="chips">
            <span class="chip chip-id">${esc(detail.id)}</span>
            <span class="chip diff-${esc(detail.difficulty)}">${esc(detail.difficulty_label)}</span>
            <span class="chip">${esc(detail.type_label)}</span>
            <span class="chip">${esc(t("minutes", { n: detail.minutes }))}</span>
            <span class="status status-${esc(detail.status)}">${esc(t("status_" + detail.status))}</span>
          </div>
          <h1>${esc(detail.title)}</h1>
          <p class="lede">${esc(detail.summary)}</p>
          ${note}
        </header>
        ${renderControl(detail)}
        <nav class="tabs" role="tablist">${renderTabs(detail)}</nav>
        <section class="panel" role="tabpanel">${panels[tab](detail)}</section>
      </article>`;
  }

  function render() {
    renderChrome();
    main.innerHTML = state.detail ? renderScenario() : renderHome();
    for (const link of main.querySelectorAll(".prose a[href^='http']")) {
      link.target = "_blank";
      link.rel = "noopener noreferrer";
    }
  }

  // ---------------------------------------------------------------- actions
  async function run(name, work) {
    if (state.busy) return;
    state.busy = name;
    state.confirm = null;
    render();
    try {
      await work();
    } catch (error) {
      toast(error.message, "error");
    } finally {
      state.busy = null;
      try {
        await loadOverview();
      } catch (error) {
        /* the next action reports it */
      }
      render();
    }
  }

  function needsSecondClick(name) {
    if (state.confirm === name) return false;
    state.confirm = name;
    render();
    return true;
  }

  const actions = {
    async lang(target) {
      await run("lang", async () => {
        await api("POST", "/lang", { lang: target.dataset.lang });
        await loadOverview();
        await refreshDetail();
        state.presets = null;
        state.defense = null;
        enterTab();
      });
    },
    async create() {
      const id = state.detail.id;
      await run("create", async () => {
        state.detail = await api("POST", "/scenarios/" + id + "/create", {});
        state.presets = null;
        state.response = null;
        state.file = null;
        toast(t("started_toast"), "good");
      });
      enterTab();
    },
    async destroy() {
      if (needsSecondClick("destroy")) return;
      const id = state.detail.id;
      await run("destroy", async () => {
        state.detail = await api("POST", "/scenarios/" + id + "/destroy", {});
        state.file = null;
        state.presets = null;
        state.response = null;
        toast(t("destroyed_toast"), "info");
      });
    },
    async hint() {
      const id = state.detail.id;
      await run("hint", async () => {
        state.detail = await api("POST", "/scenarios/" + id + "/hint", {});
      });
    },
    async file(target) {
      const name = target.dataset.name;
      if (target.dataset.viewable !== "true") {
        state.file = { name, binary: true };
        render();
        return;
      }
      try {
        const path = name.split("/").map(encodeURIComponent).join("/");
        state.file = await api("GET", "/scenarios/" + state.detail.id + "/files/" + path);
      } catch (error) {
        toast(error.message, "error");
      }
      render();
    },
    preset(target) {
      const preset = state.presets[Number(target.dataset.index)];
      state.request = {
        method: preset.method,
        path: preset.path,
        body: preset.body === null ? "" : JSON.stringify(preset.body),
      };
      render();
    },
    async reveal() {
      if (needsSecondClick("reveal")) return;
      state.confirm = null;
      await loadDefense(true);
      render();
    },
    async copy(target) {
      try {
        await navigator.clipboard.writeText(target.dataset.value);
        toast(t("copied"), "good");
      } catch (error) {
        toast(target.dataset.value, "info");
      }
    },
  };

  const forms = {
    async flag() {
      const id = state.detail.id;
      await run("flag", async () => {
        const answer = await api("POST", "/scenarios/" + id + "/submit", { flag: state.flag });
        state.detail = answer.scenario;
        state.flagResult = answer.correct ? "correct" : "incorrect";
        if (answer.correct) state.defense = null;
      });
    },
    async console() {
      const id = state.detail.id;
      const request = state.request;
      let body = null;
      if (request.method === "POST") {
        try {
          body = JSON.parse(request.body || "null");
        } catch (error) {
          state.response = { error: t("console_bad_json") };
          render();
          return;
        }
      }
      await run("console", async () => {
        try {
          state.response = await api("POST", "/scenarios/" + id + "/request", {
            method: request.method,
            path: request.path,
            body,
          });
        } catch (error) {
          state.response = { error: error.message };
          if (error.status === 409) await refreshDetail();
        }
      });
    },
  };

  document.addEventListener("click", (event) => {
    const target = event.target.closest("[data-action]");
    if (!target) {
      if (state.confirm) {
        state.confirm = null;
        render();
      }
      return;
    }
    const action = actions[target.dataset.action];
    if (action) action(target);
  });

  main.addEventListener("submit", (event) => {
    event.preventDefault();
    const form = forms[event.target.dataset.form];
    if (form) form();
  });

  main.addEventListener("input", (event) => {
    const field = event.target.dataset.field;
    if (field === "flag") state.flag = event.target.value;
    else if (field === "path" || field === "body") state.request[field] = event.target.value;
  });

  main.addEventListener("change", (event) => {
    if (event.target.dataset.field === "method") {
      state.request.method = event.target.value;
      render();
    }
  });

  window.addEventListener("hashchange", onRoute);
  window.addEventListener("focus", async () => {
    // Pick up what the command line changed in the meantime.
    if (state.busy || !state.overview) return;
    try {
      await loadOverview();
      await refreshDetail();
      render();
    } catch (error) {
      /* shown on the next action */
    }
  });

  loadOverview()
    .then(onRoute)
    .catch((error) => {
      main.textContent = error.message;
    });
})();
