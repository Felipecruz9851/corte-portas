---
modulo: "backend/main.py"
tipo: "automacao"
linguagem: "python"
data_atualizacao: 2026-11-19
tags: [automacao, servidor, uvicorn]
---

# Módulo: Inicialização do Servidor Local

**Gatilho:** Execução direta `python ./backend/main.py` (variáveis opcionais `HOST`, padrão `0.0.0.0`, e `PORT`, padrão `8085`).

## Fluxo de Execução
1. Adiciona `./backend` ao `sys.path` e monta os arquivos estáticos de `./frontend/dist/static` (com fallback para `./frontend`).
2. A função `main()` inicia o servidor `uvicorn.run("main:app", host=host, port=port, reload=False)`.
3. Disponibiliza a interface web (build `./frontend/dist/`) em `http://127.0.0.1:8085/`.

## Dependências
* [[02-Backend-API/API-Extracao-ERP-Portas]]
