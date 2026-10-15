# Segurança do MVP

- Senhas são armazenadas com hash `scrypt` e nunca em texto simples.
- Consultas SQLite usam parâmetros para reduzir risco de injeção.
- Autorização por setor é validada no servidor.
- Mensagens de erro não exibem detalhes internos.
- A chave de sessão deve ser configurada por variável de ambiente em produção.

Antes de uma implantação real, o servidor deve usar HTTPS, proteção CSRF, limitação de tentativas de login, expiração de sessão e cópias de segurança do banco.
