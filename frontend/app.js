/* Cliente SPA para Extrator Construtivo e Plano de Corte — PORTAS */

const STATE = {
  payload: null,
  filteredItems: [],
  rules: {},
};

const els = {
  erpForm: document.getElementById("erp-form"),
  erpData: document.getElementById("erp-data"),
  erpDatasExtra: document.getElementById("erp-datas-extra"),
  erpEmpresa: document.getElementById("erp-empresa"),
  erpLocal: document.getElementById("erp-local"),
  erpPhpsessid: document.getElementById("erp-phpsessid"),
  erpUsuario: document.getElementById("erp-usuario"),
  erpSenha: document.getElementById("erp-senha"),
  authCookieRadio: document.getElementById("auth-cookie"),
  authCredsRadio: document.getElementById("auth-creds"),
  authCookieBox: document.getElementById("auth-cookie-box"),
  authCredsBox: document.getElementById("auth-creds-box"),
  btnConsultarErp: document.getElementById("btn-consultar-erp"),
  btnLoadHtml: document.getElementById("btn-load-html"),
  htmlFileInput: document.getElementById("html-file-input"),
  statusBanner: document.getElementById("status-banner"),
  kpisSection: document.getElementById("kpis-section"),

  btnExportXlsx: document.getElementById("btn-export-xlsx"),
  btnExportCsvItems: document.getElementById("btn-export-csv-items"),
  btnExportCsvCorte: document.getElementById("btn-export-csv-corte"),
  btnExportCsvVidro: document.getElementById("btn-export-csv-vidro"),
  btnExportJson: document.getElementById("btn-export-json"),

  fBusca: document.getElementById("f-busca"),
  fModelo: document.getElementById("f-modelo"),
  fPuxador: document.getElementById("f-puxador"),
  fDivisoria: document.getElementById("f-divisoria"),
  fEntrega: document.getElementById("f-entrega"),
  itemsTbody: document.getElementById("items-tbody"),
  itemsCountLabel: document.getElementById("items-count-label"),

  corteThead: document.getElementById("corte-thead"),
  corteTbody: document.getElementById("corte-tbody"),
  corteCountLabel: document.getElementById("corte-count-label"),
  fCorteModelo: document.getElementById("f-corte-modelo"),
  corteAgrupadoRadio: document.getElementById("corte-agrupado"),
  corteDetalhadoRadio: document.getElementById("corte-detalhado"),

  vidrosThead: document.getElementById("vidros-thead"),
  vidrosTbody: document.getElementById("vidros-tbody"),
  vidroCountLabel: document.getElementById("vidro-count-label"),
  fVidroModelo: document.getElementById("f-vidro-modelo"),
  vidroAgrupadoRadio: document.getElementById("vidro-agrupado"),
  vidroDetalhadoRadio: document.getElementById("vidro-detalhado"),

  rulesTbody: document.getElementById("rules-tbody"),
  btnSaveRules: document.getElementById("btn-save-rules"),
  btnResetRules: document.getElementById("btn-reset-rules"),

  detailDialog: document.getElementById("detail-dialog"),
  dialogTitle: document.getElementById("dialog-title"),
  dialogSubtitle: document.getElementById("dialog-subtitle"),
  svgContainer: document.getElementById("svg-container"),
  detailDl: document.getElementById("detail-dl"),
  detailBarsTbody: document.getElementById("detail-bars-tbody"),
  detailGlassTbody: document.getElementById("detail-glass-tbody"),
  detailRawDesc: document.getElementById("detail-raw-desc"),
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function fmtNum(val) {
  if (val === null || val === undefined || val === "") return "-";
  const n = Number(val);
  if (Number.isNaN(n)) return escapeHtml(val);
  return Number.isInteger(n) ? String(n) : n.toFixed(2).replace(/\.?0+$/, "");
}

function setStatus(message, kind = "") {
  els.statusBanner.textContent = message;
  els.statusBanner.className = "status-banner" + (kind ? ` ${kind}` : "");
}

function toggleAuthBoxes() {
  const useCookie = els.authCookieRadio.checked;
  els.authCookieBox.hidden = !useCookie;
  els.authCredsBox.hidden = useCookie;
}

// Tabs com teclado + hidden="until-found"
function setupTabs() {
  const tablist = document.querySelector('[role="tablist"]');
  const tabs = Array.from(tablist.querySelectorAll('[role="tab"]'));
  const panels = Array.from(document.querySelectorAll('[role="tabpanel"]'));

  function selectTab(targetTab) {
    tabs.forEach((tab) => {
      const selected = tab === targetTab;
      tab.setAttribute("aria-selected", String(selected));
      tab.toggleAttribute("focusgroupstart", selected);
    });
    panels.forEach((panel) => {
      const active = panel.getAttribute("aria-labelledby") === targetTab.id;
      if (active) {
        panel.removeAttribute("hidden");
        panel.setAttribute("tabindex", "0");
      } else {
        panel.setAttribute("hidden", "until-found");
        panel.removeAttribute("tabindex");
      }
    });
  }

  tabs.forEach((tab, idx) => {
    tab.addEventListener("click", () => selectTab(tab));
    tab.addEventListener("keydown", (e) => {
      if (e.key === "ArrowRight") {
        const next = tabs[(idx + 1) % tabs.length];
        next.focus();
        selectTab(next);
      } else if (e.key === "ArrowLeft") {
        const prev = tabs[(idx - 1 + tabs.length) % tabs.length];
        prev.focus();
        selectTab(prev);
      }
    });
  });

  panels.forEach((panel) => {
    panel.addEventListener("beforematch", () => {
      const tab = document.getElementById(panel.getAttribute("aria-labelledby"));
      if (tab) selectTab(tab);
    });
  });
}

// Fallback para browsers sem closedby="any"
function setupDialogFallback() {
  if (!("closedBy" in HTMLDialogElement.prototype)) {
    els.detailDialog.addEventListener("click", (event) => {
      if (event.target !== els.detailDialog) return;
      const rect = els.detailDialog.getBoundingClientRect();
      const inside =
        rect.top <= event.clientY &&
        event.clientY <= rect.top + rect.height &&
        rect.left <= event.clientX &&
        event.clientX <= rect.left + rect.width;
      if (!inside) els.detailDialog.close();
    });
  }
}

function applyPayload(payload) {
  STATE.payload = payload;
  if (payload.rules) {
    STATE.rules = payload.rules;
    renderRulesTable();
  }
  renderKpis(payload.kpis, payload.meta);
  populateFilters(payload.items);
  applyItemFilters();
  renderCorteTable();
  renderVidrosTable();

  const hasData = payload.items && payload.items.length > 0;
  els.btnExportXlsx.disabled = !hasData;
  els.btnExportCsvItems.disabled = !hasData;
  els.btnExportCsvCorte.disabled = !hasData;
  els.btnExportCsvVidro.disabled = !hasData;
  els.btnExportJson.disabled = !hasData;
}

function renderKpis(kpis, meta) {
  els.kpisSection.hidden = false;
  document.getElementById("kpi-linhas").textContent = kpis.total_linhas_op;
  document.getElementById("kpi-pecas").textContent = `${kpis.total_pecas_op} peças`;
  document.getElementById("kpi-estruturas").textContent = kpis.total_estruturas;
  document.getElementById("kpi-especiais").textContent = `${kpis.itens_especiais} especiais`;
  document.getElementById("kpi-barras").textContent = kpis.total_barras_corte;
  document.getElementById("kpi-metros").textContent = `${kpis.total_metros_lineares} m lineares`;
  document.getElementById("kpi-vidros").textContent = kpis.total_pecas_vidro ?? 0;
  document.getElementById("kpi-area-vidros").textContent = `${kpis.total_area_vidro_m2 ?? 0} m²`;
  document.getElementById("kpi-puxadores").textContent = kpis.total_puxadores;
  document.getElementById("kpi-itens-pux").textContent = `${kpis.itens_com_puxador} itens c/ puxador`;
  document.getElementById("kpi-divisorias").textContent = kpis.itens_com_divisoria;
  const datas = (meta?.datas_abertura || []).join(", ") || "-";
  document.getElementById("kpi-origem").textContent = `Abertura: ${datas}`;
}

function populateFilters(items) {
  const modelos = Array.from(new Set(items.map((i) => i.modelo))).sort();
  const puxadores = Array.from(new Set(items.map((i) => i.posicao_puxador))).sort();
  const entregas = Array.from(new Set(items.map((i) => i.data_entrega).filter(Boolean))).sort();

  function fillSelect(sel, values, defaultLabel) {
    const prev = sel.value;
    sel.innerHTML = `<option value="">${escapeHtml(defaultLabel)}</option>` +
      values.map((v) => `<option value="${escapeHtml(v)}">${escapeHtml(v)}</option>`).join("");
    if (values.includes(prev)) sel.value = prev;
  }

  fillSelect(els.fModelo, modelos, "Todos");
  fillSelect(els.fCorteModelo, modelos, "Todos");
  fillSelect(els.fVidroModelo, modelos, "Todos");
  fillSelect(els.fPuxador, puxadores, "Todas");
  fillSelect(els.fEntrega, entregas, "Todas");
}

function applyItemFilters() {
  if (!STATE.payload) return;
  const q = els.fBusca.value.trim().toLowerCase();
  const modelo = els.fModelo.value;
  const pux = els.fPuxador.value;
  const div = els.fDivisoria.value;
  const ent = els.fEntrega.value;

  const filtered = STATE.payload.items.filter((it) => {
    if (modelo && it.modelo !== modelo) return false;
    if (pux && it.posicao_puxador !== pux) return false;
    if (div === "sim" && !it.tem_divisorias) return false;
    if (div === "nao" && it.tem_divisorias) return false;
    if (ent && it.data_entrega !== ent) return false;
    if (q) {
      const hay = [
        it.op,
        it.codigo,
        it.pedido,
        it.modelo,
        it.categoria,
        it.acabamento_perfil,
        it.acabamento_placa,
        it.descricao,
      ]
        .join(" ")
        .toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });

  STATE.filteredItems = filtered;
  renderItemsTable(filtered);
}

function renderItemsTable(items) {
  els.itemsCountLabel.textContent = `${items.length} item(ns) exibido(s)`;
  if (!items.length) {
    els.itemsTbody.innerHTML =
      '<tr><td colspan="15" class="empty-cell">Nenhum item corresponde aos filtros.</td></tr>';
    return;
  }

  els.itemsTbody.innerHTML = items
    .map((it, idx) => {
      const puxLabel = it.tem_puxador
        ? `<span class="badge badge-accent">${it.qtd_puxadores}x</span> ${escapeHtml(it.posicao_puxador)}`
        : `<span class="badge">0 · SEM PUXADOR</span>`;

      const divLabel = it.tem_divisorias
        ? `<span class="badge badge-ok">${it.qtd_divisorias}x</span> ${escapeHtml(
            (it.divisorias_mm || []).map((d) => `${fmtNum(d)}mm`).join(", ")
          )}`
        : "Não";

      return `
        <tr data-item-index="${idx}">
          <th data-label="OP">${escapeHtml(it.op)}</th>
          <td data-label="Código"><code>${escapeHtml(it.codigo)}</code></td>
          <td data-label="Pedido">${escapeHtml(it.pedido)}</td>
          <td data-label="Entrega">${escapeHtml(it.data_entrega)}</td>
          <td data-label="Categoria">${escapeHtml(it.subcategoria || it.categoria)}</td>
          <td data-label="Modelo"><span class="badge">${escapeHtml(it.modelo)}</span></td>
          <td data-label="Qtd" class="num">${fmtNum(it.quantidade)}</td>
          <td data-label="Quadros" class="num">${it.qtd_estruturas}</td>
          <td data-label="Largura (mm)" class="num">${fmtNum(it.largura_mm)}</td>
          <td data-label="Altura (mm)" class="num">${fmtNum(it.altura_mm)}</td>
          <td data-label="Puxadores">${puxLabel}</td>
          <td data-label="Divisórias">${divLabel}</td>
          <td data-label="Perfil">${escapeHtml(it.acabamento_perfil || "-")}</td>
          <td data-label="Placa / Vidro">${escapeHtml(it.acabamento_placa || "-")}</td>
          <td data-label="Furação">${escapeHtml(it.furacao || "-")}</td>
        </tr>
      `;
    })
    .join("");
}

function renderCorteTable() {
  if (!STATE.payload) return;
  const isAgrupado = els.corteAgrupadoRadio.checked;
  const modeloFilter = els.fCorteModelo.value;

  if (isAgrupado) {
    const rows = (STATE.payload.corte_agrupado || []).filter(
      (r) => !modeloFilter || r.modelo === modeloFilter
    );
    els.corteCountLabel.textContent = `${rows.length} grupo(s) de corte`;
    els.corteThead.innerHTML = `
      <tr>
        <th>Modelo</th>
        <th>Acabamento Perfil</th>
        <th>Função da Barra</th>
        <th>Orientação</th>
        <th>Puxador?</th>
        <th>Tipo Corte</th>
        <th>Qtd Barras</th>
        <th>Medida Corte (mm)</th>
        <th>Total (m)</th>
        <th>OPs</th>
      </tr>
    `;
    if (!rows.length) {
      els.corteTbody.innerHTML =
        '<tr><td colspan="10" class="empty-cell">Nenhuma barra para este filtro.</td></tr>';
      return;
    }
    els.corteTbody.innerHTML = rows
      .map(
        (r) => `
      <tr>
        <th><span class="badge">${escapeHtml(r.modelo)}</span></th>
        <td>${escapeHtml(r.acabamento_perfil)}</td>
        <td>${escapeHtml(r.funcao_barra)}</td>
        <td>${escapeHtml(r.orientacao)}</td>
        <td>${r.eh_perfil_puxador ? '<span class="badge badge-accent">Sim</span>' : "Não"}</td>
        <td>${escapeHtml(r.tipo_corte)}</td>
        <td class="num"><strong>${r.qtd_barras}</strong></td>
        <td class="num"><strong>${fmtNum(r.medida_corte_mm)}</strong></td>
        <td class="num">${fmtNum(r.total_metros)}</td>
        <td>${escapeHtml(r.ops)}</td>
      </tr>
    `
      )
      .join("");
  } else {
    const rows = (STATE.payload.corte_detalhado || []).filter(
      (r) => !modeloFilter || r.modelo === modeloFilter
    );
    els.corteCountLabel.textContent = `${rows.length} linha(s) de corte por OP`;
    els.corteThead.innerHTML = `
      <tr>
        <th>OP</th>
        <th>Código</th>
        <th>Entrega</th>
        <th>Modelo</th>
        <th>Acabamento</th>
        <th>Função da Barra</th>
        <th>Qtd</th>
        <th>Nominal (mm)</th>
        <th>Desc. (mm)</th>
        <th>Corte (mm)</th>
        <th>Obs.</th>
      </tr>
    `;
    if (!rows.length) {
      els.corteTbody.innerHTML =
        '<tr><td colspan="11" class="empty-cell">Nenhuma barra para este filtro.</td></tr>';
      return;
    }
    els.corteTbody.innerHTML = rows
      .map(
        (r) => `
      <tr>
        <th>${escapeHtml(r.op)}</th>
        <td><code>${escapeHtml(r.codigo)}</code></td>
        <td>${escapeHtml(r.data_entrega)}</td>
        <td><span class="badge">${escapeHtml(r.modelo)}</span></td>
        <td>${escapeHtml(r.acabamento_perfil)}</td>
        <td>${escapeHtml(r.funcao_barra)}</td>
        <td class="num"><strong>${r.qtd_barras}</strong></td>
        <td class="num">${fmtNum(r.medida_nominal_mm)}</td>
        <td class="num">${fmtNum(r.desconto_mm)}</td>
        <td class="num"><strong>${fmtNum(r.medida_corte_mm)}</strong></td>
        <td>${escapeHtml(r.observacao_corte || "")}</td>
      </tr>
    `
      )
      .join("");
  }
}

function renderVidrosTable() {
  if (!STATE.payload) return;
  const isAgrupado = els.vidroAgrupadoRadio.checked;
  const modeloFilter = els.fVidroModelo.value;

  if (isAgrupado) {
    const rows = (STATE.payload.vidro_agrupado || []).filter(
      (r) => !modeloFilter || r.modelo === modeloFilter
    );
    els.vidroCountLabel.textContent = `${rows.length} medida(s) de vidro`;
    els.vidrosThead.innerHTML = `
      <tr>
        <th>Modelo</th>
        <th>Acabamento / Placa</th>
        <th>Qtd Peças</th>
        <th>Largura Corte (mm)</th>
        <th>Altura Corte (mm)</th>
        <th>Regra Largura</th>
        <th>Regra Altura</th>
        <th>Área (m²)</th>
        <th>OPs</th>
      </tr>
    `;
    if (!rows.length) {
      els.vidrosTbody.innerHTML =
        '<tr><td colspan="9" class="empty-cell">Nenhum vidro para este filtro.</td></tr>';
      return;
    }
    els.vidrosTbody.innerHTML = rows
      .map(
        (r) => `
      <tr>
        <th><span class="badge">${escapeHtml(r.modelo)}</span></th>
        <td>${escapeHtml(r.acabamento_placa)}</td>
        <td class="num"><strong>${r.qtd_pecas}</strong></td>
        <td class="num"><strong>${fmtNum(r.largura_corte_mm)}</strong></td>
        <td class="num"><strong>${fmtNum(r.altura_corte_mm)}</strong></td>
        <td>${escapeHtml(r.regra_largura)}</td>
        <td>${escapeHtml(r.regra_altura)}</td>
        <td class="num">${fmtNum(r.area_m2)}</td>
        <td>${escapeHtml(r.ops)}</td>
      </tr>
    `
      )
      .join("");
  } else {
    const rows = (STATE.payload.vidro_detalhado || []).filter(
      (r) => !modeloFilter || r.modelo === modeloFilter
    );
    els.vidroCountLabel.textContent = `${rows.length} linha(s) de vidro por OP`;
    els.vidrosThead.innerHTML = `
      <tr>
        <th>OP</th>
        <th>Código</th>
        <th>Entrega</th>
        <th>Modelo</th>
        <th>Acabamento / Placa</th>
        <th>Posição Puxador</th>
        <th>Qtd</th>
        <th>Larg. Nom.</th>
        <th>Desc. L</th>
        <th>Larg. Corte (mm)</th>
        <th>Alt. Nom.</th>
        <th>Desc. A</th>
        <th>Alt. Corte (mm)</th>
        <th>Área (m²)</th>
      </tr>
    `;
    if (!rows.length) {
      els.vidrosTbody.innerHTML =
        '<tr><td colspan="14" class="empty-cell">Nenhum vidro para este filtro.</td></tr>';
      return;
    }
    els.vidrosTbody.innerHTML = rows
      .map(
        (r) => `
      <tr>
        <th>${escapeHtml(r.op)}</th>
        <td><code>${escapeHtml(r.codigo)}</code></td>
        <td>${escapeHtml(r.data_entrega)}</td>
        <td><span class="badge">${escapeHtml(r.modelo)}</span></td>
        <td>${escapeHtml(r.acabamento_placa)}</td>
        <td>${escapeHtml(r.posicao_puxador)}</td>
        <td class="num"><strong>${r.qtd_pecas}</strong></td>
        <td class="num">${fmtNum(r.largura_nominal_mm)}</td>
        <td class="num">${fmtNum(r.desconto_largura_mm)}</td>
        <td class="num"><strong>${fmtNum(r.largura_corte_mm)}</strong></td>
        <td class="num">${fmtNum(r.altura_nominal_mm)}</td>
        <td class="num">${fmtNum(r.desconto_altura_mm)}</td>
        <td class="num"><strong>${fmtNum(r.altura_corte_mm)}</strong></td>
        <td class="num">${fmtNum(r.area_m2)}</td>
      </tr>
    `
      )
      .join("");
  }
}

function renderRulesTable() {
  const keys = Object.keys(STATE.rules).sort();
  els.rulesTbody.innerHTML = keys
    .map((key) => {
      const r = STATE.rules[key];
      return `
        <tr data-rule-key="${escapeHtml(key)}">
          <th><span class="badge">${escapeHtml(r.modelo)}</span></th>
          <td>${escapeHtml(r.descricao)}</td>
          <td>
            <select class="rule-select" data-field="tipo_corte" aria-label="Tipo de corte para ${escapeHtml(r.modelo)}">
              <option value="45°" ${r.tipo_corte === "45°" ? "selected" : ""}>45°</option>
              <option value="90° (Topo)" ${r.tipo_corte === "90° (Topo)" ? "selected" : ""}>90° (Topo)</option>
              <option value="90° (Explícito)" ${r.tipo_corte === "90° (Explícito)" ? "selected" : ""}>90° (Explícito)</option>
            </select>
          </td>
          <td><input type="number" step="0.5" min="0" class="rule-input" data-field="largura_perfil_quadro_mm" aria-label="Largura do perfil quadro em mm para ${escapeHtml(r.modelo)}" value="${r.largura_perfil_quadro_mm ?? 0}"></td>
          <td><input type="number" step="0.5" min="0" class="rule-input" data-field="largura_perfil_puxador_mm" aria-label="Largura do perfil puxador em mm para ${escapeHtml(r.modelo)}" value="${r.largura_perfil_puxador_mm ?? 0}"></td>
          <td><input type="number" step="0.5" min="0" class="rule-input" data-field="desconto_adjacente_puxador_mm" aria-label="Desconto adjacente ao puxador em mm para ${escapeHtml(r.modelo)}" value="${r.desconto_adjacente_puxador_mm ?? 0}"></td>
          <td><input type="number" step="0.5" class="rule-input" data-field="desconto_vertical_mm" aria-label="Desconto fixo vertical em mm para ${escapeHtml(r.modelo)}" value="${r.desconto_vertical_mm}"></td>
          <td><input type="number" step="0.5" class="rule-input" data-field="desconto_horizontal_mm" aria-label="Desconto fixo horizontal em mm para ${escapeHtml(r.modelo)}" value="${r.desconto_horizontal_mm}"></td>
          <td><input type="number" step="0.5" class="rule-input" data-field="desconto_divisoria_mm" aria-label="Desconto fixo divisória em mm para ${escapeHtml(r.modelo)}" value="${r.desconto_divisoria_mm}"></td>
          <td><input type="number" step="0.5" min="0" class="rule-input" data-field="desconto_vidro_lateral_mm" aria-label="Desconto vidro lateral em mm por lado para ${escapeHtml(r.modelo)}" value="${r.desconto_vidro_lateral_mm ?? 0}"></td>
          <td><input type="number" step="0.5" min="0" class="rule-input" data-field="desconto_vidro_puxador_mm" aria-label="Desconto vidro lado puxador em mm por lado para ${escapeHtml(r.modelo)}" value="${r.desconto_vidro_puxador_mm ?? 0}"></td>
          <td>${escapeHtml(r.observacao || "")}</td>
        </tr>
      `;
    })
    .join("");
}

function buildPieceSvg(item) {
  const w = Number(item.largura_mm) || 400;
  const h = Number(item.altura_mm) || (item.eh_barra_avulsa ? 60 : 800);

  const maxW = 220;
  const maxH = 260;
  const scale = Math.min(maxW / w, maxH / h);
  const drawW = Math.max(40, Math.round(w * scale));
  const drawH = Math.max(24, Math.round(h * scale));

  const padX = 65;
  const padY = 40;
  const svgW = drawW + padX * 2;
  const svgH = drawH + padY * 2;

  const rects = [];
  // Quadro base
  rects.push(
    `<rect x="${padX}" y="${padY}" width="${drawW}" height="${drawH}" fill="none" stroke="currentColor" stroke-width="4" />`
  );

  // Destaque do(s) puxador(es)
  const puxColor = "#2563eb";
  if (item.tem_puxador) {
    if (item.posicao_puxador === "SUPERIOR" || item.posicao_puxador === "HORIZONTAL (BASCULA/GAVETA)") {
      rects.push(
        `<line x1="${padX}" y1="${padY}" x2="${padX + drawW}" y2="${padY}" stroke="${puxColor}" stroke-width="7" />`
      );
    } else if (item.posicao_puxador === "DUPLO (DIREITA E ESQUERDA)") {
      rects.push(
        `<line x1="${padX}" y1="${padY}" x2="${padX}" y2="${padY + drawH}" stroke="${puxColor}" stroke-width="7" />`,
        `<line x1="${padX + drawW}" y1="${padY}" x2="${padX + drawW}" y2="${padY + drawH}" stroke="${puxColor}" stroke-width="7" />`
      );
    } else if (item.lado === "DIREITA") {
      rects.push(
        `<line x1="${padX + drawW}" y1="${padY}" x2="${padX + drawW}" y2="${padY + drawH}" stroke="${puxColor}" stroke-width="7" />`
      );
    } else {
      rects.push(
        `<line x1="${padX}" y1="${padY}" x2="${padX}" y2="${padY + drawH}" stroke="${puxColor}" stroke-width="7" />`
      );
    }
  }

  // Divisórias internas (medida a partir da base inferior)
  const divs = item.divisorias_mm || [];
  divs.forEach((posMm) => {
    const y = padY + drawH - (posMm / h) * drawH;
    if (y >= padY && y <= padY + drawH) {
      rects.push(
        `<line x1="${padX}" y1="${y.toFixed(1)}" x2="${padX + drawW}" y2="${y.toFixed(1)}" stroke="#d97706" stroke-width="3" />`,
        `<text x="${padX + drawW + 8}" y="${(y + 4).toFixed(1)}" font-size="11" fill="#d97706">${fmtNum(posMm)}mm</text>`
      );
    }
  });

  // Cotas de largura e altura
  rects.push(
    `<text x="${padX + drawW / 2}" y="${padY - 12}" text-anchor="middle" font-size="12" font-weight="bold" fill="currentColor">L: ${fmtNum(w)} mm</text>`,
    `<text x="${padX - 10}" y="${padY + drawH / 2}" text-anchor="end" font-size="12" font-weight="bold" fill="currentColor">A: ${fmtNum(h)} mm</text>`
  );

  return `<svg viewBox="0 0 ${svgW} ${svgH}" width="100%" style="max-width:380px; height:auto;">${rects.join("")}</svg>`;
}

function openItemDetail(item) {
  els.dialogTitle.textContent = `${item.codigo} · OP ${item.op}`;
  els.dialogSubtitle.textContent = `${item.categoria} (${item.modelo}) · Pedido ${item.pedido} · Entrega ${item.data_entrega}`;
  els.svgContainer.innerHTML = buildPieceSvg(item);

  const specs = [
    ["Modelo / Perfil", `${item.modelo} ${item.codigo_perfil ? `(${item.codigo_perfil})` : ""}`],
    ["Quantidade OP", `${fmtNum(item.quantidade)} · Estruturas/Escadas: ${item.qtd_estruturas}`],
    ["Medidas", `${fmtNum(item.largura_mm)} x ${fmtNum(item.altura_mm)} mm`],
    ["Lado / Folha", `${item.lado} · ${item.posicao_folha}`],
    ["Puxadores", `${item.qtd_puxadores}x · ${item.posicao_puxador} ${item.tipo_puxador ? `(${item.tipo_puxador})` : ""}`],
    ["Divisórias", item.tem_divisorias ? item.detalhe_divisorias : "Sem divisórias"],
    ["Acabamento Perfil", item.acabamento_perfil || "-"],
    ["Acabamento Placa", item.acabamento_placa || "-"],
    ["Sistema / Furação", `${item.sistema || "-"} · ${item.furacao || "-"}`],
  ];

  els.detailDl.innerHTML = specs
    .map(([k, v]) => `<dt>${escapeHtml(k)}</dt><dd>${escapeHtml(v)}</dd>`)
    .join("");

  els.detailBarsTbody.innerHTML = (item.barras_corte || [])
    .map(
      (b) => `
      <tr>
        <td>${escapeHtml(b.funcao_barra)}</td>
        <td class="num"><strong>${b.qtd_barras}</strong></td>
        <td class="num">${fmtNum(b.medida_nominal_mm)}</td>
        <td class="num">${fmtNum(b.desconto_mm)}</td>
        <td class="num"><strong>${fmtNum(b.medida_corte_mm)}</strong></td>
        <td>${escapeHtml(b.observacao_corte || "-")}</td>
      </tr>
    `
    )
    .join("");

  const vidros = item.vidros_corte || [];
  els.detailGlassTbody.innerHTML = vidros.length
    ? vidros
        .map(
          (g) => `
        <tr>
          <td>${escapeHtml(g.acabamento_placa)}</td>
          <td class="num"><strong>${g.qtd_pecas}</strong></td>
          <td class="num"><strong>${fmtNum(g.largura_corte_mm)} mm</strong></td>
          <td class="num"><strong>${fmtNum(g.altura_corte_mm)} mm</strong></td>
          <td>L: -${fmtNum(g.desconto_largura_mm)} (${escapeHtml(g.regra_largura)}) · A: -${fmtNum(g.desconto_altura_mm)} (${escapeHtml(g.regra_altura)})</td>
        </tr>
      `
        )
        .join("")
    : '<tr><td colspan="5">Item sem placa/vidro para corte.</td></tr>';

  els.detailRawDesc.textContent = item.descricao;
  els.detailDialog.showModal();
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || `Erro HTTP ${response.status}`);
  }
  return data;
}

async function handleErpSubmit(event) {
  event.preventDefault();
  const dataPrincipal = els.erpData.value.trim();
  const extras = els.erpDatasExtra.value
    .split(/[,;\s]+/)
    .map((s) => s.trim())
    .filter(Boolean);
  const datas = Array.from(new Set([dataPrincipal, ...extras].filter(Boolean)));

  const body = {
    datas,
    cod_empresa: els.erpEmpresa.value.trim() || "11",
    local: els.erpLocal.value.trim() || "PORTAS",
    item_desc: "S",
  };

  if (els.authCookieRadio.checked) {
    body.phpsessid = els.erpPhpsessid.value.trim();
  } else {
    body.usuario = els.erpUsuario.value.trim();
    body.senha = els.erpSenha.value;
  }

  els.btnConsultarErp.disabled = true;
  setStatus(`Consultando ERP (${datas.join(", ")})...`);
  try {
    const payload = await fetchJson("/api/extract/erp", {
      method: "POST",
      body: JSON.stringify(body),
    });
    applyPayload(payload);
    setStatus(
      `Extração concluída: ${payload.kpis.total_linhas_op} linhas e ${payload.kpis.total_barras_corte} barras calculadas.`,
      "ok"
    );
  } catch (err) {
    setStatus(err.message, "err");
  } finally {
    els.btnConsultarErp.disabled = false;
  }
}

async function handleLocalHtmlUpload(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  setStatus(`Processando ${file.name}...`);
  try {
    const html = await file.text();
    const payload = await fetchJson("/api/extract/html", {
      method: "POST",
      body: JSON.stringify({ html, source_name: file.name }),
    });
    applyPayload(payload);
    setStatus(
      `Arquivo ${file.name} processado: ${payload.kpis.total_linhas_op} linhas e ${payload.kpis.total_barras_corte} barras.`,
      "ok"
    );
  } catch (err) {
    setStatus(err.message, "err");
  } finally {
    els.htmlFileInput.value = "";
  }
}

async function handleSaveRules() {
  const updated = {};
  els.rulesTbody.querySelectorAll("tr[data-rule-key]").forEach((tr) => {
    const key = tr.dataset.ruleKey;
    const base = { ...STATE.rules[key] };
    tr.querySelectorAll("[data-field]").forEach((input) => {
      const field = input.dataset.field;
      base[field] =
        field === "tipo_corte" ? input.value : Number(input.value) || 0;
    });
    updated[key] = base;
  });

  setStatus("Salvando regras e recalculando barras...");
  try {
    const res = await fetchJson("/api/rules", {
      method: "PUT",
      body: JSON.stringify({ rules: updated }),
    });
    STATE.rules = res.rules;
    renderRulesTable();
    if (res.recalculated) {
      applyPayload(res.recalculated);
    }
    setStatus("Regras salvas e plano de corte recalculado.", "ok");
  } catch (err) {
    setStatus(err.message, "err");
  }
}

async function handleResetRules() {
  setStatus("Restaurando regras padrão...");
  try {
    const res = await fetchJson("/api/rules/reset", { method: "POST" });
    STATE.rules = res.rules;
    renderRulesTable();
    if (res.recalculated) {
      applyPayload(res.recalculated);
    }
    setStatus("Regras restauradas para os padrões configurados.", "ok");
  } catch (err) {
    setStatus(err.message, "err");
  }
}

async function downloadExport(endpoint, body, fallbackFilename) {
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || "Falha ao gerar arquivo.");
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = fallbackFilename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } catch (err) {
    setStatus(err.message, "err");
  }
}

async function init() {
  setupTabs();
  setupDialogFallback();

  els.authCookieRadio.addEventListener("change", toggleAuthBoxes);
  els.authCredsRadio.addEventListener("change", toggleAuthBoxes);
  els.erpForm.addEventListener("submit", handleErpSubmit);
  els.btnLoadHtml.addEventListener("click", () => els.htmlFileInput.click());
  els.htmlFileInput.addEventListener("change", handleLocalHtmlUpload);

  [els.fBusca, els.fModelo, els.fPuxador, els.fDivisoria, els.fEntrega].forEach(
    (el) => el.addEventListener("input", applyItemFilters)
  );
  [els.corteAgrupadoRadio, els.corteDetalhadoRadio, els.fCorteModelo].forEach(
    (el) => el.addEventListener("change", renderCorteTable)
  );
  [els.vidroAgrupadoRadio, els.vidroDetalhadoRadio, els.fVidroModelo].forEach(
    (el) => el.addEventListener("change", renderVidrosTable)
  );

  els.itemsTbody.addEventListener("click", (event) => {
    const tr = event.target.closest("tr[data-item-index]");
    if (!tr) return;
    const item = STATE.filteredItems[Number(tr.dataset.itemIndex)];
    if (item) openItemDetail(item);
  });

  els.rulesTbody.addEventListener("input", (event) => {
    const input = event.target;
    if (
      input.dataset.field === "largura_perfil_quadro_mm" ||
      input.dataset.field === "largura_perfil_puxador_mm"
    ) {
      const tr = input.closest("tr[data-rule-key]");
      if (!tr) return;
      const quadro = Number(tr.querySelector('[data-field="largura_perfil_quadro_mm"]').value) || 0;
      const pux = Number(tr.querySelector('[data-field="largura_perfil_puxador_mm"]').value) || 0;
      const adjInput = tr.querySelector('[data-field="desconto_adjacente_puxador_mm"]');
      if (adjInput && (quadro > 0 || pux > 0)) {
        adjInput.value = String(Math.max(0, pux - quadro));
      }
    }
  });

  els.btnSaveRules.addEventListener("click", handleSaveRules);
  els.btnResetRules.addEventListener("click", handleResetRules);

  els.btnExportXlsx.addEventListener("click", () =>
    downloadExport("/api/export/xlsx", {}, "plano_corte_portas.xlsx")
  );
  els.btnExportCsvItems.addEventListener("click", () =>
    downloadExport("/api/export/csv", { mode: "items" }, "itens_portas.csv")
  );
  els.btnExportCsvCorte.addEventListener("click", () =>
    downloadExport("/api/export/csv", { mode: "corte" }, "corte_serra_portas.csv")
  );
  els.btnExportCsvVidro.addEventListener("click", () =>
    downloadExport("/api/export/csv", { mode: "vidro" }, "corte_vidros_portas.csv")
  );
  els.btnExportJson.addEventListener("click", () =>
    downloadExport("/api/export/json", {}, "extracao_portas.json")
  );

  try {
    const res = await fetchJson("/api/rules");
    STATE.rules = res.rules;
    renderRulesTable();
  } catch (err) {
    setStatus(`Erro ao carregar regras iniciais: ${err.message}`, "err");
  }
}

init();
