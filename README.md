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

## Atos do Dia (monitoramento de publicações diretas)

- `atos.html`: página editorial de atos, organizada pelas datas efetivas de publicação; inclui ANEEL, MME, IBAMA e outros órgãos apenas quando há relação DIRETA com ativos ou pessoas jurídicas do Grupo.
- `dados/atos-aneel.json`: base pública dos documentos editorialmente conferidos. Não cadastrar notícias, candidatos, links genéricos, publicações homônimas, nem deslocar atos antigos para datas recentes.
- `scripts/monitorar_aneel.py`: triagem complementar do GitHub Actions, em dias úteis e sob demanda. Inspeciona títulos de páginas institucionais, notícias indexadas e, quando autorizado, o conteúdo integral de XMLs do DOU pelo INLABS. O resultado é preservado no artefato `triagem-aneel-core`; NÃO é publicação automática.
- Para ativar a varredura documental do DOU: criar conta gratuita em https://inlabs.in.gov.br; adicionar no repositório GitHub em **Settings → Secrets and variables → Actions → New repository secret** os secrets `INLABS_EMAIL` e `INLABS_PASSWORD`. Não escrever senhas no código nem em arquivos versionados. A compatibilidade do acesso INLABS a partir do GitHub Actions precisa ser verificada após essa configuração; redes de datacenter podem sofrer bloqueios.
- A rotina envia uma lista de candidatos à avaliação. Duas automações editoriais do ChatGPT, às 10h e às 17h (Brasília), estão encarregadas de pesquisar, conferir documentos oficiais e atualizar `dados/atos-aneel.json` somente após comprovar fonte específica, texto, data e vínculo direto. A edição principal do Radar permanece separada e semanal.
- Resultado com zero candidatos, falha HTTP ou ausência de credenciais NÃO comprova ausência de atos. O campo `cobertura_dou_xml` do relatório distingue busca integral no XML de pesquisa parcial.
- Os testes locais são executados por `python -m unittest discover -s scripts -p 'test_monitorar_aneel.py' -v`. O GitHub Actions valida sintaxe e classificação antes da triagem.
