---
modulo: "frontend/index.html + frontend/app.js + frontend/styles.css"
tipo: "frontend"
linguagem: "html-css-javascript"
data_atualizacao: 2026-11-18
tags: [codigo, frontend, javascript, ui]
---

# Módulo: Interface Web — Corte local portas

**Responsabilidade:** Fornece o painel de consulta ao vivo do ERP (`PHPSESSID` ou Usuário/Senha), cards de KPIs, abas de Construção das Peças, Plano de Corte (agrupado e por OP), edição de descontos por modelo, modal 2D proporcional em SVG e exportação direta.

## Principais Funções / Métodos
* `handleErpSubmit()`: Envia data(s), empresa, local e credenciais para `/api/extract/erp`.
* `handleLocalHtmlUpload()`: Carrega um arquivo `.html` salvo para processamento em `/api/extract/html`.
* `applyItemFilters()` / `renderItemsTable()`: Aplica filtros por busca, modelo, posição de puxador, divisórias e entrega.
* `buildPieceSvg()` / `openItemDetail()`: Desenha o esquema 2D da peça com puxadores e cotas de divisórias dentro de `<dialog closedby="any">`.
* `handleSaveRules()` / `handleResetRules()`: Persiste alterações em `regras_corte.json` e atualiza a lista de corte.

## Dependências (Grafo)
**⬅️ Quem chama este módulo (Entrada):**
* Navegador do usuário via `./backend/main.py` (`GET /` e `/static/*`).

**➡️ Quem este módulo chama (Saída/Uso):**
* [[02-Backend-API/API-Extracao-ERP-Portas]]
* **Bibliotecas Externas:** Web Platform nativa (Fetch API, `<dialog>`, SVG, CSS `light-dark()`, `@container`).
