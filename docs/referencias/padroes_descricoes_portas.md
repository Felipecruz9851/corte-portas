# Padrões de Descrições — Local `PORTAS` (`op_abertura.php`)

Catalogação baseada nos 143 arquivos HTML de 2026 (2.337 linhas de item) em `PORTAS`.

## 1. Linha ALLU (`2ESCAA`, `2LATAL`, `2NICHA`, `2PEALU`, `2ILHA`, `2ESTAL`)
- **Estrutura:** Quadro fechado nas dimensões `LARGURA x ALTURA` (2 barras verticais + 2 horizontais; ou 1 horizontal quando `ALLU EM U` / `FORMATO DE U`) + travessas internas na largura conforme `DIVISORIA <N> - <POS>MM`.
- **Multiplicador:** `PRODUZIR UMA ESCADA` (1), `DUAS ESCADAS` (2), `TRES ESCADAS` (3), `QUATRO ESCADAS` (4).
- **Barras avulsas:** `BARRA ALLU - ENVIAR SOMENTE A BARRA...`, `ESPECIAL CORTE BARRA ALLU COM FURO...`, `ESPECIAL ENVIAR APENAR A BARRA CORTADA...`, `ESPECIAL LATERAL NICHO ALLU PERFIL LINEAR`.

## 2. Portas, Básculas e Gavetas
- **Modelos identificados:**
  - `CATCH` (`PERLARE - 5307/5317`)
  - `PERFIL 5307` (`PERFIL 5307 S/PUXADOR - PERLARE - 5307`)
  - `DJEI` (`5307/6817` ou `5307/5307`)
  - `CLEAR S` (`CLEAR_S_PUXADOR` com puxador vs `CLEAR S/PUXADOR` sem puxador)
  - `CLEAR G` (`CLEAR G C/PUXADOR`)
  - `RISK` (`RISK USINADO`, `RISK INCLINADO`, `RISK SEM USINAGEM`, `RISK`)
  - `GROOVE` (`CORRER GROOVE`)
  - `INTEIRA` (`CORRER INTEIRA`)
  - `SINGULAR` (`CORRER SINGULAR`)
- **Puxadores:**
  - `0` (`SEM PUXADOR`): `S/PUXADOR`, `S/ PUXADOR`, `SEM PUXADOR`, `SEM PUXADRO`, `_SEM PUX`, `SEM USINAGEM`.
  - `2` (`DUPLO (DIREITA E ESQUERDA)`): `C/ PUXADOR DIREITO E ESQUERDO`, `LATERAL DIREITA E LATERAL ESQUERDA`, `PUXADOR DIREITA E ESQUERDA`, `PUXADOR DOS DOIS LADOS`.
  - `1` (`SUPERIOR`, `LATERAL (DIREITA/ESQUERDA)` ou `HORIZONTAL (BASCULA/GAVETA)`).
- **Divisórias em portas:**
  - `TRAVESSA (DE DIVISÃO) A <POS>MM DA PARTE DE BAIXO`
  - `DIVISAO A <POS> MM DA PARTE INFERIOR`
  - `VAO INFERIOR <X>_VAO CENTRAL <Y>_VAO SUPERIOR <Z>` (2 divisórias entre os 3 vãos).

## 3. Cristaleira Provence Urda & Tampo/Prateleira Visor
- **Cristaleira (`2PTUR...`):** `MINI KENDO + BAGUETE (3PERUNO6BG215B)` com cortes explícitos `02 UNIDADES MEDIDA <H> MM E 02 UNIDADES MEDIDA <V> MM`.
- **Visor (`2TPVI...` / `2PRVI...`):** Perfil `DJEI SEM PUXADOR` com `MEDIDA <L> X <P>` (ou `LARGURA <L> X PROFUNDIDADE <P>`).
