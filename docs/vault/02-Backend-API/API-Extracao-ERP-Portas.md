---
modulo: "backend/main.py + backend/app/exporter.py"
tipo: "backend"
linguagem: "python"
data_atualizacao: 2026-11-18
tags: [codigo, backend, python, fastapi]
---

# Módulo: API FastAPI e Exportador

**Responsabilidade:** Expõe os endpoints HTTP REST para consulta ao vivo do ERP, parsing de HTML, gerenciamento de regras de corte em JSON e exportação em Excel multi-abas (`.xlsx`), CSV e JSON.

## Principais Funções / Métodos
* `extract_from_erp()` (`POST /api/extract/erp`): Consulta uma ou mais datas em `http://192.168.0.6/pcp/op_abertura.php` e retorna itens extraídos, barras e KPIs.
* `extract_from_html()` (`POST /api/extract/html`): Executa o mesmo pipeline a partir de um HTML enviado.
* `get_rules()`, `update_rules()`, `reset_rules()`: Lê, atualiza e reseta `./backend/app/data/regras_corte.json` recalculando os cortes em memória.
* `export_xlsx()`, `export_csv()`, `export_json()`: Exportam planilhas formatadas via `./backend/app/exporter.py`.

## Dependências (Grafo)
**⬅️ Quem chama este módulo (Entrada):**
* [[01-Frontend-UI/Interface-Web-Corte-Portas]]

**➡️ Quem este módulo chama (Saída/Uso):**
* [[04-Infra-Dados/Integracao-HTTP-ERP]]
* [[03-Dominio-Calculos/Regras-Extracao-e-Corte-Perfis]]
* **Bibliotecas Externas:** `fastapi`, `pydantic`, `pandas`, `openpyxl`.
