# Central de Solicitações

MVP web para centralizar e acompanhar solicitações internas entre Comercial e Logística. Implementa cadastro de pedidos, fila por status, transições controladas e histórico auditável.

## Tecnologias

- Python 3.12 e Flask
- SQLite
- HTML e CSS responsivos
- pytest e GitHub Actions
- Gunicorn e configuração de deploy no Render

## Execução local

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
flask --app app init-db
flask --app app run
```

Contas fictícias de demonstração: `comercial.teste` e `logistica.teste`, ambas com senha `teste123`.

## Testes

Execute `pytest -q`. O pipeline de CI repete a suíte em cada push e pull request.

## Escopo

RF01 a RF06: cadastro, fila, atualização sequencial de status, consulta do andamento e histórico, além de filtro por status. Integração com ERP, estoque completo, app nativo e modo offline permanecem fora do MVP.

## Produção e monitoramento

O arquivo `render.yaml` descreve o serviço web, instala as dependências, inicializa o banco e executa a aplicação com Gunicorn. O endpoint público `/health` responde em JSON e é utilizado para verificar a disponibilidade do serviço.
