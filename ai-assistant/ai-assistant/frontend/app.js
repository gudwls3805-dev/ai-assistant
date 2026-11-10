/* 내 데이터 AI 비서 — 바닐라 JS 프론트엔드 */
(() => {
  "use strict";

  const API = ((window.APP_CONFIG && window.APP_CONFIG.API_BASE_URL) || "http://localhost:8000").replace(/\/+$/, "");
  const $ = (id) => document.getElementById(id);
  const nf = new Intl.NumberFormat("ko-KR", { maximumFractionDigits: 0 });
  const fmt = (n) => (n == null ? "-" : nf.format(n));
  const UNIT = "원";

  const state = {
    conversationId: null,
    conversations: [],
    data: [],
    summary: null,
    editingId: null,
    sending: false,
  };

  // ---------------- 공통 ----------------
  async function api(path, options = {}) {
    const res = await fetch(API + path, {
      ...options,
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    });
    let body = null;
    try { body = await res.json(); } catch (_) { /* 본문 없음 */ }
    if (!res.ok) {
      let msg = `요청 실패 (${res.status})`;
      if (body && body.detail) {
        msg = Array.isArray(body.detail)
          ? body.detail.map((d) => `${(d.loc || []).slice(-1)[0]}: ${d.msg}`).join(", ")
          : body.detail;
      }
      throw new Error(msg);
    }
    return body;
  }

  let toastTimer;
  function toast(msg, isError = false) {
    const t = $("toast");
    t.textContent = msg;
    t.classList.toggle("error", isError);
    t.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => (t.hidden = true), isError ? 4500 : 2200);
  }

  function el(tag, attrs = {}, ...children) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === "class") node.className = v;
      else if (k === "text") node.textContent = v;
      else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v);
    }
    children.flat().forEach((c) => c != null && node.append(c));
    return node;
  }

  // ---------------- 서버 상태 / 콜드스타트 ----------------
  async function wakeServer() {
    const status = $("serverStatus");
    const notice = $("coldStartNotice");
    const slowTimer = setTimeout(() => {
      notice.hidden = false;
      status.textContent = "서버 깨우는 중…";
    }, 2500);

    for (let attempt = 0; attempt < 6; attempt++) {
      try {
        const ctrl = new AbortController();
        const to = setTimeout(() => ctrl.abort(), 20000);
        const res = await fetch(API + "/health", { signal: ctrl.signal });
        clearTimeout(to);
        if (res.ok) {
          clearTimeout(slowTimer);
          notice.hidden = true;
          status.dataset.state = "ok";
          status.textContent = "서버 연결됨";
          return true;
        }
      } catch (_) { /* 재시도 */ }
      await new Promise((r) => setTimeout(r, 3000));
    }
    clearTimeout(slowTimer);
    notice.hidden = true;
    status.dataset.state = "error";
    status.textContent = "서버 연결 실패";
    toast("서버에 연결할 수 없어요. 잠시 후 새로고침해 주세요.", true);
    return false;
  }

  // ---------------- 요약 ----------------
  async function loadSummary() {
    try {
      state.summary = await api("/api/data/summary");
    } catch (e) {
      $("summaryStrip").textContent = "요약을 불러오지 못했어요: " + e.message;
      return;
    }
    renderSummary();
  }

  function trendClass(pct) {
    if (pct == null) return "";
    return pct >= 3 ? "up" : pct <= -3 ? "down" : "";
  }

  function renderSummary() {
    const s = state.summary;
    const strip = $("summaryStrip");
    const cards = $("summaryCards");
    strip.replaceChildren();
    cards.replaceChildren();
    if (!s || !s.count) {
      strip.textContent = "아직 데이터가 없어요. ‘데이터 관리’ 탭에서 데이터를 추가해 보세요.";
      return;
    }
    const m = s.metrics;
    const pair = (k, v, cls) => el("span", {}, k + " ", el("b", { class: cls || "", text: v }));
    strip.append(
      pair("기간", s.period),
      pair("개수", `${s.count}개`),
      pair("일평균", `${fmt(m.average)}${UNIT}`),
      pair("최대", `${fmt(m.max)}${UNIT} (${m.max_date})`),
      pair("트렌드", s.trend, trendClass(s.trend_change_pct)),
    );

    const stat = (label, value, sub, cls) =>
      el("div", { class: "stat" },
        el("div", { class: "label", text: label }),
        el("div", { class: "value " + (cls || ""), text: value }),
        sub ? el("div", { class: "sub", text: sub }) : null);
    const lm = s.latest_month;
    const trendWord = s.trend.split(" ")[0];
    cards.append(
      stat("기간", `${s.count}개`, s.period),
      stat("합계", `${fmt(m.total)}${UNIT}`),
      stat("일평균", `${fmt(m.average)}${UNIT}`, `표준편차 ${fmt(m.std)}`),
      stat("최대", `${fmt(m.max)}${UNIT}`, m.max_date),
      stat("최소", `${fmt(m.min)}${UNIT}`, m.min_date),
      stat("최근 7일 평균", `${fmt(s.recent_7_days_average)}${UNIT}`),
      stat("트렌드", trendWord + (s.trend_change_pct != null ? ` ${s.trend_change_pct > 0 ? "+" : ""}${s.trend_change_pct}%` : ""),
        "최근 30일 vs 직전 30일", trendClass(s.trend_change_pct)),
      lm ? stat(`${lm.month} 일평균`, `${fmt(lm.average)}${UNIT}`,
        lm.vs_overall_daily_avg_pct != null ? `전체 대비 ${lm.vs_overall_daily_avg_pct > 0 ? "+" : ""}${lm.vs_overall_daily_avg_pct}%` : "") : null,
    );
  }

  // ---------------- 데이터 CRUD ----------------
  async function loadData() {
    try {
      state.data = await api("/api/data");
    } catch (e) {
      toast("데이터 목록을 불러오지 못했어요: " + e.message, true);
      return;
    }
    renderTable();
    drawChart();
  }

  async function refreshData(flashId) {
    await Promise.all([loadData(), loadSummary()]);
    if (flashId) {
      const row = document.querySelector(`tr[data-id="${CSS.escape(flashId)}"]`);
      if (row) { row.classList.add("flash"); row.scrollIntoView({ block: "nearest" }); }
    }
  }

  function renderTable() {
    const body = $("dataBody");
    body.replaceChildren();
    $("dataCount").textContent = `(${state.data.length}개)`;
    const rows = [...state.data].reverse(); // 최신순 표시
    if (!rows.length) {
      body.append(el("tr", {}, el("td", { colspan: "4", class: "muted", text: "데이터가 없습니다." })));
      return;
    }
    const frag = document.createDocumentFragment();
    for (const item of rows) {
      frag.append(
        el("tr", { "data-id": item.id, class: item.id === state.editingId ? "editing" : "" },
          el("td", { text: item.date }),
          el("td", { class: "num", text: fmt(item.value) }),
          el("td", { text: item.memo || "" }),
          el("td", { class: "actions" },
            el("button", { class: "btn small", text: "수정", onclick: () => startEdit(item) }),
            " ",
            el("button", { class: "btn small danger", text: "삭제", onclick: () => deleteItem(item) }),
          ),
        ),
      );
    }
    body.append(frag);
  }

  function startEdit(item) {
    state.editingId = item.id;
    $("fDate").value = item.date;
    $("fValue").value = item.value;
    $("fMemo").value = item.memo || "";
    $("formTitle").textContent = `데이터 수정 (${item.date})`;
    $("formSubmit").textContent = "수정 저장";
    $("formCancel").hidden = false;
    renderTable();
    $("dataForm").scrollIntoView({ behavior: "smooth", block: "center" });
    $("fValue").focus();
  }

  function resetForm() {
    state.editingId = null;
    $("dataForm").reset();
    $("fDate").value = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);
    $("formTitle").textContent = "새 데이터 추가";
    $("formSubmit").textContent = "추가";
    $("formCancel").hidden = true;
    renderTable();
  }

  async function submitData(e) {
    e.preventDefault();
    const payload = {
      date: $("fDate").value,
      value: Number($("fValue").value),
      memo: $("fMemo").value.trim(),
    };
    if (!payload.date || !Number.isFinite(payload.value) || payload.value < 0) {
      toast("날짜와 0 이상의 값을 입력해 주세요.", true);
      return;
    }
    const btn = $("formSubmit");
    btn.disabled = true;
    try {
      let saved;
      if (state.editingId) {
        saved = await api(`/api/data/${encodeURIComponent(state.editingId)}`, { method: "PUT", body: JSON.stringify(payload) });
        toast("수정했어요.");
      } else {
        saved = await api("/api/data", { method: "POST", body: JSON.stringify(payload) });
        toast("추가했어요.");
      }
      resetForm();
      await refreshData(saved.id);
    } catch (err) {
      toast("저장 실패: " + err.message, true);
    } finally {
      btn.disabled = false;
    }
  }

  async function deleteItem(item) {
    if (!confirm(`${item.date} (${fmt(item.value)}${UNIT}) 데이터를 삭제할까요?`)) return;
    try {
      await api(`/api/data/${encodeURIComponent(item.id)}`, { method: "DELETE" });
      if (state.editingId === item.id) resetForm();
      toast("삭제했어요.");
      await refreshData();
    } catch (err) {
      toast("삭제 실패: " + err.message, true);
    }
  }

  // ---------------- 내보내기 ----------------
  function download(filename, content, type) {
    const url = URL.createObjectURL(new Blob([content], { type }));
    const a = el("a", { href: url, download: filename });
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function exportCsv() {
    const esc = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
    const lines = ["date,value,memo", ...state.data.map((d) => [d.date, d.value, esc(d.memo)].join(","))];
    download(`data_${today()}.csv`, "﻿" + lines.join("\n"), "text/csv;charset=utf-8"); // BOM: 엑셀 한글 깨짐 방지
  }

  function exportJson() {
    const out = state.data.map(({ date, value, memo }) => ({ date, value, memo }));
    download(`data_${today()}.json`, JSON.stringify(out, null, 2), "application/json");
  }

  const today = () => new Date().toISOString().slice(0, 10);

  // ---------------- 그래프 (캔버스 직접 그리기) ----------------
  function drawChart() {
    const canvas = $("chart");
    if (!canvas || canvas.offsetParent === null) return; // 탭이 숨겨진 상태
    const css = getComputedStyle(document.documentElement);
    const color = (n) => css.getPropertyValue(n).trim();
    const dpr = window.devicePixelRatio || 1;
    const W = canvas.clientWidth, H = 240;
    canvas.width = W * dpr; canvas.height = H * dpr;
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    ctx.font = "12px Pretendard, sans-serif";

    const d = state.data;
    if (d.length < 2) {
      ctx.fillStyle = color("--muted");
      ctx.fillText("그래프를 그리려면 데이터가 2개 이상 필요해요.", 12, 24);
      return;
    }
    const pad = { l: 64, r: 12, t: 32, b: 28 };
    const vals = d.map((x) => x.value);
    const ma = vals.map((_, i) => {
      const s = vals.slice(Math.max(0, i - 6), i + 1);
      return s.reduce((a, b) => a + b, 0) / s.length;
    });
    let min = Math.min(...vals), max = Math.max(...vals);
    if (min === max) { min -= 1; max += 1; }
    const span = max - min; min -= span * 0.05; max += span * 0.05;
    const x = (i) => pad.l + (i / (d.length - 1)) * (W - pad.l - pad.r);
    const y = (v) => pad.t + (1 - (v - min) / (max - min)) * (H - pad.t - pad.b);

    // 가로 눈금
    ctx.strokeStyle = color("--border");
    ctx.fillStyle = color("--muted");
    ctx.lineWidth = 1;
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    const compact = new Intl.NumberFormat("ko-KR", { notation: "compact", maximumFractionDigits: 1 });
    for (let k = 0; k <= 4; k++) {
      const v = min + ((max - min) * k) / 4;
      const yy = Math.round(y(v)) + 0.5;
      ctx.beginPath(); ctx.moveTo(pad.l, yy); ctx.lineTo(W - pad.r, yy); ctx.stroke();
      ctx.fillText(compact.format(v), pad.l - 8, yy);
    }
    // 날짜 라벨
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    const ticks = Math.min(6, d.length);
    for (let k = 0; k < ticks; k++) {
      const i = Math.round((k / (ticks - 1)) * (d.length - 1));
      ctx.fillText(d[i].date.slice(5), Math.min(Math.max(x(i), pad.l + 16), W - pad.r - 16), H - pad.b + 8);
    }

    const line = (arr, stroke, width, alpha) => {
      ctx.globalAlpha = alpha;
      ctx.strokeStyle = stroke;
      ctx.lineWidth = width;
      ctx.lineJoin = "round";
      ctx.beginPath();
      arr.forEach((v, i) => (i ? ctx.lineTo(x(i), y(v)) : ctx.moveTo(x(i), y(v))));
      ctx.stroke();
      ctx.globalAlpha = 1;
    };
    line(vals, color("--chart-line"), 1.5, 0.55);
    line(ma, color("--chart-avg"), 2.5, 1);

    // 범례
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";
    const legend = [["일별 값", "--chart-line"], ["7일 이동평균", "--chart-avg"]];
    let lx = pad.l + 8;
    for (const [label, c] of legend) {
      ctx.fillStyle = color(c);
      ctx.fillRect(lx, 9, 14, 3);
      ctx.fillStyle = color("--text");
      ctx.fillText(label, lx + 20, 11);
      lx += ctx.measureText(label).width + 40;
    }
  }

  // ---------------- 대화 기록 ----------------
  async function loadConversations() {
    try {
      state.conversations = await api("/api/conversations");
    } catch (e) {
      toast("대화 목록을 불러오지 못했어요: " + e.message, true);
      return;
    }
    renderConversations();
  }

  function renderConversations() {
    const list = $("convList");
    list.replaceChildren();
    $("convEmpty").hidden = state.conversations.length > 0;
    for (const c of state.conversations) {
      const date = c.updated_at ? new Date(c.updated_at).toLocaleString("ko-KR", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "";
      list.append(
        el("li", { class: "conv-item" + (c.id === state.conversationId ? " active" : "") },
          el("button", { class: "conv-open", title: c.title, onclick: () => openConversation(c.id) },
            el("span", { class: "t", text: c.title }),
            el("span", { class: "d", text: `${date} · 메시지 ${c.message_count}개` })),
          el("button", { class: "conv-del", "aria-label": "대화 삭제", title: "삭제", text: "✕", onclick: () => deleteConversation(c) }),
        ),
      );
    }
  }

  async function openConversation(id) {
    closeSidebar();
    switchTab("chat");
    const box = $("messages");
    box.replaceChildren(el("div", { class: "welcome", text: "대화를 불러오는 중…" }));
    try {
      const conv = await api(`/api/conversations/${encodeURIComponent(id)}`);
      state.conversationId = conv.id;
      box.replaceChildren();
      conv.messages.forEach((m) => addMessage(m.role, m.content));
      renderConversations();
    } catch (e) {
      toast("대화를 불러오지 못했어요: " + e.message, true);
      newChat();
    }
  }

  async function deleteConversation(c) {
    if (!confirm(`"${c.title}" 대화를 삭제할까요?`)) return;
    try {
      await api(`/api/conversations/${encodeURIComponent(c.id)}`, { method: "DELETE" });
      if (state.conversationId === c.id) newChat();
      toast("대화를 삭제했어요.");
      await loadConversations();
    } catch (e) {
      toast("삭제 실패: " + e.message, true);
    }
  }

  // ---------------- 채팅 ----------------
  const SUGGESTIONS = ["이번 달 실적이 어때?", "가장 실적이 좋았던 때는?", "최근 추세를 요약해 줘", "월별로 비교해 줘"];

  function newChat() {
    state.conversationId = null;
    closeSidebar();
    const box = $("messages");
    box.replaceChildren(
      el("div", { class: "welcome" },
        el("h2", { text: "무엇이 궁금하세요?" }),
        el("p", { text: "저장된 데이터 요약을 바탕으로 답해 드려요." }),
        el("div", { class: "suggestions" },
          SUGGESTIONS.map((q) => el("button", { type: "button", text: q, onclick: () => sendMessage(q) })))),
    );
    renderConversations();
    $("chatInput").focus();
  }

  function addMessage(role, text) {
    const box = $("messages");
    box.querySelector(".welcome")?.remove();
    const node = el("div", { class: `msg ${role}`, text });
    box.append(node);
    box.scrollTop = box.scrollHeight;
    return node;
  }

  function showTyping() {
    const node = el("div", { class: "msg assistant" },
      el("span", { class: "typing" }, el("i"), el("i"), el("i"), el("span", { text: "데이터를 분석하는 중…" })));
    $("messages").append(node);
    $("messages").scrollTop = $("messages").scrollHeight;
    return node;
  }

  async function sendMessage(text) {
    text = (text || "").trim();
    if (!text || state.sending) return;
    state.sending = true;
    $("sendBtn").disabled = true;
    $("chatInput").value = "";
    autoGrow();
    addMessage("user", text);
    const typing = showTyping();
    try {
      const res = await api("/api/chat", {
        method: "POST",
        body: JSON.stringify({ message: text, conversation_id: state.conversationId }),
      });
      typing.remove();
      addMessage("assistant", res.reply);
      const isNew = state.conversationId !== res.conversation_id;
      state.conversationId = res.conversation_id;
      await loadConversations();
      if (isNew) toast("대화가 자동 저장됐어요.");
    } catch (e) {
      typing.remove();
      addMessage("error", "답변을 받지 못했어요: " + e.message);
    } finally {
      state.sending = false;
      $("sendBtn").disabled = false;
      $("chatInput").focus();
    }
  }

  function autoGrow() {
    const t = $("chatInput");
    t.style.height = "auto";
    t.style.height = Math.min(t.scrollHeight, 140) + "px";
  }

  // ---------------- UI ----------------
  function switchTab(name) {
    document.querySelectorAll(".tab").forEach((t) => {
      const on = t.dataset.tab === name;
      t.classList.toggle("active", on);
      t.setAttribute("aria-selected", on);
    });
    $("panel-chat").hidden = name !== "chat";
    $("panel-data").hidden = name !== "data";
    if (name === "data") drawChart();
  }

  function closeSidebar() { $("sidebar").classList.remove("open"); }

  function applyThemeIcon() {
    const dark = document.documentElement.dataset.theme === "dark" ||
      (!document.documentElement.dataset.theme && matchMedia("(prefers-color-scheme: dark)").matches);
    if (!document.documentElement.dataset.theme) document.documentElement.dataset.theme = dark ? "dark" : "light";
    $("themeToggle").textContent = dark ? "☀️" : "🌙";
  }

  function toggleTheme() {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("theme", next); } catch (_) { /* 저장 불가 환경 */ }
    applyThemeIcon();
    drawChart();
  }

  function bind() {
    $("chatForm").addEventListener("submit", (e) => { e.preventDefault(); sendMessage($("chatInput").value); });
    $("chatInput").addEventListener("input", autoGrow);
    $("chatInput").addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); sendMessage($("chatInput").value); }
    });
    $("newChatBtn").addEventListener("click", newChat);
    $("dataForm").addEventListener("submit", submitData);
    $("formCancel").addEventListener("click", resetForm);
    $("exportCsv").addEventListener("click", exportCsv);
    $("exportJson").addEventListener("click", exportJson);
    $("themeToggle").addEventListener("click", toggleTheme);
    $("sidebarToggle").addEventListener("click", () => $("sidebar").classList.toggle("open"));
    document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => switchTab(t.dataset.tab)));
    let rt;
    window.addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(drawChart, 150); });
  }

  async function init() {
    bind();
    applyThemeIcon();
    resetForm();
    newChat();
    const ok = await wakeServer();
    if (ok) await Promise.all([loadSummary(), loadData(), loadConversations()]);
  }

  document.addEventListener("DOMContentLoaded", init);
})();
