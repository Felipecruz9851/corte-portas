---
modulo: "frontend/src/* (Vite + React + Tailwind CSS)"
tipo: "frontend"
linguagem: "javascript-react-css"
data_atualizacao: 2026-11-19
tags: [codigo, frontend, react, vite, tailwind, ui, lider-design]
---

# Módulo: Interface Web — Corte local portas (Lider Design)

**Responsabilidade:** Aplicação SPA em **React + Vite + Tailwind CSS** estilizada conforme a identidade visual **Lider Design** (`./docs/referencias/Guia_Consolidado_UI_UX_Lider.md` e `./docs/referencias/Guia de Identidade UI_UX_ Estilo Lider Design.md`), oferecendo consulta ao vivo do ERP (`PHPSESSID` ou Usuário/Senha), upload/drag-and-drop de HTML local, cartões de KPIs, abas navegáveis por teclado (`Construção das Peças`, `Plano de Corte de Barras`, `Plano de Corte de Vidros` e `Regras e Descontos (mm)`), modal 2D proporcional em SVG e exportação direta.

## Arquitetura e Componentes (`./frontend/src/`)
* `App.jsx`: Orquestração de estado (React Hooks), abas com `focusgroup="tablist nomemory"` e `hidden="until-found"`, chamadas REST e controle de modal.
* `components/Sidebar.jsx`: Barra lateral fixa à esquerda (recolhível em desktop e drawer em mobile) exibindo a logomarca `./frontend/public/logo_lider.png` no topo esquerdo, formulário ERP, zona de drag-and-drop HTML, banner de status e resumo da sessão.
* `components/Header.jsx`: Cabeçalho fixo no topo com fallback da logomarca no topo esquerdo quando recolhida/mobile, título editorial e ações globais de exportação (`Excel .xlsx`, `CSV Itens`, `CSV Serra`, `CSV Vidros`, `JSON`).
* `components/MetricsCards.jsx`: Grid responsivo com 6 cartões minimalistas de métricas (`#FFFFFF` sobre canvas `#F8F8F8`, borda `#E0E0E0`, sombra difusa `rgba(0,0,0,0.05)`).
* `components/ItemsTab.jsx`: Filtros combinados, ordenação por coluna e tabela responsiva (empilhamento em cards via `@container (width < 640px)`).
* `components/BarsCutTab.jsx` & `components/GlassCutTab.jsx`: Alternância Agrupado/Detalhado, filtro por modelo, busca rápida e totalizadores dinâmicos.
* `components/RulesTab.jsx`: Edição em grade das regras por modelo com cálculo automático em tempo real de `desconto_adjacente_puxador_mm`.
* `components/PieceDetailDialog.jsx`: Modal nativo `<dialog closedby="any">` com navegação Anterior/Próxima, diagrama 2D SVG na paleta Lider Design (`#222222`, `#8B5A2B`, `#A0522D`) e detalhamento técnico.

## Dependências (Grafo)
**⬅️ Quem chama este módulo (Entrada):**
* Navegador do usuário via `./backend/main.py` (`GET /`, `/logo_lider.png` e `/static/*` servindo `./frontend/dist/`) ou `vite dev` na porta `5173` com proxy `/api`.

**➡️ Quem este módulo chama (Saída/Uso):**
* [[02-Backend-API/API-Extracao-ERP-Portas]]
* **Bibliotecas Externas:** `react`, `react-dom`, `lucide-react`, `tailwindcss`, `vite`.
