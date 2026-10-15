import os
import sqlite3
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

STATUS_FLOW = ("Aguardando", "Em separação", "Concluído")


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(SECRET_KEY=os.environ.get("SECRET_KEY", "dev-change-this-key"), DATABASE=os.path.join(app.instance_path, "central.db"))
    if test_config:
        app.config.update(test_config)
    os.makedirs(app.instance_path, exist_ok=True)

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
        return g.db

    @app.teardown_appcontext
    def close_db(_error=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def init_db():
        db = get_db()
        with app.open_resource("schema.sql") as schema:
            db.executescript(schema.read().decode("utf8"))
        users = [
            ("Comercial Exemplo", "comercial.teste", "Comercial", generate_password_hash("teste123", method="scrypt")),
            ("Operador Exemplo", "logistica.teste", "Logística", generate_password_hash("teste123", method="scrypt")),
        ]
        db.executemany("INSERT OR IGNORE INTO colaborador (nome, identificador_acesso, setor, senha_hash) VALUES (?, ?, ?, ?)", users)
        db.commit()

    app.get_db = get_db
    app.init_db = init_db

    def login_required(view):
        @wraps(view)
        def wrapped(**kwargs):
            if not session.get("user_id"):
                return redirect(url_for("login"))
            return view(**kwargs)
        return wrapped

    def require_sector(sector):
        def decorator(view):
            @wraps(view)
            @login_required
            def wrapped(**kwargs):
                if session.get("setor") != sector:
                    abort(403)
                return view(**kwargs)
            return wrapped
        return decorator

    @app.get("/")
    def index():
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return redirect(url_for("queue" if session["setor"] == "Logística" else "new_request"))

    @app.route("/login", methods=("GET", "POST"))
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = get_db().execute("SELECT * FROM colaborador WHERE identificador_acesso = ?", (username,)).fetchone()
            if user and check_password_hash(user["senha_hash"], password):
                session.clear()
                session.update(user_id=user["id"], nome=user["nome"], setor=user["setor"])
                return redirect(url_for("index"))
            flash("Identificador ou senha inválidos.", "error")
        return render_template("login.html")

    @app.post("/logout")
    @login_required
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/solicitacoes/nova", methods=("GET", "POST"))
    @require_sector("Comercial")
    def new_request():
        if request.method == "POST":
            produto = request.form.get("produto", "").strip()
            codigo = request.form.get("codigo", "").strip() or None
            observacao = request.form.get("observacao", "").strip() or None
            try:
                quantidade = int(request.form.get("quantidade", ""))
            except ValueError:
                quantidade = 0
            if not produto or quantidade <= 0:
                flash("Informe o produto e uma quantidade maior que zero.", "error")
            else:
                now = datetime.now(timezone.utc).isoformat(timespec="seconds")
                db = get_db()
                try:
                    cursor = db.execute("INSERT INTO solicitacao (produto, codigo, quantidade, observacao, criado_em, status, solicitante_id) VALUES (?, ?, ?, ?, ?, ?, ?)", (produto, codigo, quantidade, observacao, now, "Aguardando", session["user_id"]))
                    request_id = cursor.lastrowid
                    db.execute("INSERT INTO historico_status (solicitacao_id, colaborador_id, status_anterior, status_novo, alterado_em) VALUES (?, ?, ?, ?, ?)", (request_id, session["user_id"], None, "Aguardando", now))
                    db.commit()
                except sqlite3.Error:
                    db.rollback()
                    flash("Não foi possível registrar a solicitação.", "error")
                else:
                    flash(f"Solicitação SOL-{request_id:03d} enviada com status Aguardando.", "success")
                    return redirect(url_for("request_detail", request_id=request_id))
        return render_template("new_request.html")

    @app.get("/solicitacoes")
    @login_required
    def queue():
        status = request.args.get("status", "")
        sql = "SELECT s.*, c.nome AS solicitante FROM solicitacao s JOIN colaborador c ON c.id = s.solicitante_id"
        params = ()
        if status in STATUS_FLOW:
            sql += " WHERE s.status = ?"
            params = (status,)
        sql += " ORDER BY CASE s.status WHEN 'Aguardando' THEN 0 WHEN 'Em separação' THEN 1 ELSE 2 END, s.criado_em"
        rows = get_db().execute(sql, params).fetchall()
        return render_template("queue.html", requests=rows, selected_status=status, statuses=STATUS_FLOW)

    @app.get("/solicitacoes/<int:request_id>")
    @login_required
    def request_detail(request_id):
        db = get_db()
        item = db.execute("SELECT s.*, c.nome AS solicitante FROM solicitacao s JOIN colaborador c ON c.id = s.solicitante_id WHERE s.id = ?", (request_id,)).fetchone()
        if item is None:
            abort(404)
        history = db.execute("SELECT h.*, c.nome FROM historico_status h JOIN colaborador c ON c.id = h.colaborador_id WHERE h.solicitacao_id = ? ORDER BY h.alterado_em", (request_id,)).fetchall()
        current_index = STATUS_FLOW.index(item["status"])
        next_status = STATUS_FLOW[current_index + 1] if current_index < len(STATUS_FLOW) - 1 else None
        return render_template("detail.html", item=item, history=history, next_status=next_status)

    @app.post("/solicitacoes/<int:request_id>/status")
    @require_sector("Logística")
    def update_status(request_id):
        db = get_db()
        item = db.execute("SELECT status FROM solicitacao WHERE id = ?", (request_id,)).fetchone()
        if item is None:
            abort(404)
        current_index = STATUS_FLOW.index(item["status"])
        expected = STATUS_FLOW[current_index + 1] if current_index < len(STATUS_FLOW) - 1 else None
        requested_status = request.form.get("status")
        if requested_status != expected:
            abort(400)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        try:
            db.execute("UPDATE solicitacao SET status = ? WHERE id = ?", (requested_status, request_id))
            db.execute("INSERT INTO historico_status (solicitacao_id, colaborador_id, status_anterior, status_novo, alterado_em) VALUES (?, ?, ?, ?, ?)", (request_id, session["user_id"], item["status"], requested_status, now))
            db.commit()
        except sqlite3.Error:
            db.rollback()
            flash("Não foi possível atualizar o status.", "error")
        else:
            flash(f"Status atualizado para {requested_status}.", "success")
        return redirect(url_for("request_detail", request_id=request_id))

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("error.html", message="Seu perfil não possui permissão para esta ação."), 403

    @app.cli.command("init-db")
    def init_db_command():
        init_db()
        print("Banco inicializado.")

    return app


app = create_app()

if __name__ == "__main__":
    with app.app_context():
        app.init_db()
    app.run(debug=True)

