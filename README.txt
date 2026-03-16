CONTROLE DE ESCOLTAS - PROJETO PRONTO

Usuário inicial:
- usuário: admin
- senha: admin123

Se usar online no Streamlit, configure o Secrets assim:
DATABASE_URL = "sua_string_postgres"

Se usar localmente, sem DATABASE_URL, o sistema usa SQLite automaticamente.

Páginas:
- Início
- Agentes
- Rotas
- Lançamentos
- Fechamento (admin)
- Backup (admin)
- Usuários (admin)

Perfis:
- admin: vê tudo
- operador: não vê recebimento, total a receber, lucro, fechamento, backup, usuários
