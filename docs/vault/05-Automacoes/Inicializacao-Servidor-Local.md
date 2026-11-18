---
modulo: "backend/run.py"
tipo: "automacao"
linguagem: "python"
data_atualizacao: 2026-11-18
tags: [automacao, servidor, uvicorn]
---

# Módulo: Inicialização do Servidor Local

**Gatilho:** Execução direta `python ./backend/run.py` (variáveis opcionais `HOST`, padrão `127.0.0.1`, e `PORT`, padrão `8085`).

## Fluxo de Execução
1. Adiciona `./backend` ao `sys.path`.
2. Inicia o servidor `uvicorn` carregando `main:app`.
3. Disponibiliza a interface web em `http://127.0.0.1:8085/`.

## Dependências
* [[02-Backend-API/API-Extracao-ERP-Portas]]
