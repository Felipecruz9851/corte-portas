---
modulo: "backend/app/erp_client.py + backend/app/html_parser.py"
tipo: "infra"
linguagem: "python"
data_atualizacao: 2026-11-18
tags: [codigo, infra, python, http]
---

# Módulo: Integração HTTP com ERP e Parser HTML

**Responsabilidade:** Realiza requisições `POST` autenticadas ao endpoint `http://192.168.0.6/pcp/op_abertura.php` (via cookie `PHPSESSID` ou login automático em `/home/login/`) e converte a resposta HTML do PCP em registros estruturados `RawOpRow`.

## Principais Funções / Métodos
* `ERPClient.login_with_credentials()`: Autentica usuário/senha no ERP e captura o cookie `PHPSESSID`.
* `ERPClient.fetch_op_abertura()`: Executa `POST` com `cod_empresa`, `data`, `local` e `item_desc=S`, tratando UTF-8/ISO-8859-1 e detectando sessão expirada.
* `parse_op_html()`: Extrai cabeçalho (`local_producao`, `data_abertura`), seções de `Data de Entrega` e ignora linhas de sumário/rodapé.

## Dependências (Grafo)
**⬅️ Quem chama este módulo (Entrada):**
* [[02-Backend-API/API-Extracao-ERP-Portas]]

**➡️ Quem este módulo chama (Saída/Uso):**
* [[03-Dominio-Calculos/Regras-Extracao-e-Corte-Perfis]]
* **Bibliotecas Externas:** `requests`, `beautifulsoup4`.
