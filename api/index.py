from __future__ import annotations

import hashlib
import html
import os
import re
import secrets
import smtplib
import sqlite3
import unicodedata
import zipfile
from contextlib import contextmanager
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import requests
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS


APP_DIR = Path(__file__).resolve().parents[1]
DB_PATH = APP_DIR / "bahia.db"
STORAGE_DIR = APP_DIR / "storage"
OS_UPLOAD_DIR = STORAGE_DIR / "os"
DATABASE_URL = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
USE_POSTGRES = bool(DATABASE_URL)

NIVEIS = ["Básico", "Intermediário", "Avançado"]
AREAS_CURSO = ["CIMATEC", "SEBRAE"]
FORM_GERAL_PENDENTE = "Formulario geral pendente"
CADASTRO_INICIAL = "Cadastro inicial"
STATUS_FLUXO = [
    "Validação Administrativa",
    "Análise Técnica",
    "Agendamento",
    "Execução",
    "Finalizado",
    "Cancelado",
    "Reprovado",
]
EDITABLE_TABLES = {
    "cursos": "cursos",
    "perguntas_qualificacao": "perguntas_qualificacao",
    "perguntas_bpf": "perguntas_bpf",
    "perguntas_curso": "perguntas_curso",
    "alternativas_curso": "alternativas_curso",
    "owners_area": "owners_area",
    "entidades": "entidades",
    "usuarios": "usuarios",
}

app = Flask(__name__)
CORS(app)


def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def temporary_password(size: int = 10) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    return "".join(secrets.choice(alphabet) for _ in range(size))


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_") or "arquivo"


def docx_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return html.escape(text or "-", quote=False)


def docx_paragraph(text: Any, *, bold: bool = False, size: int = 22, align: str = "left", shade: str = "") -> str:
    bold_xml = "<w:b/>" if bold else ""
    jc_xml = f"<w:jc w:val=\"{align}\"/>" if align else ""
    shade_xml = f"<w:shd w:fill=\"{shade}\"/>" if shade else ""
    return (
        f"<w:p><w:pPr>{jc_xml}{shade_xml}<w:spacing w:after=\"120\"/></w:pPr><w:r><w:rPr>"
        f"{bold_xml}<w:sz w:val=\"{size}\"/></w:rPr><w:t>{docx_escape(text)}</w:t></w:r></w:p>"
    )


def docx_table(rows: list[list[Any]]) -> str:
    table_rows = []
    for row in rows:
        cells = []
        for cell_idx, cell in enumerate(row):
            fill = "EAF2FF" if cell_idx == 0 else "FFFFFF"
            cells.append(
                "<w:tc><w:tcPr><w:tcW w:w=\"5000\" w:type=\"dxa\"/>"
                f"<w:shd w:fill=\"{fill}\"/><w:tcMar><w:top w:w=\"90\" w:type=\"dxa\"/><w:left w:w=\"120\" w:type=\"dxa\"/><w:bottom w:w=\"90\" w:type=\"dxa\"/><w:right w:w=\"120\" w:type=\"dxa\"/></w:tcMar>"
                f"</w:tcPr>{docx_paragraph(cell, bold=cell_idx == 0, size=21)}</w:tc>"
            )
        table_rows.append(f"<w:tr>{''.join(cells)}</w:tr>")
    return (
        "<w:tbl><w:tblPr><w:tblW w:w=\"0\" w:type=\"auto\"/>"
        "<w:tblBorders><w:top w:val=\"single\" w:sz=\"4\" w:color=\"BFBFBF\"/>"
        "<w:left w:val=\"single\" w:sz=\"4\" w:color=\"BFBFBF\"/><w:bottom w:val=\"single\" w:sz=\"4\" w:color=\"BFBFBF\"/>"
        "<w:right w:val=\"single\" w:sz=\"4\" w:color=\"BFBFBF\"/><w:insideH w:val=\"single\" w:sz=\"4\" w:color=\"BFBFBF\"/>"
        "<w:insideV w:val=\"single\" w:sz=\"4\" w:color=\"BFBFBF\"/></w:tblBorders></w:tblPr>"
        f"{''.join(table_rows)}</w:tbl>"
    )


def docx_section(title: str) -> str:
    return docx_paragraph(title, bold=True, size=24, shade="D9EAF7")


def write_simple_docx(path: Path, body_xml: str):
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""
    document = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>{body_xml}<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="708" w:footer="708" w:gutter="0"/></w:sectPr></w:body>
</w:document>"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", content_types)
        docx.writestr("_rels/.rels", rels)
        docx.writestr("word/document.xml", document)


def normalize_sql(sql: str) -> str:
    if USE_POSTGRES:
        return sql.replace("?", "%s")
    return re.sub(r"\s+RETURNING\s+id\s*$", "", sql, flags=re.IGNORECASE)


@contextmanager
def db():
    if USE_POSTGRES:
        import psycopg
        from psycopg.rows import dict_row

        conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def fetch_all(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with db() as conn:
        cur = conn.execute(normalize_sql(sql), params)
        return [dict(row) for row in cur.fetchall()]


def fetch_one(sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: tuple[Any, ...] = ()) -> int | None:
    with db() as conn:
        cur = conn.execute(normalize_sql(sql), params)
        if USE_POSTGRES and sql.lstrip().lower().startswith("insert"):
            try:
                row = cur.fetchone()
                return row["id"] if row and "id" in row else None
            except Exception:
                return None
        return getattr(cur, "lastrowid", None)


def init_db():
    if USE_POSTGRES:
        return
    ddl = """
    CREATE TABLE IF NOT EXISTS usuarios (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      nome TEXT,
      usuario TEXT UNIQUE,
      senha_hash TEXT,
      perfil TEXT,
      email TEXT,
      ativo INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS entidades (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      entidade TEXT,
      cnpj TEXT,
      email_responsavel TEXT,
      telefone TEXT,
      endereco TEXT,
      territorio_identidade TEXT,
      municipio_entidade TEXT,
      certificacao TEXT,
      licenca_ambiental TEXT,
      atep TEXT,
      agente_negocio TEXT,
      numero_convenio TEXT,
      an_atep_ateg TEXT,
      nome_ateg TEXT,
      coordenador_tipo TEXT,
      nome_coordenador TEXT,
      natureza_juridica TEXT,
      dap_caf TEXT,
      tipologia_beneficiarios TEXT,
      comunidade_tradicional TEXT,
      ativa_dinamica TEXT,
      status_qualificacao TEXT DEFAULT 'Cadastro inicial',
      nivel TEXT,
      pontuacao INTEGER DEFAULT 0,
      pontuacao_q1 INTEGER DEFAULT 0,
      pontuacao_q2 INTEGER DEFAULT 0,
      data_cadastro TEXT,
      cadastrado_por TEXT,
      cadastrado_por_email TEXT,
      ativo INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS cursos (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      curso TEXT,
      area TEXT,
      nivel TEXT,
      descricao TEXT,
      carga_horaria TEXT,
      owner_email TEXT,
      estoque_total INTEGER DEFAULT 0,
      ativo INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS perguntas_qualificacao (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      questionario TEXT,
      ordem INTEGER,
      pergunta TEXT,
      opcao_1 TEXT,
      opcao_2 TEXT,
      opcao_3 TEXT,
      pontos_1 INTEGER DEFAULT 0,
      pontos_2 INTEGER DEFAULT 5,
      pontos_3 INTEGER DEFAULT 10,
      pontos_sim INTEGER DEFAULT 1,
      ativo INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS perguntas_bpf (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      secao TEXT,
      subsecao TEXT,
      codigo_pergunta TEXT,
      ordem INTEGER,
      pergunta TEXT,
      opcoes TEXT DEFAULT 'S;N;P;NA',
      pontos_sim INTEGER DEFAULT 1,
      ativo INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS perguntas_curso (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      curso_id INTEGER,
      ordem INTEGER,
      pergunta TEXT,
      pontos_sim INTEGER DEFAULT 1,
      ativo INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS alternativas_curso (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      pergunta_id INTEGER,
      ordem INTEGER,
      alternativa TEXT,
      pontos INTEGER DEFAULT 0,
      ativo INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS protocolos (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      protocolo TEXT UNIQUE,
      entidade_id INTEGER,
      curso_id INTEGER,
      area TEXT,
      pontuacao_curso INTEGER,
      status TEXT,
      etapa_atual TEXT,
      responsavel_atual TEXT,
      solicitante_nome TEXT,
      solicitante_email TEXT,
      data_abertura TEXT,
      data_atualizacao TEXT,
      data_agendada TEXT,
      observacao TEXT,
      ativo INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS respostas_entidade (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      entidade_id INTEGER,
      questionario TEXT,
      pergunta_id INTEGER,
      pergunta TEXT,
      resposta TEXT,
      pontuacao INTEGER,
      data_resposta TEXT
    );
    CREATE TABLE IF NOT EXISTS respostas_bpf (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      entidade_id INTEGER,
      pergunta_id INTEGER,
      pergunta TEXT,
      resposta TEXT,
      pontuacao INTEGER,
      data_resposta TEXT
    );
    CREATE TABLE IF NOT EXISTS respostas_curso (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      protocolo TEXT,
      pergunta_id INTEGER,
      pergunta TEXT,
      resposta TEXT,
      pontuacao INTEGER,
      data_resposta TEXT
    );
    CREATE TABLE IF NOT EXISTS owners_area (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      area TEXT,
      etapa TEXT,
      nome TEXT,
      email TEXT,
      usuario TEXT,
      ativo INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS historico_fluxo (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      protocolo TEXT,
      status_anterior TEXT,
      status_novo TEXT,
      usuario TEXT,
      data_movimento TEXT,
      observacao TEXT
    );
    CREATE TABLE IF NOT EXISTS notificacoes (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      protocolo TEXT,
      destinatario TEXT,
      assunto TEXT,
      corpo TEXT,
      enviado INTEGER DEFAULT 0,
      data_criacao TEXT,
      data_envio TEXT,
      erro TEXT
    );
    """
    if USE_POSTGRES:
        return
    with db() as conn:
        conn.executescript(ddl)
        protocol_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(protocolos)").fetchall()
        }
        for column, definition in {
            "os_modelo_nome": "TEXT",
            "os_modelo_path": "TEXT",
            "os_preenchida_nome": "TEXT",
            "os_preenchida_path": "TEXT",
            "os_preenchida_em": "TEXT",
            "os_preenchida_por": "TEXT",
        }.items():
            if column not in protocol_columns:
                conn.execute(f"ALTER TABLE protocolos ADD COLUMN {column} {definition}")
        user_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(usuarios)").fetchall()
        }
        for column, definition in {
            "senha_temporaria": "INTEGER DEFAULT 0",
            "trocar_senha_obrigatorio": "INTEGER DEFAULT 0",
            "acesso_pendente": "INTEGER DEFAULT 0",
            "data_solicitacao": "TEXT",
        }.items():
            if column not in user_columns:
                conn.execute(f"ALTER TABLE usuarios ADD COLUMN {column} {definition}")
        exists = conn.execute("SELECT COUNT(*) AS total FROM usuarios").fetchone()["total"]
        if not exists:
            conn.execute(
                "INSERT INTO usuarios(nome,usuario,senha_hash,perfil,email,ativo) VALUES(?,?,?,?,?,1)",
                ("Administrador", "admin", hash_pw("admin123"), "Administrador", ""),
            )


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in user.items() if k != "senha_hash"}


def bool_value(value: Any) -> bool:
    if isinstance(value, str):
        return value.lower() in {"1", "true", "sim", "yes"}
    return bool(value)


def text_key(value: Any) -> str:
    text = str(value or "").lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def stage_aliases(etapa: str = "", status: str = "") -> list[str]:
    aliases = {
        "validacao administrativa": [
            "Validacao Administrativa",
            "Validação Administrativa",
            "Administrativo",
            "Analista Administrativo",
        ],
        "analise tecnica": [
            "Analise Tecnica",
            "Análise Técnica",
            "Tecnico",
            "Técnico",
            "Analista Tecnico",
        ],
        "agendamento": ["Agendamento"],
        "execucao": ["Execucao", "Execução", "Executor"],
        "finalizado": ["Finalizado"],
        "cancelado": ["Cancelado"],
    }
    values = [etapa, status]
    values.extend(aliases.get(text_key(etapa or status), []))
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        clean = str(value or "").strip()
        if clean and clean not in seen:
            seen.add(clean)
            ordered.append(clean)
    return ordered


def role_emails_for_stage(status: str = "", etapa: str = "") -> list[str]:
    role_map = {
        "validacao administrativa": ["Analista Administrativo"],
        "analise tecnica": ["Analista Tecnico"],
        "agendamento": ["Agendamento"],
        "execucao": ["Execucao"],
    }
    roles = role_map.get(text_key(status or etapa), [])
    if not roles:
        return []
    rows = fetch_all(
        "SELECT email, usuario FROM usuarios WHERE ativo=1 AND COALESCE(acesso_pendente,0)=0 AND perfil IN ({})".format(
            ",".join("?" for _ in roles)
        ),
        tuple(roles),
    )
    return [row.get("email") or row.get("usuario") for row in rows]


def owner_emails_for_stage(area: str, etapa: str = "", status: str = "") -> list[str]:
    if not area:
        return []
    keys = {text_key(value) for value in stage_aliases(etapa, status)}
    rows = fetch_all("SELECT email, etapa FROM owners_area WHERE area=? AND ativo=1", (area,))
    return [row.get("email") for row in rows if text_key(row.get("etapa")) in keys]


def notification_recipients(area: str, etapa: str = "", solicitante_email: str = "", include_all_area: bool = False) -> list[str]:
    recipients = []
    if solicitante_email:
        recipients.append(solicitante_email)
    if include_all_area:
        recipients += [row.get("email") for row in fetch_all("SELECT email FROM owners_area WHERE area=? AND ativo=1", (area,))]
    elif etapa:
        owner_emails = owner_emails_for_stage(area, etapa, etapa)
        recipients += owner_emails if owner_emails else role_emails_for_stage(etapa, etapa)
    recipients += [row.get("email") for row in fetch_all("SELECT email FROM usuarios WHERE ativo=1 AND perfil IN ('Administrador','Moderador')")]
    return sorted({str(email).strip() for email in recipients if str(email or "").strip()})


def register_notification(protocolo: str, destinatario: str, assunto: str, corpo: str, enviado: bool = False, erro: str = ""):
    execute(
        "INSERT INTO notificacoes(protocolo,destinatario,assunto,corpo,enviado,data_criacao,data_envio,erro) VALUES(?,?,?,?,?,?,?,?)",
        (protocolo, destinatario, assunto, corpo, 1 if enviado else 0, now_str(), now_str() if enviado else None, erro),
    )


def try_send_email(destinatario: str, assunto: str, corpo: str) -> tuple[bool, str]:
    resend_key = os.getenv("RESEND_API_KEY", "").strip()
    resend_from = (os.getenv("MAIL_FROM") or os.getenv("RESEND_FROM_EMAIL") or "").strip()
    if resend_key and resend_from:
        try:
            response = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {resend_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": resend_from,
                    "to": [destinatario],
                    "subject": assunto,
                    "text": corpo,
                },
                timeout=20,
            )
            if response.ok:
                return True, ""
            try:
                details = response.json()
            except Exception:
                details = response.text
            return False, f"Resend: {details}"
        except Exception as exc:
            return False, f"Resend: {exc}"
    host = os.getenv("SMTP_HOST", "")
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")
    from_email = os.getenv("SMTP_FROM") or user
    if not host or not from_email:
        return False, "SMTP não configurado. Notificação ficou registrada no sistema."
    msg = EmailMessage()
    msg["From"] = from_email
    msg["To"] = destinatario
    msg["Subject"] = assunto
    msg.set_content(corpo)
    try:
        with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587"))) as server:
            if os.getenv("SMTP_TLS", "1") != "0":
                server.starttls()
            if user and password:
                server.login(user, password)
            server.send_message(msg)
        return True, ""
    except Exception as exc:
        return False, str(exc)


def notify_protocol(protocolo: str, area: str, etapa: str, status: str, solicitante_email: str = "", observacao: str = "", cancelled: bool = False):
    if cancelled:
        assunto = f"Protocolo {protocolo} cancelado"
        corpo = f"O protocolo {protocolo} foi cancelado.\n\nÁrea: {area or '-'}\nObservação: {observacao or '-'}"
        recipients = notification_recipients(area, solicitante_email=solicitante_email, include_all_area=True)
    else:
        assunto = f"Nova demanda para {status} - {protocolo}"
        corpo = f"Existe uma nova demanda aguardando atuação.\n\nProtocolo: {protocolo}\nÁrea: {area or '-'}\nEtapa: {etapa or '-'}\nStatus: {status or '-'}\n\nObservação: {observacao or '-'}"
        recipients = notification_recipients(area, etapa=etapa, solicitante_email=solicitante_email)
    for destinatario in recipients:
        ok, erro = try_send_email(destinatario, assunto, corpo)
        register_notification(protocolo, destinatario, assunto, corpo, ok, erro)


def allowed_levels(nivel: str) -> list[str]:
    return {
        "Básico": ["Básico"],
        "Intermediário": ["Básico", "Intermediário"],
        "Avançado": ["Básico", "Intermediário", "Avançado"],
    }.get(nivel, ["Básico"])


def next_step(status: str) -> tuple[str, str]:
    return {
        "Validação Administrativa": ("Análise Técnica", "Técnico"),
        "Análise Técnica": ("Agendamento", "Agendamento"),
        "Agendamento": ("Execução", "Executor"),
        "Execução": ("Finalizado", "Finalizado"),
    }.get(status, (status, ""))


def generate_filled_os(protocolo: str, usuario: str, observacao: str = "") -> tuple[str, str] | tuple[None, None]:
    row = fetch_one(
        """SELECT p.*, e.entidade, e.cnpj, e.email_responsavel, e.municipio_entidade,
                  e.territorio_identidade, e.endereco, e.telefone, c.curso
           FROM protocolos p
           LEFT JOIN entidades e ON e.id=p.entidade_id
           LEFT JOIN cursos c ON c.id=p.curso_id
           WHERE p.protocolo=? LIMIT 1""",
        (protocolo,),
    )
    if not row:
        return None, None
    numero_os = f"OS-{datetime.now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(2).upper()}"
    data_br = datetime.now().strftime("%d/%m/%Y")
    filename = f"{slug(protocolo)}_{numero_os}.docx"
    destino = OS_UPLOAD_DIR / filename
    body = [
        docx_paragraph("ORDEM DE SERVIÇO", bold=True, size=32, align="center"),
        docx_paragraph("Governança e Qualificação de Demandas - Bahia", bold=True, size=22, align="center"),
        docx_section("1. IDENTIFICAÇÃO DA ORDEM DE SERVIÇO"),
        docx_table([
            [f"Número da OS: {numero_os}", f"Data de Abertura: {data_br}"],
            ["Status: ( ) Aberta  ( ) Aprovada  ( X ) Agendamento  ( ) Em Execução  ( ) Concluída  ( ) Cancelada", ""],
            [f"Origem da Demanda: {row.get('entidade') or '-'}", f"Número do Protocolo da Demanda: {protocolo}"],
        ]),
        docx_section("2. DADOS DA ORGANIZAÇÃO PRODUTIVA"),
        docx_table([
            [f"Nome da Organização: {row.get('entidade') or '-'}", f"CNPJ/CPF: {row.get('cnpj') or '-'}"],
            [f"Município: {row.get('municipio_entidade') or '-'}", f"Território: {row.get('territorio_identidade') or '-'}"],
            [f"Responsável Local: {row.get('email_responsavel') or '-'}", f"E-mail: {row.get('email_responsavel') or '-'}"],
            [f"Endereço: {row.get('endereco') or '-'}", f"Telefone/WhatsApp: {row.get('telefone') or '-'}"],
        ]),
        docx_section("3. SOLICITANTE DA DEMANDA"),
        docx_table([
            [f"Nome do Coordenador/Demandante: {row.get('solicitante_nome') or usuario or '-'}", "Função: Analista Técnico"],
            [f"Contato: {row.get('solicitante_email') or usuario or '-'}", f"Data da Solicitação: {data_br}"],
        ]),
        docx_section("4. DADOS DA DEMANDA"),
        docx_table([
            [f"Curso/Solução: {row.get('curso') or '-'}", f"Área: {row.get('area') or '-'}"],
            [f"Observação da análise técnica: {observacao or '-'}", ""],
        ]),
    ]
    write_simple_docx(destino, "".join(body))
    data = now_str()
    execute(
        """UPDATE protocolos
           SET os_preenchida_nome=?, os_preenchida_path=?, os_preenchida_em=?, os_preenchida_por=?
           WHERE protocolo=?""",
        (filename, str(destino), data, usuario, protocolo),
    )
    return str(destino), filename


@app.get("/api/health")
def health():
    init_db()
    return jsonify({"ok": True, "backend": "postgres" if USE_POSTGRES else "sqlite"})


@app.post("/api/login")
def login():
    init_db()
    data = request.get_json(force=True)
    login_value = (data.get("usuario") or "").strip().lower()
    password = data.get("senha") or ""
    user = fetch_one(
        "SELECT * FROM usuarios WHERE ativo=1 AND (LOWER(usuario)=? OR LOWER(email)=?) LIMIT 1",
        (login_value, login_value),
    )
    if not user or user.get("senha_hash") != hash_pw(password):
        return jsonify({"error": "Usuário ou senha inválidos."}), 401
    return jsonify({"user": public_user(user)})


@app.post("/api/register")
def register_user():
    init_db()
    data = request.get_json(force=True)
    email = (data.get("email") or "").strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return jsonify({"error": "Informe um e-mail válido."}), 400
    existing = fetch_one("SELECT * FROM usuarios WHERE LOWER(email)=? OR LOWER(usuario)=? LIMIT 1", (email, email))
    temp = temporary_password()
    data_solicitacao = now_str()
    if existing:
        if not existing.get("ativo"):
            return jsonify({"error": "Este usuário está inativo. Procure um administrador."}), 400
        execute(
            """UPDATE usuarios
               SET senha_hash=?, senha_temporaria=1, trocar_senha_obrigatorio=1,
                   acesso_pendente=1, perfil=NULL, data_solicitacao=?, email=?, usuario=?, ativo=1
               WHERE id=?""",
            (hash_pw(temp), data_solicitacao, email, email, existing["id"]),
        )
        user_id = existing["id"]
    else:
        user_id = execute(
            """INSERT INTO usuarios(nome,usuario,email,senha_hash,perfil,senha_temporaria,
                      trocar_senha_obrigatorio,acesso_pendente,data_solicitacao,ativo)
               VALUES(?,?,?,?,?,?,?,?,?,1) RETURNING id""",
            (email, email, email, hash_pw(temp), None, 1, 1, 1, data_solicitacao),
        )
    assunto = "Senha temporária - Sistema Bahia"
    corpo = f"Olá.\n\nCriamos um acesso temporário para o Sistema Bahia.\n\nE-mail: {email}\nSenha temporária: {temp}\n\nAo entrar, defina uma nova senha."
    ok, erro = try_send_email(email, assunto, corpo)
    register_notification(f"ACESSO-{email}", email, assunto, corpo, ok, erro)
    mod_subject = "Novo usuário aguardando qualificação - Sistema Bahia"
    mod_body = f"Um novo usuário criou acesso e aguarda qualificação de atividade.\n\nE-mail: {email}\nID: {user_id}\nData: {data_solicitacao}"
    for row in fetch_all("SELECT email FROM usuarios WHERE ativo=1 AND perfil IN ('Administrador','Moderador') AND email IS NOT NULL AND email<>''"):
        destinatario = row.get("email")
        ok, erro = try_send_email(destinatario, mod_subject, mod_body)
        register_notification(f"ACESSO-{user_id}", destinatario, mod_subject, mod_body, ok, erro)
    return jsonify({"message": "Usuário criado. Enviamos uma senha temporária para o e-mail informado."})


@app.post("/api/change-password")
def change_password():
    init_db()
    data = request.get_json(force=True)
    user_id = data.get("user_id")
    password = data.get("senha") or ""
    if len(password) < 6:
        return jsonify({"error": "A nova senha deve ter pelo menos 6 caracteres."}), 400
    user = fetch_one("SELECT * FROM usuarios WHERE id=? AND ativo=1 LIMIT 1", (user_id,))
    if not user:
        return jsonify({"error": "Usuário não encontrado."}), 404
    execute(
        "UPDATE usuarios SET senha_hash=?, senha_temporaria=0, trocar_senha_obrigatorio=0 WHERE id=?",
        (hash_pw(password), user_id),
    )
    updated = fetch_one("SELECT * FROM usuarios WHERE id=? LIMIT 1", (user_id,))
    return jsonify({"message": "Senha definida com sucesso.", "user": public_user(updated)})


@app.get("/api/dashboard")
def dashboard():
    init_db()
    entidades = fetch_all("SELECT * FROM entidades WHERE ativo=1")
    cursos = fetch_all("SELECT * FROM cursos WHERE ativo=1")
    protocolos = fetch_all("SELECT * FROM protocolos")
    andamento = [p for p in protocolos if p.get("status") not in {"Finalizado", "Cancelado", "Reprovado"}]
    return jsonify(
        {
            "cards": {
                "entidades": len(entidades),
                "qualificadas": len([e for e in entidades if e.get("status_qualificacao") == "Concluída"]),
                "formGeralPendentes": len([e for e in entidades if e.get("status_qualificacao") == FORM_GERAL_PENDENTE]),
                "bpfPendentes": len([e for e in entidades if e.get("status_qualificacao") == "BPF pendente"]),
                "cursos": len(cursos),
                "fluxos": len(andamento),
            },
            "protocolos": protocolos[-20:],
            "entidadesPorNivel": entidades,
            "cursosPorArea": cursos,
        }
    )


@app.get("/api/entities")
def entities():
    init_db()
    rows = fetch_all("SELECT * FROM entidades WHERE ativo=1 ORDER BY id DESC")
    return jsonify({"items": rows})


@app.post("/api/entities")
def create_entity():
    init_db()
    data = request.get_json(force=True)
    nome = (data.get("entidade") or "").strip()
    cnpj = (data.get("cnpj") or "").strip()
    if not nome:
        return jsonify({"error": "Informe o nome da entidade."}), 400
    if not cnpj:
        return jsonify({"error": "Informe o CNPJ da entidade."}), 400
    row_id = execute(
        """INSERT INTO entidades(entidade,cnpj,status_qualificacao,data_cadastro,cadastrado_por,cadastrado_por_email,ativo)
           VALUES(?,?,?,?,?,?,?) RETURNING id""",
        (nome, cnpj, CADASTRO_INICIAL, now_str(), data.get("usuario", "admin"), data.get("email", ""), True),
    )
    return jsonify({"id": row_id, "message": "Entidade cadastrada."})


@app.get("/api/qualification/start-options")
def qualification_start_options():
    init_db()
    rows = fetch_all(
        """SELECT * FROM entidades
           WHERE ativo=1 AND COALESCE(status_qualificacao,'') NOT IN (?, ?)
           ORDER BY entidade""",
        (FORM_GERAL_PENDENTE, "BPF pendente"),
    )
    return jsonify({"items": rows})


@app.post("/api/qualification/cadastro")
def save_cadastro():
    init_db()
    data = request.get_json(force=True)
    entidade_id = data.get("id")
    fields = data.get("fields", {})
    execute(
        """UPDATE entidades
           SET cnpj=?, email_responsavel=?, telefone=?, endereco=?, territorio_identidade=?,
               municipio_entidade=?, certificacao=?, licenca_ambiental=?, numero_convenio=?,
               an_atep_ateg=?, agente_negocio=?, atep=?, nome_ateg=?, coordenador_tipo=?,
               nome_coordenador=?, natureza_juridica=?, dap_caf=?, tipologia_beneficiarios=?,
               comunidade_tradicional=?, ativa_dinamica=?, status_qualificacao=?
           WHERE id=?""",
        (
            fields.get("cnpj"),
            fields.get("email_responsavel"),
            fields.get("telefone"),
            fields.get("endereco"),
            fields.get("territorio_identidade"),
            fields.get("municipio_entidade"),
            fields.get("certificacao"),
            fields.get("licenca_ambiental"),
            fields.get("numero_convenio"),
            fields.get("an_atep_ateg"),
            fields.get("agente_negocio"),
            fields.get("atep"),
            fields.get("nome_ateg"),
            fields.get("coordenador_tipo"),
            fields.get("nome_coordenador"),
            fields.get("natureza_juridica"),
            fields.get("dap_caf"),
            fields.get("tipologia_beneficiarios"),
            fields.get("comunidade_tradicional"),
            fields.get("ativa_dinamica"),
            FORM_GERAL_PENDENTE,
            entidade_id,
        ),
    )
    return jsonify({"message": "Dados cadastrais salvos."})


@app.get("/api/questions/<kind>")
def questions(kind: str):
    init_db()
    if kind == "geral":
        rows = fetch_all("SELECT * FROM perguntas_qualificacao WHERE ativo=1 ORDER BY questionario, ordem")
    elif kind == "bpf":
        rows = fetch_all("SELECT * FROM perguntas_bpf WHERE ativo=1 ORDER BY secao, subsecao, ordem")
    else:
        return jsonify({"error": "Tipo inválido."}), 404
    return jsonify({"items": rows})


@app.get("/api/qualification/pending/<kind>")
def qualification_pending(kind: str):
    init_db()
    status = FORM_GERAL_PENDENTE if kind == "geral" else "BPF pendente"
    rows = fetch_all("SELECT * FROM entidades WHERE ativo=1 AND status_qualificacao=? ORDER BY id DESC", (status,))
    return jsonify({"items": rows})


@app.post("/api/qualification/general")
def save_general():
    init_db()
    data = request.get_json(force=True)
    entidade_id = int(data["entidade_id"])
    respostas = data.get("respostas", [])
    pontos = sum(int(r.get("pontuacao") or 0) for r in respostas)
    nivel = "Básico" if pontos <= 20 else "Intermediário" if pontos <= 35 else "Avançado"
    data_resposta = now_str()
    with db() as conn:
        conn.execute(normalize_sql("DELETE FROM respostas_entidade WHERE entidade_id=?"), (entidade_id,))
        for r in respostas:
            conn.execute(
                normalize_sql(
                    """INSERT INTO respostas_entidade(entidade_id,questionario,pergunta_id,pergunta,resposta,pontuacao,data_resposta)
                       VALUES(?,?,?,?,?,?,?)"""
                ),
                (
                    entidade_id,
                    r.get("questionario"),
                    r.get("pergunta_id"),
                    r.get("pergunta"),
                    r.get("resposta"),
                    r.get("pontuacao"),
                    data_resposta,
                ),
            )
        conn.execute(
            normalize_sql(
                "UPDATE entidades SET status_qualificacao='BPF pendente', nivel=?, pontuacao=?, pontuacao_q1=? WHERE id=?"
            ),
            (nivel, pontos, pontos, entidade_id),
        )
    return jsonify({"message": "Formulário Geral salvo.", "nivel": nivel, "pontuacao": pontos})


@app.post("/api/qualification/bpf")
def save_bpf():
    init_db()
    data = request.get_json(force=True)
    entidade_id = int(data["entidade_id"])
    respostas = data.get("respostas", [])
    pontos = sum(int(r.get("pontuacao") or 0) for r in respostas)
    data_resposta = now_str()
    with db() as conn:
        conn.execute(normalize_sql("DELETE FROM respostas_bpf WHERE entidade_id=?"), (entidade_id,))
        for r in respostas:
            conn.execute(
                normalize_sql(
                    "INSERT INTO respostas_bpf(entidade_id,pergunta_id,pergunta,resposta,pontuacao,data_resposta) VALUES(?,?,?,?,?,?)"
                ),
                (entidade_id, r.get("pergunta_id"), r.get("pergunta"), r.get("resposta"), r.get("pontuacao"), data_resposta),
            )
        conn.execute(
            normalize_sql("UPDATE entidades SET status_qualificacao='Concluída', pontuacao=COALESCE(pontuacao,0)+? WHERE id=?"),
            (pontos, entidade_id),
        )
    return jsonify({"message": "BPF salvo. Entidade liberada para cursos."})


@app.get("/api/courses")
def courses():
    init_db()
    rows = fetch_all("SELECT * FROM cursos WHERE ativo=1 ORDER BY area,nivel,curso")
    return jsonify({"items": rows})


@app.get("/api/courses/<int:course_id>/questions")
def course_questions(course_id: int):
    init_db()
    questions = fetch_all("SELECT * FROM perguntas_curso WHERE curso_id=? AND ativo=1 ORDER BY ordem", (course_id,))
    alternatives = fetch_all(
        """SELECT a.*
           FROM alternativas_curso a
           JOIN perguntas_curso p ON p.id=a.pergunta_id
           WHERE p.curso_id=? AND a.ativo=1
           ORDER BY a.pergunta_id, a.ordem""",
        (course_id,),
    )
    alternatives_by_question: dict[Any, list[dict[str, Any]]] = {}
    for alternative in alternatives:
        alternatives_by_question.setdefault(alternative.get("pergunta_id"), []).append(alternative)
    for question in questions:
        question["alternativas"] = alternatives_by_question.get(question.get("id"), [])
    return jsonify({"items": questions})


@app.get("/api/protocols")
def protocols():
    init_db()
    rows = fetch_all(
        """SELECT p.*, e.entidade, e.nivel AS nivel_entidade, c.curso
           FROM protocolos p
           LEFT JOIN entidades e ON e.id=p.entidade_id
           LEFT JOIN cursos c ON c.id=p.curso_id
           ORDER BY p.id DESC"""
    )
    return jsonify({"items": rows, "status": STATUS_FLUXO})


@app.post("/api/protocols")
def create_protocol():
    init_db()
    data = request.get_json(force=True)
    protocolo = f"BA-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    data_mov = now_str()
    respostas = data.get("respostas", [])
    pontuacao_curso = data.get("pontuacao_curso", sum(int(r.get("pontuacao") or 0) for r in respostas))
    execute(
        """INSERT INTO protocolos(protocolo,entidade_id,curso_id,area,pontuacao_curso,status,etapa_atual,responsavel_atual,
                  solicitante_nome,solicitante_email,data_abertura,data_atualizacao,observacao)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) RETURNING id""",
        (
            protocolo,
            data.get("entidade_id"),
            data.get("curso_id"),
            data.get("area"),
            pontuacao_curso,
            "Validação Administrativa",
            "Administrativo",
            "Administrativo",
            data.get("solicitante_nome", ""),
            data.get("solicitante_email", ""),
            data_mov,
            data_mov,
            data.get("observacao", ""),
        ),
    )
    execute(
        "INSERT INTO historico_fluxo(protocolo,status_anterior,status_novo,usuario,data_movimento,observacao) VALUES(?,?,?,?,?,?)",
        (protocolo, "", "Validação Administrativa", data.get("usuario", "admin"), data_mov, data.get("observacao", "")),
    )
    notify_protocol(
        protocolo,
        data.get("area", ""),
        "Administrativo",
        "Validação Administrativa",
        data.get("solicitante_email", ""),
        data.get("observacao", ""),
    )
    with db() as conn:
        for r in respostas:
            conn.execute(
                normalize_sql(
                    "INSERT INTO respostas_curso(protocolo,pergunta_id,pergunta,resposta,pontuacao,data_resposta) VALUES(?,?,?,?,?,?)"
                ),
                (
                    protocolo,
                    r.get("pergunta_id"),
                    r.get("pergunta"),
                    r.get("resposta"),
                    r.get("pontuacao", 0),
                    data_mov,
                ),
            )
    return jsonify({"message": "Protocolo criado.", "protocolo": protocolo})


@app.post("/api/protocols/<protocolo>/advance")
def advance_protocol(protocolo: str):
    init_db()
    data = request.get_json(force=True)
    row = fetch_one("SELECT * FROM protocolos WHERE protocolo=? LIMIT 1", (protocolo,))
    if not row:
        return jsonify({"error": "Protocolo não encontrado."}), 404
    novo_status, nova_etapa = next_step(row.get("status"))
    data_mov = now_str()
    if text_key(row.get("status")) == "agendamento":
        execute(
            "UPDATE protocolos SET status=?, etapa_atual=?, responsavel_atual=?, data_atualizacao=?, data_agendada=? WHERE protocolo=?",
            (novo_status, nova_etapa, nova_etapa, data_mov, data.get("data_agendada"), protocolo),
        )
    else:
        execute(
            "UPDATE protocolos SET status=?, etapa_atual=?, responsavel_atual=?, data_atualizacao=? WHERE protocolo=?",
            (novo_status, nova_etapa, nova_etapa, data_mov, protocolo),
        )
    if text_key(row.get("status")) in {"analise tecnica", "analise t cnica"} and text_key(novo_status) == "agendamento":
        generate_filled_os(protocolo, data.get("usuario", "admin"), data.get("observacao", ""))
    execute(
        "INSERT INTO historico_fluxo(protocolo,status_anterior,status_novo,usuario,data_movimento,observacao) VALUES(?,?,?,?,?,?)",
        (protocolo, row.get("status"), novo_status, data.get("usuario", "admin"), data_mov, data.get("observacao", "")),
    )
    notify_protocol(
        protocolo,
        row.get("area", ""),
        nova_etapa,
        novo_status,
        row.get("solicitante_email", ""),
        data.get("observacao", ""),
    )
    return jsonify({"message": "Fluxo atualizado.", "status": novo_status})


@app.post("/api/protocols/<protocolo>/cancel")
def cancel_protocol(protocolo: str):
    init_db()
    data = request.get_json(force=True)
    row = fetch_one("SELECT * FROM protocolos WHERE protocolo=? LIMIT 1", (protocolo,))
    if not row:
        return jsonify({"error": "Protocolo não encontrado."}), 404
    if text_key(row.get("status")) in {"cancelado", "reprovado", "finalizado"}:
        return jsonify({"error": "Este protocolo já está encerrado."}), 400
    data_mov = now_str()
    execute(
        "UPDATE protocolos SET status='Cancelado', etapa_atual='Cancelado', responsavel_atual='Cancelado', data_atualizacao=? WHERE protocolo=?",
        (data_mov, protocolo),
    )
    execute(
        "INSERT INTO historico_fluxo(protocolo,status_anterior,status_novo,usuario,data_movimento,observacao) VALUES(?,?,?,?,?,?)",
        (protocolo, row.get("status"), "Cancelado", data.get("usuario", "admin"), data_mov, data.get("observacao", "")),
    )
    notify_protocol(
        protocolo,
        row.get("area", ""),
        "Cancelado",
        "Cancelado",
        row.get("solicitante_email", ""),
        data.get("observacao", ""),
        cancelled=True,
    )
    return jsonify({"message": "Protocolo cancelado.", "status": "Cancelado"})


@app.get("/api/protocols/<protocolo>/os")
def download_os(protocolo: str):
    init_db()
    row = fetch_one("SELECT status, os_preenchida_nome, os_preenchida_path FROM protocolos WHERE protocolo=? LIMIT 1", (protocolo,))
    if not row or not row.get("os_preenchida_path"):
        if row and text_key(row.get("status")) in {"agendamento", "execucao", "finalizado"}:
            generate_filled_os(protocolo, "admin", "")
            row = fetch_one("SELECT status, os_preenchida_nome, os_preenchida_path FROM protocolos WHERE protocolo=? LIMIT 1", (protocolo,))
        else:
            return jsonify({"error": "OS ainda não foi gerada."}), 404
    path = Path(row["os_preenchida_path"])
    if not path.exists():
        return jsonify({"error": "Arquivo da OS não encontrado."}), 404
    return send_file(path, as_attachment=True, download_name=row.get("os_preenchida_nome") or path.name)


@app.get("/api/forms/<protocolo>")
def protocol_forms(protocolo: str):
    init_db()
    prot = fetch_one("SELECT * FROM protocolos WHERE protocolo=? LIMIT 1", (protocolo,))
    if not prot:
        return jsonify({"error": "Protocolo não encontrado."}), 404
    entidade_id = prot.get("entidade_id")
    return jsonify(
        {
            "geral": fetch_all("SELECT * FROM respostas_entidade WHERE entidade_id=? ORDER BY id", (entidade_id,)),
            "bpf": fetch_all("SELECT * FROM respostas_bpf WHERE entidade_id=? ORDER BY id", (entidade_id,)),
            "curso": fetch_all("SELECT * FROM respostas_curso WHERE protocolo=? ORDER BY id", (protocolo,)),
            "historico": fetch_all("SELECT * FROM historico_fluxo WHERE protocolo=? ORDER BY id", (protocolo,)),
        }
    )


@app.get("/api/admin/table/<table>")
def get_table(table: str):
    init_db()
    if table not in EDITABLE_TABLES:
        return jsonify({"error": "Tabela não permitida."}), 404
    rows = fetch_all(f"SELECT * FROM {EDITABLE_TABLES[table]} ORDER BY id DESC")
    return jsonify({"items": rows})


@app.post("/api/admin/table/<table>")
def save_table(table: str):
    init_db()
    if table not in EDITABLE_TABLES:
        return jsonify({"error": "Tabela não permitida."}), 404
    real_table = EDITABLE_TABLES[table]
    data = request.get_json(force=True)
    rows = data.get("rows", [])
    existing_rows = fetch_all(f"SELECT * FROM {real_table}")
    existing_ids = {row["id"] for row in existing_rows if row.get("id")}
    incoming_ids = {row.get("id") for row in rows if row.get("id")}
    removed_ids = [row_id for row_id in existing_ids if row_id not in incoming_ids]
    for row_id in removed_ids:
        execute(f"DELETE FROM {real_table} WHERE id=?", (row_id,))

    if table == "usuarios":
        existing_by_id = {row["id"]: row for row in existing_rows if row.get("id")}
        allowed_roles = {
            "Administrador",
            "Moderador",
            "Analista Administrativo",
            "Analista Tecnico",
            "Agendamento",
            "Execucao",
        }
        seen_login_keys: set[str] = set()
        for row in rows:
            temp_password = row.get("generated_temp_password")
            clean = {k: v for k, v in row.items() if k not in {"_deleted", "generated_temp_password"}}
            row_id = clean.get("id")
            login_value = str(clean.get("email") or clean.get("usuario") or "").strip().lower()
            nome = str(clean.get("nome") or "").strip()
            if not login_value and not nome:
                continue
            if not login_value:
                return jsonify({"error": "Informe o e-mail do usuario antes de salvar."}), 400
            if login_value in seen_login_keys and not row_id:
                return jsonify({"error": f"E-mail/usuario duplicado na tabela: {login_value}"}), 400
            seen_login_keys.add(login_value)

            previous = existing_by_id.get(row_id) if row_id else None
            senha_hash = clean.get("senha_hash") or (previous.get("senha_hash") if previous else None)
            acesso_pendente = bool_value(clean.get("acesso_pendente"))
            ativo = bool_value(clean.get("ativo", True))
            perfil = clean.get("perfil") or None
            if perfil and perfil not in allowed_roles:
                return jsonify({"error": f"Cargo invalido para o usuario {login_value}: {perfil}"}), 400
            if not perfil:
                acesso_pendente = True
            if not senha_hash:
                return jsonify({"error": f"Gere a senha temporaria do usuario {login_value} antes de salvar."}), 400

            duplicate = fetch_one(
                "SELECT id FROM usuarios WHERE (LOWER(email)=? OR LOWER(usuario)=?) AND id<>COALESCE(?, -1) LIMIT 1",
                (login_value, login_value, row_id),
            )
            if duplicate:
                return jsonify({"error": f"Ja existe um usuario cadastrado com o login {login_value}."}), 400

            payload = {
                "nome": nome or login_value,
                "usuario": login_value,
                "email": login_value,
                "senha_hash": senha_hash,
                "perfil": perfil,
                "senha_temporaria": bool_value(clean.get("senha_temporaria")),
                "trocar_senha_obrigatorio": bool_value(clean.get("trocar_senha_obrigatorio")),
                "acesso_pendente": acesso_pendente,
                "data_solicitacao": clean.get("data_solicitacao") or (previous.get("data_solicitacao") if previous else now_str()),
                "ativo": ativo,
            }
            cols = list(payload.keys())
            if row_id:
                set_clause = ", ".join(f"{c}=?" for c in cols)
                execute(f"UPDATE usuarios SET {set_clause} WHERE id=?", tuple(payload[c] for c in cols) + (row_id,))
                if temp_password:
                    assunto = "Senha temporaria - Sistema Bahia"
                    corpo = (
                        "Ola.\n\n"
                        "Sua senha temporaria do Sistema Bahia foi redefinida.\n\n"
                        f"E-mail: {login_value}\n"
                        f"Senha temporaria: {temp_password}\n\n"
                        "Ao entrar, defina uma nova senha."
                    )
                    ok, erro = try_send_email(login_value, assunto, corpo)
                    register_notification(f"ACESSO-{login_value}", login_value, assunto, corpo, ok, erro)
                if previous and (bool_value(previous.get("acesso_pendente")) or not previous.get("perfil")) and not acesso_pendente and perfil:
                    assunto = "Acesso liberado - Sistema Bahia"
                    corpo = (
                        "Seu acesso ao Sistema Bahia foi liberado.\n\n"
                        f"Cargo: {perfil}\n"
                        f"Usuario: {login_value}\n\n"
                        "Entre com sua senha para continuar."
                    )
                    ok, erro = try_send_email(login_value, assunto, corpo)
                    register_notification(f"ACESSO-{login_value}", login_value, assunto, corpo, ok, erro)
            else:
                placeholders = ", ".join("?" for _ in cols)
                execute(f"INSERT INTO usuarios({', '.join(cols)}) VALUES({placeholders})", tuple(payload[c] for c in cols))
                if temp_password:
                    assunto = "Senha temporaria - Sistema Bahia"
                    corpo = (
                        "Ola.\n\n"
                        "Criamos um acesso para o Sistema Bahia.\n\n"
                        f"E-mail: {login_value}\n"
                        f"Senha temporaria: {temp_password}\n\n"
                        "Ao entrar, defina uma nova senha."
                    )
                    ok, erro = try_send_email(login_value, assunto, corpo)
                    register_notification(f"ACESSO-{login_value}", login_value, assunto, corpo, ok, erro)
        return jsonify({"message": "Tabela salva."})

    for row in rows:
        row = {k: v for k, v in row.items() if k != "_deleted"}
        row_id = row.get("id")
        cols = [k for k in row.keys() if k != "id"]
        if row_id:
            set_clause = ", ".join(f"{c}=?" for c in cols)
            execute(f"UPDATE {real_table} SET {set_clause} WHERE id=?", tuple(row[c] for c in cols) + (row_id,))
        elif any(v not in (None, "") for v in row.values()):
            placeholders = ", ".join("?" for _ in cols)
            execute(f"INSERT INTO {real_table}({', '.join(cols)}) VALUES({placeholders})", tuple(row[c] for c in cols))
    return jsonify({"message": "Tabela salva."})


init_db()
