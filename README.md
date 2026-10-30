# Radar CORE | Grupo Diamante

Painel executivo de inteligência regulatória e de mercado.

**Site:** https://corediamante.github.io/radar-core-diamante/

## Estrutura
- `index.html`: edição atual (30/10/2026, TESTE).
- `edicoes/`: edições oficiais das terças-feiras (06, 13, 20 e 27/10/2026) e teste de 28/10/2026. Os arquivos históricos não devem ser alterados em seu conteúdo analítico; ajustes de navegação são permitidos.
- `dados/fontes-radar.json`: cadastro canônico de fontes, métodos e evidências. Preservar histórico.
- `scripts/`: rotinas auxiliares de coleta e auditoria. Não publicam valores automaticamente.
- `.github/workflows/pages.yml`: publicação do site por GitHub Pages.
- `.github/workflows/coleta-core.yml` e `auditoria-fontes.yml`: conferências auxiliares.

## Regra do menu Edições
Mostrar somente a edição atual de 30/10 (TESTE), a edição de 28/10 (TESTE) e as terças-feiras 27, 20, 13 e 06/10. Cada página deve indicar corretamente a edição visualizada. Não inserir outras datas automaticamente e não usar scripts que reescrevam `.edition-menu`.

## Atualizações futuras
Consultar primeiro o cadastro canônico, validar fontes e indicadores, preservar as evidências e registrar pendências. Arquivar a edição anterior antes de substituir o `index.html`. Verificar o deploy e o HTML público antes de declarar publicação concluída. Para novas edições, respeitar a política editorial vigente e atualizar conscientemente a lista de edições visíveis.
