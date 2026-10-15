import sqlite3
import pytest
from app import create_app

@pytest.fixture()
def app(tmp_path):
    application = create_app({"TESTING": True, "SECRET_KEY": "test", "DATABASE": str(tmp_path / "test.db")})
    with application.app_context(): application.init_db()
    yield application

@pytest.fixture()
def client(app): return app.test_client()

def login(client, username):
    return client.post("/login", data={"username": username, "password": "teste123"}, follow_redirects=True)

def test_login_rejects_invalid_credentials(client):
    response = client.post("/login", data={"username": "inexistente", "password": "x"})
    assert response.status_code == 200
    assert "Identificador ou senha inválidos".encode() in response.data

def test_comercial_creates_request_and_history(client, app):
    login(client, "comercial.teste")
    response = client.post("/solicitacoes/nova", data={"produto": "Caixa para presente", "codigo": "00123", "quantidade": "2", "observacao": "Separar para atendimento interno"}, follow_redirects=True)
    assert response.status_code == 200 and b"SOL-001" in response.data
    with app.app_context():
        db = sqlite3.connect(app.config["DATABASE"])
        assert db.execute("SELECT codigo, quantidade, status FROM solicitacao").fetchone() == ("00123", 2, "Aguardando")
        assert db.execute("SELECT status_anterior, status_novo FROM historico_status").fetchone() == (None, "Aguardando")

def test_logistica_updates_status_in_sequence(client, app):
    login(client, "comercial.teste")
    client.post("/solicitacoes/nova", data={"produto": "Caixa", "quantidade": "2"})
    client.post("/logout"); login(client, "logistica.teste")
    assert client.post("/solicitacoes/1/status", data={"status": "Em separação"}).status_code == 302
    assert client.post("/solicitacoes/1/status", data={"status": "Concluído"}).status_code == 302
    with app.app_context():
        db = sqlite3.connect(app.config["DATABASE"])
        assert db.execute("SELECT status FROM solicitacao WHERE id=1").fetchone()[0] == "Concluído"
        assert db.execute("SELECT COUNT(*) FROM historico_status WHERE solicitacao_id=1").fetchone()[0] == 3

def test_comercial_cannot_update_status(client):
    login(client, "comercial.teste")
    assert client.post("/solicitacoes/1/status", data={"status": "Em separação"}).status_code == 403

def test_invalid_quantity_is_not_persisted(client, app):
    login(client, "comercial.teste")
    response = client.post("/solicitacoes/nova", data={"produto": "Caixa", "quantidade": "0"})
    assert b"quantidade maior que zero" in response.data
    with app.app_context():
        db = sqlite3.connect(app.config["DATABASE"])
        assert db.execute("SELECT COUNT(*) FROM solicitacao").fetchone()[0] == 0

