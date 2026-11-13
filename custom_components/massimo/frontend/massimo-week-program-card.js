// SPDX-License-Identifier: Apache-2.0
// Massimo for Home Assistant: the week programme card.
//
// The card edits a room's week programme with Massimo's own editor, the
// element <massimo-week-program>. That element and its texts are
// Massimo's, under its AGPL, and are not part of this file: the card
// fetches them from the Massimo server the room belongs to, through the
// integration's view (/api/massimo/ui/…), signed in to Home Assistant, and
// runs the element once per page. The card gives it a kit of controls in
// Home Assistant's look: native buttons and inputs in the theme's colours,
// which the element styles by their classes, and Home Assistant's switch.
//
// The programme is read with massimo.get_program and the changed days are
// written with massimo.set_program and the tag they were read with, so
// that a change made meanwhile, in Massimo or at a thermostat, is never
// overwritten: the card then keeps the edits and offers to load the
// current programme. It loads it again by itself when the room's
// program_tag changes and nothing is being edited.
//
// Plain JavaScript without a build, as Massimo's own web UI.
"use strict";

(() => {
  const CARD = "massimo-week-program-card";
  const EDITOR = "massimo-week-program";
  const LANGUAGES = ["en", "de", "fr", "it", "nl", "pl"];

  // The element, once per page; the texts, once per language.
  let elementLoad = null;
  const textLoads = {};

  async function loadElement(hass, entityId) {
    if (customElements.get(EDITOR)) return;
    if (!elementLoad) {
      elementLoad = (async () => {
        const resp = await hass.fetchWithAuth(`/api/massimo/ui/week-program.js?entity_id=${encodeURIComponent(entityId)}`);
        if (!resp.ok) throw new Error(`${resp.status} ${await resp.text()}`);
        const url = URL.createObjectURL(new Blob([await resp.text()], { type: "text/javascript" }));
        try {
          await new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src = url;
            script.onload = resolve;
            script.onerror = () => reject(new Error("the editor did not load"));
            document.head.appendChild(script);
          });
        } finally {
          URL.revokeObjectURL(url);
        }
        await customElements.whenDefined(EDITOR);
      })().catch((err) => {
        elementLoad = null;
        throw err;
      });
    }
    return elementLoad;
  }

  async function loadTexts(hass, entityId, lang) {
    const one = (code) => {
      if (!textLoads[code]) {
        textLoads[code] = hass
          .fetchWithAuth(`/api/massimo/ui/i18n/${code}.json?entity_id=${encodeURIComponent(entityId)}`)
          .then((resp) => (resp.ok ? resp.json() : {}))
          .catch(() => ({}));
      }
      return textLoads[code];
    };
    const en = await one("en");
    return lang === "en" ? en : { ...en, ...(await one(lang)) };
  }

  function language(hass) {
    const lang = String((hass.locale && hass.locale.language) || hass.language || "en").slice(0, 2).toLowerCase();
    return LANGUAGES.includes(lang) ? lang : "en";
  }

  // The kit the element builds with (week-program.js, its head comment).
  function kit(texts, hass, temps) {
    const t = (key, params) => {
      let s = texts[key];
      if (s === undefined) s = key;
      if (params) s = s.replace(/\{(\w+)\}/g, (m, k) => (params[k] === undefined ? m : String(params[k])));
      return s;
    };
    const locale = (hass.locale && hass.locale.language) || hass.language || "en";
    const fmtNum = (v, digits) =>
      new Intl.NumberFormat(locale, { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(v);
    const textEl = (tag, text, cls) => {
      const el = document.createElement(tag);
      el.textContent = text;
      if (cls) el.className = cls;
      return el;
    };
    const elem = (tag, cls, ...children) => {
      const el = document.createElement(tag);
      if (cls) el.className = cls;
      el.append(...children);
      return el;
    };
    const button = (label, opts, onClick) => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = label;
      const o = typeof opts === "string" ? { cls: opts } : opts || {};
      if (o.cls) b.className = o.cls;
      if (o.aria) b.setAttribute("aria-label", o.aria);
      if (o.title) b.title = o.title;
      if (onClick) b.addEventListener("click", onClick);
      return b;
    };
    const switchEl = (label, checked, onChange) => {
      const box = elem("label", "switch");
      let control;
      if (customElements.get("ha-switch")) {
        control = document.createElement("ha-switch");
        control.checked = !!checked;
        control.addEventListener("change", () => onChange(control.checked));
      } else {
        control = document.createElement("input");
        control.type = "checkbox";
        control.checked = !!checked;
        control.addEventListener("change", () => onChange(control.checked));
      }
      box.append(control, textEl("span", label, "switch-label"));
      return box;
    };
    const fieldRow = (label, control, { hint } = {}) => {
      const row = elem("div", "field");
      if (label) row.appendChild(textEl("label", label));
      row.appendChild(control);
      if (hint) row.appendChild(textEl("p", hint, "muted small"));
      return row;
    };
    const numberInput = (value, min, max, step, onChange) => {
      const i = document.createElement("input");
      i.type = "number";
      i.min = String(min);
      i.max = String(max);
      i.step = String(step);
      if (value !== undefined && value !== null) i.value = String(value);
      i.addEventListener("change", () => onChange(i.value === "" ? undefined : Number(i.value)));
      return i;
    };
    const clamp = (v) => {
      if (v === undefined || Number.isNaN(v)) return temps.min;
      return Math.min(temps.max, Math.max(temps.min, Math.round(v / temps.step) * temps.step));
    };
    return {
      t, elem, textEl, button, switchEl, fieldRow, numberInput, fmtNum,
      fmtTemp: (v) => `${fmtNum(v, 1)} °C`,
      clamp,
      temps,
    };
  }

  const STYLE = `
    :host { display: block; }
    ha-card { overflow: hidden; }
    .content { padding: 0 16px 8px; }
    .status { margin: 4px 0 12px; font-size: 0.9em; color: var(--secondary-text-color); }
    .status.error { color: var(--error-color); }
    .status.warning { color: var(--warning-color, var(--error-color)); }
    .actions {
      display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-end; align-items: center;
      padding: 8px 16px 16px; border-top: 1px solid var(--divider-color);
    }
    .actions .left { margin-right: auto; display: flex; gap: 8px; flex-wrap: wrap; }
    button {
      font: inherit; font-size: 0.875em; font-weight: 500; cursor: pointer;
      color: var(--primary-color); background: transparent;
      border: 1px solid var(--divider-color); border-radius: 18px;
      padding: 6px 14px; min-height: 36px;
    }
    button:hover:not(:disabled) { background: color-mix(in srgb, var(--primary-color) 10%, transparent); }
    button:disabled { color: var(--disabled-text-color); cursor: default; opacity: 0.6; }
    button.primary { color: var(--text-primary-color, #fff); background: var(--primary-color); border-color: var(--primary-color); }
    button.primary:disabled { background: var(--disabled-text-color); border-color: transparent; color: var(--card-background-color); }
    .day-bar { display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0; }
    .day-bar.week button { min-width: 44px; padding: 6px 8px; position: relative; color: var(--primary-text-color); }
    .day-bar button.selected, .day-bar button.chosen {
      background: color-mix(in srgb, var(--primary-color) 18%, transparent); border-color: var(--primary-color);
    }
    .day-bar button.editing { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: var(--primary-color); }
    .day-bar button.dirty::after {
      content: ""; position: absolute; top: 3px; right: 5px; width: 6px; height: 6px; border-radius: 50%;
      background: var(--warning-color, #ffa600);
    }
    .field { display: flex; align-items: center; gap: 8px; margin: 8px 0; }
    .switch { display: inline-flex; align-items: center; gap: 10px; cursor: pointer; }
    .muted { color: var(--secondary-text-color); }
    .small { font-size: 0.85em; }
    p { margin: 4px 0; }
    h4 { margin: 16px 0 4px; font-weight: 500; font-size: 0.95em; }
    .prog-bar {
      display: flex; height: 28px; margin: 12px 0; border-radius: 8px; overflow: hidden;
      border: 1px solid var(--divider-color);
    }
    .prog-seg {
      display: flex; align-items: center; justify-content: center; min-width: 0; overflow: hidden;
      font-size: 0.75em; color: #fff; white-space: nowrap;
      background: color-mix(
        in srgb,
        var(--state-climate-heat-color, #ff8100) calc(var(--warm, 0.5) * 100%),
        var(--state-climate-cool-color, #2b9af9)
      );
      border-right: 1px solid var(--card-background-color);
    }
    .prog-seg:last-child { border-right: 0; }
    .prog-points { display: flex; flex-direction: column; gap: 6px; }
    .prog-point { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
    .prog-end { min-width: 96px; font-variant-numeric: tabular-nums; }
    input[type="time"], input[type="number"] {
      font: inherit; color: var(--primary-text-color); background: var(--card-background-color);
      border: 1px solid var(--divider-color); border-radius: 6px; padding: 6px 8px; min-height: 22px;
    }
    input[type="time"] { min-width: 96px; color-scheme: light dark; }
    input[type="number"] { width: 4.5em; }
    input:focus { outline: 2px solid var(--primary-color); outline-offset: -1px; }
    button.step { min-width: 36px; padding: 4px 0; border-radius: 50%; font-size: 1.1em; line-height: 1; }
    .day-copy { margin-top: 8px; }
    @media (max-width: 450px) {
      .content { padding: 0 12px 8px; }
      .day-bar.week button { min-width: 38px; padding: 6px 4px; }
      .actions { padding: 8px 12px 12px; }
    }
  `;

  class MassimoWeekProgramCard extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._config = null;
      this._hass = null;
      this._started = false;
      this._busy = false;
      this._etag = null;
      this._model = null;
      this._kit = null;
      this._status = { text: "", kind: "" };
      this._reload = false;
    }

    static getConfigForm() {
      return {
        schema: [
          {
            name: "entity",
            required: true,
            selector: { entity: { filter: { integration: "massimo", domain: "climate" } } },
          },
        ],
      };
    }

    static getStubConfig(hass) {
      const entity = Object.keys(hass.states).find(
        (id) => id.startsWith("climate.") && hass.entities && hass.entities[id] && hass.entities[id].platform === "massimo",
      );
      return { entity: entity || "" };
    }

    setConfig(config) {
      if (!config || !config.entity) throw new Error("Choose a Massimo room (its climate entity).");
      const changed = this._config && this._config.entity !== config.entity;
      this._config = config;
      if (changed) {
        this._started = false;
        this._model = null;
        this._etag = null;
      }
      if (this._hass) this._start();
    }

    set hass(hass) {
      this._hass = hass;
      if (!this._config) return;
      if (!this._started) {
        this._start();
        return;
      }
      this._title();
      const state = hass.states[this._config.entity];
      const tag = state && state.attributes.program_tag;
      if (tag && this._etag && tag !== this._etag && !this._busy && !this._dirty()) this._load(false);
    }

    getCardSize() {
      return 9;
    }

    getGridOptions() {
      return { columns: 12, min_columns: 6, rows: "auto" };
    }

    _W() {
      return customElements.get(EDITOR);
    }

    _dirty() {
      const W = this._W();
      return !!(W && this._model && W.dirtyDays(this._model).length);
    }

    _t(key, params) {
      return this._kit ? this._kit.t(key, params) : key;
    }

    _title() {
      const card = this.shadowRoot.querySelector("ha-card");
      const state = this._hass && this._hass.states[this._config.entity];
      if (card) card.header = (state && state.attributes.friendly_name) || this._config.entity;
    }

    async _start() {
      this._started = true;
      this._render();
      try {
        const entity = this._config.entity;
        const [, texts] = await Promise.all([
          loadElement(this._hass, entity),
          loadTexts(this._hass, entity, language(this._hass)),
        ]);
        const state = this._hass.states[entity];
        const temps = {
          min: (state && state.attributes.min_temp) || 4.5,
          max: (state && state.attributes.max_temp) || 30.5,
          step: 0.5,
        };
        this._kit = kit(texts, this._hass, temps);
        await this._load(false);
      } catch (err) {
        this._started = false;
        this._setStatus(String((err && err.message) || err), "error");
      }
    }

    async _service(service, data, response) {
      const answer = await this._hass.callWS({
        type: "call_service",
        domain: "massimo",
        service,
        service_data: data || {},
        target: { entity_id: this._config.entity },
        return_response: !!response,
      });
      return answer && answer.response ? answer.response[this._config.entity] : undefined;
    }

    async _load(announce) {
      this._busy = true;
      try {
        const program = await this._service("get_program", {}, true);
        this._model = this._W().model({ ...program.program, source: program.source });
        this._etag = program.etag;
        this._source = program.source || "";
        this._reload = false;
        this._status = { text: announce ? this._t("prog.reloaded") : "", kind: "" };
      } catch (err) {
        this._status = { text: (err && err.message) || String(err), kind: "error" };
      } finally {
        this._busy = false;
      }
      this._render();
    }

    async _send() {
      const W = this._W();
      const p = this._model;
      const t = (k, v) => this._t(k, v);
      const days = W.dirtyDays(p);
      const program = {};
      for (const day of days) {
        W.sortPoints(p.days[day]);
        const err = W.validateDay(p.days[day], t);
        if (err) return this._setStatus(t("prog.dayError", { day: t("dayShort." + day), error: err }), "error");
        program[day] = W.copyPoints(p.days[day]);
      }
      if (!days.length) return this._setStatus(t("prog.nothing"), "");
      const label = t("prog.label", { days: days.map((d) => t("day." + d)).join(", ") });
      this._busy = true;
      this._setStatus(t("result.waiting", { label }), "");
      try {
        const answer = await this._service("set_program", { program, etag: this._etag }, true);
        for (const day of days) p.orig[day] = W.copyPoints(program[day]);
        if (answer && answer.etag) this._etag = answer.etag;
        this._status = { text: t("result.ok", { label }), kind: "" };
      } catch (err) {
        if (err && err.translation_key === "program_changed_meanwhile") {
          this._status = { text: t("prog.outdated"), kind: "error" };
          this._reload = true;
        } else if (err && err.translation_key === "discarded") {
          this._status = { text: t("result.discarded", { label }), kind: "error" };
        } else {
          this._status = { text: t("result.error", { label, error: (err && err.message) || String(err) }), kind: "error" };
        }
      } finally {
        this._busy = false;
      }
      this._render();
    }

    _setStatus(text, kind) {
      this._status = { text, kind };
      const el = this.shadowRoot.querySelector(".status");
      if (el) {
        el.textContent = text;
        el.className = "status" + (kind ? " " + kind : "");
      } else this._render();
    }

    _render() {
      const root = this.shadowRoot;
      root.replaceChildren();
      const style = document.createElement("style");
      style.textContent = STYLE;
      const card = document.createElement("ha-card");
      root.append(style, card);
      this._title();
      const content = document.createElement("div");
      content.className = "content";
      const status = document.createElement("p");
      status.className = "status" + (this._status.kind ? " " + this._status.kind : "");
      status.textContent = this._status.text;
      content.appendChild(status);
      card.appendChild(content);
      if (!this._model || !this._kit) return;

      const editor = document.createElement(EDITOR);
      editor.kit = this._kit;
      editor.model = this._model;
      editor.storedOn = this._source || "";
      content.appendChild(editor);

      const actions = document.createElement("div");
      actions.className = "actions";
      const left = document.createElement("span");
      left.className = "left";
      left.append(...(editor.resetControls() || []));
      actions.appendChild(left);
      if (this._reload) {
        const reload = this._kit.button(this._t("prog.reload"), "", () => this._load(true));
        actions.appendChild(reload);
      }
      const send = this._kit.button(this._t("action.send"), "primary", () => this._send());
      send.disabled = this._busy || !this._dirty();
      actions.appendChild(send);
      card.appendChild(actions);
      editor.addEventListener("change", () => {
        send.disabled = this._busy || !this._dirty();
      });
    }
  }

  if (!customElements.get(CARD)) customElements.define(CARD, MassimoWeekProgramCard);
  window.customCards = window.customCards || [];
  if (!window.customCards.some((c) => c.type === CARD)) {
    window.customCards.push({
      type: CARD,
      name: "Massimo week programme",
      description: "Edits a room's week programme with Massimo's own editor.",
      preview: false,
      documentationURL: "https://github.com/metaworx/massimo-homeassistant",
    });
  }
})();
