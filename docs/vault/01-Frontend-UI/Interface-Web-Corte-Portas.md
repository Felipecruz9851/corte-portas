---
modulo: "frontend/src/* (Vite + React + Tailwind CSS)"
tipo: "frontend"
linguagem: "javascript-react-css"
data_atualizacao: 2026-11-19
tags: [codigo, frontend, react, vite, tailwind, ui, lider-design]
---

# Módulo: Interface Web — Corte local portas (Lider Design)

**Responsabilidade:** Aplicação SPA em **React + Vite + Tailwind CSS** estilizada conforme a identidade visual **Lider Design** (`./docs/referencias/Guia_Consolidado_UI_UX_Lider.md` e `./docs/referencias/Guia de Identidade UI_UX_ Estilo Lider Design.md`), oferecendo consulta ao vivo do ERP (`PHPSESSID` ou Usuário/Senha), upload e drag-and-drop de um ou múltiplos arquivos HTML locais (com adição incremental ao lote e remoção individual), cartões de KPIs, abas navegáveis por teclado (`Construção das Peças`, `Plano de Corte de Barras`, `Otimização Barras 6m`, `Plano de Corte de Vidros` e `Regras e Descontos (mm)`), modal 2D proporcional em SVG e exportação direta.

## Arquitetura e Componentes (`./frontend/src/`)
* `App.jsx`: Orquestração de estado (React Hooks, incluindo estado `loadedHtmlFiles`, leitura UTF-8/ISO-8859-1, adição incremental com deduplicação, remoção por arquivo e limpeza via `POST /api/session/clear`), abas com `focusgroup="tablist nomemory"` e `hidden="until-found"`, chamadas REST (incluindo `POST /api/optimize/bars`) e controle de modal.
* `components/Sidebar.jsx`: Barra lateral fixa à esquerda (recolhível em desktop e drawer em mobile) exibindo a logomarca `./frontend/public/logo_lider.png` no topo esquerdo, formulário ERP, zona de seleção múltipla e drag-and-drop de arquivos HTML locais (`.html`/`.htm`) com lista de arquivos carregados (truncamento `.file-name-truncate` preservando extensão, contagem de linhas por arquivo, remoção individual, botão `Limpar` e zona para adicionar mais arquivos ao lote), banner de status e resumo da sessão (incluindo `Origens` quando há múltiplos lotes).
* `components/Header.jsx`: Cabeçalho fixo no topo com fallback da logomarca no topo esquerdo quando recolhida/mobile, título editorial com contagem de arquivos/lotes no subtítulo e ações globais de exportação (`Excel .xlsx`, `CSV Itens`, `CSV Serra`, `CSV Vidros`, `JSON`).
* `components/MetricsCards.jsx`: Grid responsivo com 6 cartões minimalistas de métricas (`#FFFFFF` sobre canvas `#F8F8F8`, borda `#E0E0E0`, sombra difusa `rgba(0,0,0,0.05)`).
* `components/ItemsTab.jsx`: Filtros combinados, ordenação por coluna e tabela responsiva (empilhamento em cards via `@container (width < 640px)`).
* `components/BarsCutTab.jsx` & `components/GlassCutTab.jsx`: Alternância Agrupado/Detalhado, exibição de `Cód. Perfil` e coluna de ângulos (`angulos_corte`) nas barras, filtro por modelo, busca rápida e totalizadores dinâmicos.
* `components/OptimizationTab.jsx`: Parâmetros configuráveis (`Barra (mm)`, `Serra / Kerf (mm)`, `Desponte (mm)` e `Separar por acabamento`, sem o campo `Perda Máxima`), seletor comparativo entre os 2 cenários em cards de rádio dinâmicos (`Cenário 1 — Aproveitamento de Material` e `Cenário 2 — Tempo de Execução (Maior → Menor)`), faixa de **5 KPIs dinâmicos por filtro** (`Barras 6m`, `Aproveit. Médio / Barra`, `Perda Total` + economia de chanfro `//`, `Ajustes no Corte` exibindo trocas de medida e trocas de ângulo `45°↔90°`, e `Grupos de Perfil`) calculados em `useMemo` (`filterScenarioAndComputeMetrics` + `reannotateSequentialAdjustments`), legenda visual `AngleLegend` (`Simétrico //` vs `Assimétrico \/`), **diagrama 1D em SVG com chanfros reais e encaixe paralelo/em V** (trapézios alternados normal `/¯¯¯\` + invertido `\___/` em `//` ou `/¯¯¯\ /¯¯¯\` em `\/`), badges de cabeçalho nos grupos e `BarCard` (`Simétrico //`, `Assimétrico \/`, `Econ. //`), tags `// gir.` / `\/` + coluna `Ângulos` na sequência de cortes e em `ExecutionRouteTable`, com exportações CSV (`CSV Material`, `CSV Tempo (Roteiro)`, `CSV Tempo (Barras)`) enviando o recorte filtrado.
* `components/RulesTab.jsx`: Edição em grade das regras por modelo, incluindo `Tipo de Corte` (`45°`, `45° / 90° (Misto)`, `90°`), seletores de ângulo por encontro (`Âng. Quadro`, `Âng. Puxador`, `Âng. Divisória`) com sincronização automática, checkboxes `Simét. Lat. (//)` e `Simét. Pux. (//)` (`perfil_simetrico_lateral` / `perfil_simetrico_puxador`), cadastro de `Cód. Perfil Lateral` e `Cód. Perfil Puxador`, e cálculo automático em tempo real de `desconto_adjacente_puxador_mm`.
* `components/PieceDetailDialog.jsx`: Modal nativo `<dialog closedby="any">` com navegação Anterior/Próxima, diagrama 2D SVG na paleta Lider Design (`#222222`, `#8B5A2B`, `#A0522D`) e detalhamento técnico incluindo coluna `Ângulos` na tabela `Barras para Corte`.

## Dependências (Grafo)
**⬅️ Quem chama este módulo (Entrada):**
* Navegador do usuário via `./backend/main.py` (`GET /`, `/logo_lider.png` e `/static/*` servindo `./frontend/dist/`) ou `vite dev` na porta `5173` com proxy `/api`.

**➡️ Quem este módulo chama (Saída/Uso):**
* [[02-Backend-API/API-Extracao-ERP-Portas]]
* **Bibliotecas Externas:** `react`, `react-dom`, `lucide-react`, `tailwindcss`, `vite`.
