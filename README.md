# Radar CORE | Diamante Geração de Energia

Painel executivo de Comercialização e Regulação (CORE), com edição semanal e arquivo histórico.

**Site:** https://corediamante.github.io/radar-core-diamante/

## Estrutura
- `index.html`: edição principal vigente, atualizada exclusivamente nas terças-feiras. Confirmar a data exibida no próprio painel antes de divulgar.
- `edicoes/`: histórico oficial das terças-feiras (06, 13, 20 e 27/10 e 03/11/2026). Os arquivos históricos não devem ser alterados em seu conteúdo analítico; ajustes de navegação são permitidos.
- `dados/fontes-radar.json`: cadastro canônico de fontes, métodos e evidências. Preservar histórico.
- `scripts/`: rotinas auxiliares de coleta e auditoria. Não publicam valores automaticamente.
- `.github/workflows/pages.yml`: publicação do site por GitHub Pages.
- `.github/workflows/coleta-core.yml` e `auditoria-fontes.yml`: conferências auxiliares.

## Regra do menu Edições
Exibir somente edições oficiais existentes no repositório. A edição atual é sempre `index.html`; as anteriores ficam em `edicoes/`, com datas históricas preservadas. Não criar edições TESTE, datas fictícias ou links inexistentes. O botão de atos abre `atos.html`. O visual das edições usa `assets/core-theme.css`, sem substituir os fatos publicados em cada data.

## Verificação e publicação
A cada push na `main`, `.github/workflows/pages.yml` executa `scripts/validar_site.py` antes de publicar. A validação confere HTML básico, IDs, links internos, CSS compartilhado e JSON local. O pacote do GitHub Pages inclui apenas `index.html`, `atos.html`, `assets/`, `edicoes/` e `dados/`; scripts, documentação e workflows ficam fora do site público. A validação não substitui checagem de fontes, acessibilidade, links externos nem conferência visual após o deploy.

## Atualizações futuras
Consultar primeiro o cadastro canônico, validar fontes e indicadores, preservar as evidências e registrar pendências. Arquivar a edição anterior antes de substituir o `index.html`. Verificar o deploy e o HTML público antes de declarar publicação concluída. Para novas edições, respeitar a política editorial vigente e atualizar conscientemente a lista de edições visíveis.

## Atos atualizados (diário)
- `atos.html`: página independente com seleção da data de coleta.
- `dados/atos-aneel.json`: histórico de datas com atos pertinentes e metadados da última execução. Datas sem ocorrências não são exibidas nem registradas como edições.
- A pesquisa editorial e atualização de `dados/atos-aneel.json` são executadas por duas automações do ChatGPT, diariamente às 10h e às 17h (horário de Brasília), inclusive finais de semana. A segunda execução confere possíveis omissões da primeira. Ambas cruzam DOU, CEDOC, notícias oficiais da ANEEL, Leis.org (inclusive pesquisa indexada), CanalEnergia, MegaWhat e TCU. Notícias e acórdãos são fontes de alerta, não atos da ANEEL; somente atos com publicação documental confirmada entram no histórico.
- O monitor experimental antigo do GitHub Actions foi removido por redundância e falhas de coleta; o histórico regulatório foi preservado.
- A listagem do Leis.org pode ter acesso automatizado limitado; a integração estruturada do INLABS ainda depende de credenciais e testes reais. O último diagnóstico registrado no JSON pode ser histórico e não deve ser confundido com o resultado das automações atuais; a pesquisa indexada complementa a coleta, que pode ter cobertura incompleta. Resultados precisam de validação editorial. A ausência de resultado não comprova ausência de ato. Sempre conferir o DOU e os anexos antes de tratar valores como definitivos.
- A rotina diária não altera o conteúdo analítico nem a periodicidade das edições completas do Radar. A edição principal é atualizada às terças-feiras às 13h (Brasília), pela automação própria. O botão **Atos do dia** fica imediatamente ao lado do seletor **Edições**, abrindo a área específica de atos, com seleção somente das datas em que foram encontrados atos pertinentes.
