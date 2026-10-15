CREATE TABLE IF NOT EXISTS colaborador (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT NOT NULL,
  identificador_acesso TEXT NOT NULL UNIQUE,
  setor TEXT NOT NULL CHECK (setor IN ('Comercial', 'Logística')),
  senha_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS solicitacao (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  produto TEXT NOT NULL,
  codigo TEXT,
  quantidade INTEGER NOT NULL CHECK (quantidade > 0),
  observacao TEXT,
  criado_em TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('Aguardando', 'Em separação', 'Concluído')),
  solicitante_id INTEGER NOT NULL REFERENCES colaborador(id)
);
CREATE TABLE IF NOT EXISTS historico_status (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  solicitacao_id INTEGER NOT NULL REFERENCES solicitacao(id),
  colaborador_id INTEGER NOT NULL REFERENCES colaborador(id),
  status_anterior TEXT,
  status_novo TEXT NOT NULL,
  alterado_em TEXT NOT NULL
);
