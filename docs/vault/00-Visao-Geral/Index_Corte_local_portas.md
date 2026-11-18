---
projeto: "Corte local portas"
data_criacao: 2026-11-18
status: ativo
tags: [index, arquitetura, portas, pcp]
---

# Visão Geral: Corte local portas

**Resumo:** Sistema web (FastAPI + SPA HTML/CSS/JS) que consulta ao vivo as Ordens de Produção do local `PORTAS` no ERP (`http://192.168.0.6/pcp/op_abertura.php`), extrai estruturalmente medidas, modelos, puxadores, divisórias e acabamentos das descrições, calcula as listas de corte de perfis com descontos configuráveis e exporta para Excel/CSV/JSON.

## Arquitetura e Fluxo

```mermaid
graph TD
    UI[Frontend SPA: ./frontend/index.html + app.js] -->|POST /api/extract/erp| API[FastAPI: ./backend/main.py]
    API -->|Sessao PHPSESSID ou Login| ERP[ERP Client: ./backend/app/erp_client.py]
    ERP -->|POST op_abertura.php| SRV[(Servidor ERP 192.168.0.6)]
    API -->|HTML Bruto| HTMLP[HTML Parser: ./backend/app/html_parser.py]
    HTMLP -->|RawOpRow| DESCP[Description Parser: ./backend/app/description_parser.py]
    DESCP -->|ExtractedItem| CUT[Cutting Engine: ./backend/app/cutting_engine.py]
    RULES[(Regras JSON: ./backend/app/data/regras_corte.json)] -->|Descontos mm| CUT
    CUT -->|Itens + Barras + Resumo| API
    API -->|XLSX / CSV / JSON| EXP[Exporter: ./backend/app/exporter.py]
```

## Índice de Módulos

- [[01-Frontend-UI/Interface-Web-Corte-Portas]]
- [[02-Backend-API/API-Extracao-ERP-Portas]]
- [[03-Dominio-Calculos/Regras-Extracao-e-Corte-Perfis]]
- [[04-Infra-Dados/Integracao-HTTP-ERP]]
- [[05-Automacoes/Inicializacao-Servidor-Local]]
- [[Corte-local-portas-logbook/LOGBOOK_INDEX]]
