# Radar CORE | Grupo Diamante

Painel executivo de inteligência regulatória e de mercado.

**Site:** https://corediamante.github.io/radar-core-diamante/

## Estrutura
- `index.html`: edição principal vigente (27/10/2026, terça-feira). Atualizar somente nas terças-feiras.
- `edicoes/`: histórico oficial das terças-feiras (06, 13, 20 e 27/10/2026). Os arquivos históricos não devem ser alterados em seu conteúdo analítico; ajustes de navegação são permitidos.
- `dados/fontes-radar.json`: cadastro canônico de fontes, métodos e evidências. Preservar histórico.
- `scripts/`: rotinas auxiliares de coleta e auditoria. Não publicam valores automaticamente.
- `.github/workflows/pages.yml`: publicação do site por GitHub Pages.
- `.github/workflows/coleta-core.yml` e `auditoria-fontes.yml`: conferências auxiliares.

## Regra do menu Edições
Mostrar somente as terças-feiras oficiais: 27, 20, 13 e 06/10/2026, incluindo as próximas edições oficiais quando forem publicadas. A edição atual de 27/10 aponta para `index.html`; o histórico de 27/10 permanece disponível. Não mostrar edições TESTE, nem incluir datas não oficiais. Cada página deve indicar corretamente a edição visualizada. Manter o botão `Atos do dia` imediatamente ao lado de `Edições`, em todas as páginas oficiais. Não usar scripts que reescrevam `.edition-menu`.

## Atualizações futuras
Consultar primeiro o cadastro canônico, validar fontes e indicadores, preservar as evidências e registrar pendências. Arquivar a edição anterior antes de substituir o `index.html`. Verificar o deploy e o HTML público antes de declarar publicação concluída. Para novas edições, respeitar a política editorial vigente e atualizar conscientemente a lista de edições visíveis.

## Atos atualizados (diário)
- `atos.html`: página independente com seleção da data de coleta.
- `dados/atos-aneel.json`: histórico diário e status de conferência.
- `scripts/monitorar_atos_aneel.py`: triagem por Diamante, CTJL, Pecém I/II, Itaqui, CER 478/25 e processo CTJL.
- `.github/workflows/atos-aneel-diario.yml`: execução agendada diariamente às 13h UTC (10h de Brasília, UTC-3), inclusive finais de semana; o GitHub Actions pode iniciar com atraso.
- A lista pública do Leis.org pode ser parcial ou exigir JavaScript; coletas incompletas são identificadas como inconclusivas/parciais. A ausência de resultado não comprova ausência de ato. Sempre conferir o DOU e os anexos antes de tratar valores como definitivos.
- A rotina diária não altera o conteúdo analítico nem a periodicidade das edições completas do Radar. A edição principal é atualizada às terças-feiras às 13h (Brasília), pela automação própria. O botão **Atos do dia** fica imediatamente ao lado do seletor **Edições**, abrindo a área específica de atos, com seleção de datas e registros vazios quando nenhum ato relevante for identificado.
