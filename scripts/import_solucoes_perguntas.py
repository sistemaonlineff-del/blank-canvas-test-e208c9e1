from __future__ import annotations

import argparse
import os
import re
import sqlite3
import unicodedata
from pathlib import Path

import pandas as pd


DEFAULT_XLSX = Path(r"C:\Users\fabio\Downloads\Base_Soluções_Perguntas.xlsx")
DEFAULT_CURSOS_XLSX = Path(r"C:\Users\fabio\Downloads\bahia\BASE_CURSOS.xlsx")
DEFAULT_AVALIACAO_XLSX = Path(r"C:\Users\fabio\Downloads\Base_Perguntas_Avaliacao.xlsx")
DEFAULT_BPF_XLSX = Path(r"C:\Users\fabio\Downloads\bahia\Perguntas_BPF_Formatado.xlsx")
DEFAULT_SQLITE = Path("bahia.db")
NIVEL_PADRAO = "Básico"
ESTOQUE_PADRAO = 10


def txt(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def normalized_name(value) -> str:
    value = txt(value)
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"\s+", " ", value).strip().lower()
    return value


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized.columns = [
        str(c)
        .strip()
        .upper()
        .replace("Ç", "C")
        .replace("Ã", "A")
        .replace("Í", "I")
        .replace("É", "E")
        .replace("Ê", "E")
        .replace("Á", "A")
        .replace("Ó", "O")
        for c in normalized.columns
    ]
    return normalized


def nivel_minimo(value) -> str:
    raw = txt(value).lower()
    if not raw or "inicial" in raw or "basico" in raw or "básico" in raw:
        return "Básico"
    if "intermedi" in raw:
        return "Intermediário"
    if "avanc" in raw or "avanç" in raw:
        return "Avançado"
    return "Básico"


def int_or_zero(value) -> int:
    if pd.isna(value) or value == "":
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def read_base_cursos(path: Path) -> pd.DataFrame:
    sheets = pd.read_excel(path, sheet_name=None)
    sheet = sheets["CURSOS"] if "CURSOS" in sheets else next(iter(sheets.values()))
    df = normalize_columns(sheet).fillna("")
    required = {"CURSO", "NIVEL", "QUANTIDADE"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"BASE_CURSOS sem colunas obrigatórias: {', '.join(sorted(missing))}")
    if "DESCRICAO" not in df.columns:
        desc_cols = [c for c in df.columns if c.startswith("DESCRI")]
        df["DESCRICAO"] = df[desc_cols[0]] if desc_cols else ""
    if "AREA" not in df.columns:
        df["AREA"] = ""
    return df


def read_base_avaliacao(path: Path) -> pd.DataFrame:
    sheets = pd.read_excel(path, sheet_name=None)
    sheet = sheets["Perguntas"] if "Perguntas" in sheets else next(iter(sheets.values()))
    df = normalize_columns(sheet).fillna("")
    rename = {
        "OPCAO 1": "OPCAO_1",
        "OPCAO 2": "OPCAO_2",
        "OPCAO 3": "OPCAO_3",
    }
    df = df.rename(columns=rename)
    required = {"ID", "BLOCO", "ORDEM", "PERGUNTA", "TIPO", "OPCAO_1", "OPCAO_2", "OPCAO_3"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Base_Perguntas_Avaliacao sem colunas obrigatórias: {', '.join(sorted(missing))}")
    return df


def read_base_bpf(path: Path) -> pd.DataFrame:
    sheets = pd.read_excel(path, sheet_name=None)
    sheet = sheets["Perguntas"] if "Perguntas" in sheets else next(iter(sheets.values()))
    df = normalize_columns(sheet).fillna("")
    required = {"ORDEM", "SECAO", "SUBSECAO", "CODIGOPERGUNTA", "PERGUNTA", "TIPORESPOSTA", "OPCOES"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Perguntas_BPF_Formatado sem colunas obrigatórias: {', '.join(sorted(missing))}")
    return df


def infer_area_sqlite(cur: sqlite3.Cursor, curso: str, fallback: str) -> str:
    if fallback:
        return fallback.upper()
    row = cur.execute(
        "SELECT area FROM cursos WHERE curso=? AND area IS NOT NULL AND area<>'' ORDER BY id DESC LIMIT 1",
        (curso,),
    ).fetchone()
    return row[0].upper() if row and row[0] else "SEBRAE"


def find_course_sqlite(cur: sqlite3.Cursor, curso: str):
    target = normalized_name(curso)
    rows = cur.execute("SELECT id, curso, id_questionario FROM cursos ORDER BY id").fetchall()
    matches = [row for row in rows if normalized_name(row[1]) == target]
    if not matches:
        return None
    with_questionario = [row for row in matches if row[2]]
    return with_questionario[0] if with_questionario else matches[0]


def import_cursos_sqlite(db_path: Path, xlsx_path: Path) -> None:
    cursos = read_base_cursos(xlsx_path)
    conn = sqlite3.connect(db_path)
    ensure_sqlite_schema(conn)
    cur = conn.cursor()
    atualizados = criados = 0
    for _, row in cursos.iterrows():
        nome = txt(row["CURSO"])
        if not nome:
            continue
        existente = find_course_sqlite(cur, nome)
        area = txt(row.get("AREA", "")).upper()
        if not area and existente:
            area_row = cur.execute("SELECT area FROM cursos WHERE id=?", (int(existente[0]),)).fetchone()
            area = area_row[0].upper() if area_row and area_row[0] else ""
        area = area or infer_area_sqlite(cur, nome, "")
        nivel = nivel_minimo(row["NIVEL"])
        descricao = txt(row.get("DESCRICAO", ""))
        estoque = int_or_zero(row["QUANTIDADE"])
        if existente:
            cur.execute(
                """UPDATE cursos
                   SET area=?, nivel=?, descricao=?, estoque_total=?, ativo=1
                   WHERE id=?""",
                (area, nivel, descricao, estoque, int(existente[0])),
            )
            cur.execute(
                """DELETE FROM cursos
                   WHERE id<>? AND (id_questionario IS NULL OR id_questionario='')
                   AND REPLACE(LOWER(curso), '  ', ' ')=REPLACE(LOWER(?), '  ', ' ')""",
                (int(existente[0]), nome),
            )
            atualizados += 1
        else:
            cur.execute(
                """INSERT INTO cursos(curso,area,nivel,descricao,carga_horaria,owner_email,estoque_total,ativo)
                   VALUES(?,?,?,?,?,?,?,1)""",
                (nome, area, nivel, descricao, "", "", estoque),
            )
            criados += 1
    conn.commit()
    conn.close()
    print(f"SQLite BASE_CURSOS OK: {criados} criados, {atualizados} atualizados.")


def import_avaliacao_sqlite(db_path: Path, xlsx_path: Path) -> None:
    perguntas = read_base_avaliacao(xlsx_path)
    conn = sqlite3.connect(db_path)
    ensure_sqlite_schema(conn)
    cur = conn.cursor()
    cur.execute("DELETE FROM perguntas_qualificacao")
    rows = []
    for idx, row in perguntas.iterrows():
        rows.append((
            txt(row["ID"]),
            txt(row["BLOCO"]),
            int_or_zero(row["ORDEM"]) or idx + 1,
            txt(row["PERGUNTA"]),
            txt(row["TIPO"]) or "Múltipla",
            txt(row["OPCAO_1"]),
            txt(row["OPCAO_2"]),
            txt(row["OPCAO_3"]),
            0,
            5,
            10,
            1,
        ))
    cur.executemany(
        """INSERT INTO perguntas_qualificacao(
               id_externo,questionario,ordem,pergunta,tipo,opcao_1,opcao_2,opcao_3,
               pontos_1,pontos_2,pontos_3,ativo)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    conn.commit()
    conn.close()
    print(f"SQLite avaliação OK: {len(rows)} perguntas substituídas.")


def import_bpf_sqlite(db_path: Path, xlsx_path: Path) -> None:
    perguntas = read_base_bpf(xlsx_path)
    conn = sqlite3.connect(db_path)
    ensure_sqlite_schema(conn)
    cur = conn.cursor()
    cur.execute("DELETE FROM perguntas_bpf")
    rows = []
    for idx, row in perguntas.iterrows():
        rows.append((
            txt(row["SECAO"]),
            txt(row["SUBSECAO"]),
            txt(row["CODIGOPERGUNTA"]),
            int_or_zero(row["ORDEM"]) or idx + 1,
            txt(row["PERGUNTA"]),
            txt(row["TIPORESPOSTA"]) or "Multipla",
            txt(row["OPCOES"]) or "S;N;P;NA",
            1,
            1,
        ))
    cur.executemany(
        """INSERT INTO perguntas_bpf(
               secao,subsecao,codigo_pergunta,ordem,pergunta,tipo_resposta,opcoes,pontos_sim,ativo)
           VALUES(?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    conn.commit()
    conn.close()
    print(f"SQLite BPF OK: {len(rows)} perguntas substituídas.")


def read_base(path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    sheets = pd.read_excel(path, sheet_name=None)
    required = {"Mapa_Solucoes", "Questionarios", "Perguntas", "Alternativas"}
    missing = required - set(sheets)
    if missing:
        raise ValueError(f"Planilha sem abas obrigatórias: {', '.join(sorted(missing))}")

    mapa = sheets["Mapa_Solucoes"].fillna("")
    questionarios = sheets["Questionarios"].fillna("")
    perguntas = sheets["Perguntas"].fillna("")
    alternativas = sheets["Alternativas"].fillna("")

    for df in (mapa, questionarios, perguntas, alternativas):
        df.columns = [str(c).strip() for c in df.columns]

    return mapa, questionarios, perguntas, alternativas


def ensure_sqlite_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    migrations = {
        "cursos": [
            ("campo_link", "TEXT"),
            ("id_questionario", "TEXT"),
            ("questionario", "TEXT"),
            ("status_mapeamento", "TEXT"),
            ("descricao", "TEXT"),
            ("carga_horaria", "TEXT"),
            ("owner_email", "TEXT"),
            ("estoque_total", "INTEGER DEFAULT 0"),
        ],
        "perguntas_curso": [
            ("id_pergunta", "TEXT"),
            ("id_questionario", "TEXT"),
            ("questionario", "TEXT"),
        ],
        "alternativas_curso": [
            ("id_alternativa", "TEXT"),
            ("id_pergunta", "TEXT"),
            ("id_questionario", "TEXT"),
        ],
        "perguntas_qualificacao": [
            ("id_externo", "TEXT"),
            ("tipo", "TEXT DEFAULT 'Múltipla'"),
            ("opcao_1", "TEXT"),
            ("opcao_2", "TEXT"),
            ("opcao_3", "TEXT"),
            ("pontos_1", "INTEGER DEFAULT 0"),
            ("pontos_2", "INTEGER DEFAULT 5"),
            ("pontos_3", "INTEGER DEFAULT 10"),
        ],
        "perguntas_bpf": [
            ("secao", "TEXT"),
            ("subsecao", "TEXT"),
            ("codigo_pergunta", "TEXT"),
            ("tipo_resposta", "TEXT DEFAULT 'Multipla'"),
            ("opcoes", "TEXT DEFAULT 'S;N;P;NA'"),
        ],
    }
    for table, columns in migrations.items():
        existing = [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]
        for column, definition in columns:
            if column not in existing:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    conn.commit()


def import_sqlite(db_path: Path, xlsx_path: Path) -> None:
    mapa, questionarios, perguntas, alternativas = read_base(xlsx_path)
    ids_questionario = sorted({txt(v) for v in mapa["ID_QUESTIONARIO"].tolist() if txt(v)})

    conn = sqlite3.connect(db_path)
    ensure_sqlite_schema(conn)
    cur = conn.cursor()

    placeholders = ",".join("?" for _ in ids_questionario)
    if ids_questionario:
        pergunta_ids = [r[0] for r in cur.execute(
            f"SELECT id FROM perguntas_curso WHERE id_questionario IN ({placeholders})",
            ids_questionario,
        ).fetchall()]
        if pergunta_ids:
            ph_perguntas = ",".join("?" for _ in pergunta_ids)
            cur.execute(f"DELETE FROM alternativas_curso WHERE pergunta_id IN ({ph_perguntas})", pergunta_ids)
        cur.execute(f"DELETE FROM alternativas_curso WHERE id_questionario IN ({placeholders})", ids_questionario)
        cur.execute(f"DELETE FROM perguntas_curso WHERE id_questionario IN ({placeholders})", ids_questionario)
        cur.execute(f"DELETE FROM curso_questionarios WHERE id_questionario IN ({placeholders})", ids_questionario)
        cur.execute(f"DELETE FROM cursos WHERE id_questionario IN ({placeholders})", ids_questionario)

    q_by_id = {
        txt(row["ID_QUESTIONARIO"]): txt(row["QUESTIONARIO"])
        for _, row in questionarios.iterrows()
    }
    perguntas_by_q = {
        qid: group.sort_values("ORDEM")
        for qid, group in perguntas.groupby(perguntas["ID_QUESTIONARIO"].map(txt))
    }
    alternativas_by_pergunta = {
        pid: group.sort_values(["ORDEM_PERGUNTA", "PONTOS"])
        for pid, group in alternativas.groupby(alternativas["ID_PERGUNTA"].map(txt))
    }

    cursos_criados = perguntas_criadas = alternativas_criadas = 0
    for _, row in mapa.iterrows():
        id_questionario = txt(row["ID_QUESTIONARIO"])
        nome_solucao = txt(row["NOME_SOLUCAO"])
        if not nome_solucao:
            continue
        area = txt(row["ORIGEM"]).upper()
        questionario_nome = txt(row["QUESTIONARIO"]) or q_by_id.get(id_questionario, "")
        status = txt(row["STATUS"])
        cur.execute(
            """INSERT INTO cursos(
                   curso,area,nivel,campo_link,id_questionario,questionario,status_mapeamento,
                   descricao,carga_horaria,owner_email,estoque_total,ativo)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,1)""",
            (
                nome_solucao,
                area,
                NIVEL_PADRAO,
                txt(row["CAMPO_LINK"]),
                id_questionario,
                questionario_nome,
                status,
                f"Importado de {xlsx_path.name}",
                "",
                "",
                ESTOQUE_PADRAO,
            ),
        )
        curso_id = cur.lastrowid
        cursos_criados += 1

        if id_questionario and questionario_nome and status != "Sem questionário":
            cur.execute(
                "INSERT INTO curso_questionarios(curso_id,id_questionario,nome_questionario,ativo) VALUES(?,?,?,1)",
                (curso_id, id_questionario, questionario_nome),
            )

        for _, pergunta in perguntas_by_q.get(id_questionario, pd.DataFrame()).iterrows():
            id_pergunta = txt(pergunta["ID_PERGUNTA"])
            cur.execute(
                """INSERT INTO perguntas_curso(
                       curso_id,id_pergunta,id_questionario,questionario,ordem,pergunta,pontos_sim,ativo)
                   VALUES(?,?,?,?,?,?,0,1)""",
                (
                    curso_id,
                    id_pergunta,
                    id_questionario,
                    txt(pergunta["QUESTIONARIO"]) or questionario_nome,
                    int(pergunta["ORDEM"]),
                    txt(pergunta["PERGUNTA"]),
                ),
            )
            pergunta_id = cur.lastrowid
            perguntas_criadas += 1

            for ordem_alt, alternativa in enumerate(alternativas_by_pergunta.get(id_pergunta, pd.DataFrame()).itertuples(index=False), start=1):
                data = alternativa._asdict()
                cur.execute(
                    """INSERT INTO alternativas_curso(
                           pergunta_id,id_alternativa,id_pergunta,id_questionario,ordem,alternativa,pontos,ativo)
                       VALUES(?,?,?,?,?,?,?,1)""",
                    (
                        pergunta_id,
                        txt(data["ID_ALTERNATIVA"]),
                        id_pergunta,
                        id_questionario,
                        ordem_alt,
                        txt(data["OPCAO"]),
                        int(data["PONTOS"]),
                    ),
                )
                alternativas_criadas += 1

    conn.commit()
    conn.close()
    print(f"SQLite OK: {cursos_criados} cursos, {perguntas_criadas} perguntas, {alternativas_criadas} alternativas.")


def postgres_conn(database_url: str):
    try:
        import psycopg
    except ImportError as exc:
        raise SystemExit("Instale psycopg para importar no Supabase: pip install 'psycopg[binary]'") from exc
    return psycopg.connect(database_url)


def ensure_supabase_schema(conn) -> None:
    ddl = """
    CREATE TABLE IF NOT EXISTS cursos (
        id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        curso text,
        area text,
        nivel text,
        campo_link text,
        id_questionario text,
        questionario text,
        status_mapeamento text,
        descricao text,
        carga_horaria text,
        owner_email text,
        estoque_total integer DEFAULT 0,
        ativo integer DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS perguntas_curso (
        id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        curso_id bigint,
        id_pergunta text,
        id_questionario text,
        questionario text,
        ordem integer,
        pergunta text,
        pontos_sim integer DEFAULT 0,
        ativo integer DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS alternativas_curso (
        id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        pergunta_id bigint,
        id_alternativa text,
        id_pergunta text,
        id_questionario text,
        ordem integer,
        alternativa text,
        pontos integer DEFAULT 0,
        ativo integer DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS curso_questionarios (
        id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        curso_id bigint,
        id_questionario text,
        nome_questionario text,
        ativo integer DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS perguntas_qualificacao (
        id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        id_externo text,
        questionario text,
        ordem integer,
        pergunta text,
        tipo text DEFAULT 'Múltipla',
        opcao_1 text,
        opcao_2 text,
        opcao_3 text,
        pontos_1 integer DEFAULT 0,
        pontos_2 integer DEFAULT 5,
        pontos_3 integer DEFAULT 10,
        pontos_sim integer DEFAULT 1,
        ativo integer DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS perguntas_bpf (
        id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        secao text,
        subsecao text,
        codigo_pergunta text,
        ordem integer,
        pergunta text,
        tipo_resposta text DEFAULT 'Multipla',
        opcoes text DEFAULT 'S;N;P;NA',
        pontos_sim integer DEFAULT 1,
        ativo integer DEFAULT 1
    );
    ALTER TABLE cursos ADD COLUMN IF NOT EXISTS campo_link text;
    ALTER TABLE cursos ADD COLUMN IF NOT EXISTS id_questionario text;
    ALTER TABLE cursos ADD COLUMN IF NOT EXISTS questionario text;
    ALTER TABLE cursos ADD COLUMN IF NOT EXISTS status_mapeamento text;
    ALTER TABLE cursos ADD COLUMN IF NOT EXISTS descricao text;
    ALTER TABLE cursos ADD COLUMN IF NOT EXISTS carga_horaria text;
    ALTER TABLE cursos ADD COLUMN IF NOT EXISTS owner_email text;
    ALTER TABLE cursos ADD COLUMN IF NOT EXISTS estoque_total integer DEFAULT 0;
    ALTER TABLE cursos ADD COLUMN IF NOT EXISTS ativo integer DEFAULT 1;
    ALTER TABLE perguntas_curso ADD COLUMN IF NOT EXISTS curso_id bigint;
    ALTER TABLE perguntas_curso ADD COLUMN IF NOT EXISTS id_pergunta text;
    ALTER TABLE perguntas_curso ADD COLUMN IF NOT EXISTS id_questionario text;
    ALTER TABLE perguntas_curso ADD COLUMN IF NOT EXISTS questionario text;
    ALTER TABLE perguntas_curso ADD COLUMN IF NOT EXISTS ordem integer;
    ALTER TABLE perguntas_curso ADD COLUMN IF NOT EXISTS pergunta text;
    ALTER TABLE perguntas_curso ADD COLUMN IF NOT EXISTS pontos_sim integer DEFAULT 0;
    ALTER TABLE perguntas_curso ADD COLUMN IF NOT EXISTS ativo integer DEFAULT 1;
    ALTER TABLE alternativas_curso ADD COLUMN IF NOT EXISTS pergunta_id bigint;
    ALTER TABLE alternativas_curso ADD COLUMN IF NOT EXISTS id_alternativa text;
    ALTER TABLE alternativas_curso ADD COLUMN IF NOT EXISTS id_pergunta text;
    ALTER TABLE alternativas_curso ADD COLUMN IF NOT EXISTS id_questionario text;
    ALTER TABLE alternativas_curso ADD COLUMN IF NOT EXISTS ordem integer;
    ALTER TABLE alternativas_curso ADD COLUMN IF NOT EXISTS alternativa text;
    ALTER TABLE alternativas_curso ADD COLUMN IF NOT EXISTS pontos integer DEFAULT 0;
    ALTER TABLE alternativas_curso ADD COLUMN IF NOT EXISTS ativo integer DEFAULT 1;
    ALTER TABLE perguntas_qualificacao ADD COLUMN IF NOT EXISTS id_externo text;
    ALTER TABLE perguntas_qualificacao ADD COLUMN IF NOT EXISTS questionario text;
    ALTER TABLE perguntas_qualificacao ADD COLUMN IF NOT EXISTS ordem integer;
    ALTER TABLE perguntas_qualificacao ADD COLUMN IF NOT EXISTS pergunta text;
    ALTER TABLE perguntas_qualificacao ADD COLUMN IF NOT EXISTS tipo text DEFAULT 'Múltipla';
    ALTER TABLE perguntas_qualificacao ADD COLUMN IF NOT EXISTS opcao_1 text;
    ALTER TABLE perguntas_qualificacao ADD COLUMN IF NOT EXISTS opcao_2 text;
    ALTER TABLE perguntas_qualificacao ADD COLUMN IF NOT EXISTS opcao_3 text;
    ALTER TABLE perguntas_qualificacao ADD COLUMN IF NOT EXISTS pontos_1 integer DEFAULT 0;
    ALTER TABLE perguntas_qualificacao ADD COLUMN IF NOT EXISTS pontos_2 integer DEFAULT 5;
    ALTER TABLE perguntas_qualificacao ADD COLUMN IF NOT EXISTS pontos_3 integer DEFAULT 10;
    ALTER TABLE perguntas_qualificacao ADD COLUMN IF NOT EXISTS pontos_sim integer DEFAULT 1;
    ALTER TABLE perguntas_qualificacao ADD COLUMN IF NOT EXISTS ativo integer DEFAULT 1;
    ALTER TABLE perguntas_bpf ADD COLUMN IF NOT EXISTS secao text;
    ALTER TABLE perguntas_bpf ADD COLUMN IF NOT EXISTS subsecao text;
    ALTER TABLE perguntas_bpf ADD COLUMN IF NOT EXISTS codigo_pergunta text;
    ALTER TABLE perguntas_bpf ADD COLUMN IF NOT EXISTS ordem integer;
    ALTER TABLE perguntas_bpf ADD COLUMN IF NOT EXISTS pergunta text;
    ALTER TABLE perguntas_bpf ADD COLUMN IF NOT EXISTS tipo_resposta text DEFAULT 'Multipla';
    ALTER TABLE perguntas_bpf ADD COLUMN IF NOT EXISTS opcoes text DEFAULT 'S;N;P;NA';
    ALTER TABLE perguntas_bpf ADD COLUMN IF NOT EXISTS pontos_sim integer DEFAULT 1;
    ALTER TABLE perguntas_bpf ADD COLUMN IF NOT EXISTS ativo integer DEFAULT 1;
    ALTER TABLE cursos DROP CONSTRAINT IF EXISTS cursos_area_check;
    ALTER TABLE cursos ADD CONSTRAINT cursos_area_check
        CHECK (area IN ('SEBRAE', 'SEMATEC', 'CIMATEC'));
    ALTER TABLE cursos DROP CONSTRAINT IF EXISTS cursos_nivel_check;
    ALTER TABLE cursos ADD CONSTRAINT cursos_nivel_check
        CHECK (nivel IN ('Basico', 'Intermediario', 'Avancado', 'Básico', 'Intermediário', 'Avançado'));
    UPDATE cursos SET area='CIMATEC' WHERE area='SEMATEC';
    """
    with conn.cursor() as cur:
        cur.execute(ddl)
    conn.commit()


def import_supabase(database_url: str, xlsx_path: Path) -> None:
    mapa, questionarios, perguntas, alternativas = read_base(xlsx_path)
    ids_questionario = sorted({txt(v) for v in mapa["ID_QUESTIONARIO"].tolist() if txt(v)})

    conn = postgres_conn(database_url)
    ensure_supabase_schema(conn)

    q_by_id = {txt(row["ID_QUESTIONARIO"]): txt(row["QUESTIONARIO"]) for _, row in questionarios.iterrows()}
    perguntas_by_q = {qid: group.sort_values("ORDEM") for qid, group in perguntas.groupby(perguntas["ID_QUESTIONARIO"].map(txt))}
    alternativas_by_pergunta = {
        pid: group.sort_values(["ORDEM_PERGUNTA", "PONTOS"])
        for pid, group in alternativas.groupby(alternativas["ID_PERGUNTA"].map(txt))
    }

    with conn.cursor() as cur:
        if ids_questionario:
            cur.execute("SELECT id FROM perguntas_curso WHERE id_questionario = ANY(%s)", (ids_questionario,))
            pergunta_ids = [r[0] for r in cur.fetchall()]
            if pergunta_ids:
                cur.execute("DELETE FROM alternativas_curso WHERE pergunta_id = ANY(%s)", (pergunta_ids,))
            cur.execute("DELETE FROM alternativas_curso WHERE id_questionario = ANY(%s)", (ids_questionario,))
            cur.execute("DELETE FROM perguntas_curso WHERE id_questionario = ANY(%s)", (ids_questionario,))
            cur.execute("DELETE FROM curso_questionarios WHERE id_questionario = ANY(%s)", (ids_questionario,))
            cur.execute("DELETE FROM cursos WHERE id_questionario = ANY(%s)", (ids_questionario,))

        cursos_criados = perguntas_criadas = alternativas_criadas = 0
        for _, row in mapa.iterrows():
            id_questionario = txt(row["ID_QUESTIONARIO"])
            nome_solucao = txt(row["NOME_SOLUCAO"])
            if not nome_solucao:
                continue
            area = txt(row["ORIGEM"]).upper()
            questionario_nome = txt(row["QUESTIONARIO"]) or q_by_id.get(id_questionario, "")
            status = txt(row["STATUS"])
            cur.execute(
                """INSERT INTO cursos(
                       curso,area,nivel,campo_link,id_questionario,questionario,status_mapeamento,
                       descricao,carga_horaria,owner_email,estoque_total)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   RETURNING id""",
                (
                    nome_solucao,
                    area,
                    NIVEL_PADRAO,
                    txt(row["CAMPO_LINK"]),
                    id_questionario,
                    questionario_nome,
                    status,
                    f"Importado de {xlsx_path.name}",
                    "",
                    "",
                    ESTOQUE_PADRAO,
                ),
            )
            curso_id = cur.fetchone()[0]
            cursos_criados += 1

            if id_questionario and questionario_nome and status != "Sem questionário":
                cur.execute(
                    "INSERT INTO curso_questionarios(curso_id,id_questionario,nome_questionario) VALUES(%s,%s,%s)",
                    (curso_id, id_questionario, questionario_nome),
                )

            for _, pergunta in perguntas_by_q.get(id_questionario, pd.DataFrame()).iterrows():
                id_pergunta = txt(pergunta["ID_PERGUNTA"])
                cur.execute(
                    """INSERT INTO perguntas_curso(
                           curso_id,id_pergunta,id_questionario,questionario,ordem,pergunta,pontos_sim)
                       VALUES(%s,%s,%s,%s,%s,%s,0)
                       RETURNING id""",
                    (
                        curso_id,
                        id_pergunta,
                        id_questionario,
                        txt(pergunta["QUESTIONARIO"]) or questionario_nome,
                        int(pergunta["ORDEM"]),
                        txt(pergunta["PERGUNTA"]),
                    ),
                )
                pergunta_id = cur.fetchone()[0]
                perguntas_criadas += 1

                for ordem_alt, alternativa in enumerate(alternativas_by_pergunta.get(id_pergunta, pd.DataFrame()).itertuples(index=False), start=1):
                    data = alternativa._asdict()
                    cur.execute(
                        """INSERT INTO alternativas_curso(
                               pergunta_id,id_alternativa,id_pergunta,id_questionario,ordem,alternativa,pontos)
                           VALUES(%s,%s,%s,%s,%s,%s,%s)""",
                        (
                            pergunta_id,
                            txt(data["ID_ALTERNATIVA"]),
                            id_pergunta,
                            id_questionario,
                            ordem_alt,
                            txt(data["OPCAO"]),
                            int(data["PONTOS"]),
                        ),
                    )
                    alternativas_criadas += 1

    conn.commit()
    conn.close()
    print(f"Supabase OK: {cursos_criados} cursos, {perguntas_criadas} perguntas, {alternativas_criadas} alternativas.")


def infer_area_supabase(cur, curso: str, fallback: str) -> str:
    if fallback:
        return fallback.upper()
    cur.execute(
        "SELECT area FROM cursos WHERE curso=%s AND area IS NOT NULL AND area<>'' ORDER BY id DESC LIMIT 1",
        (curso,),
    )
    row = cur.fetchone()
    return row[0].upper() if row and row[0] else "SEBRAE"


def find_course_supabase(cur, curso: str):
    target = normalized_name(curso)
    cur.execute("SELECT id, curso, id_questionario FROM cursos ORDER BY id")
    rows = cur.fetchall()
    matches = [row for row in rows if normalized_name(row[1]) == target]
    if not matches:
        return None, []
    with_questionario = [row for row in matches if row[2]]
    keeper = with_questionario[0] if with_questionario else matches[0]
    duplicates = [row for row in matches if row[0] != keeper[0] and not row[2]]
    return keeper, duplicates


def import_cursos_supabase(database_url: str, xlsx_path: Path) -> None:
    cursos = read_base_cursos(xlsx_path)
    conn = postgres_conn(database_url)
    ensure_supabase_schema(conn)
    criados = atualizados = 0
    with conn.cursor() as cur:
        for _, row in cursos.iterrows():
            nome = txt(row["CURSO"])
            if not nome:
                continue
            existente, duplicados = find_course_supabase(cur, nome)
            area = txt(row.get("AREA", "")).upper()
            if not area and existente:
                cur.execute("SELECT area FROM cursos WHERE id=%s", (existente[0],))
                area_row = cur.fetchone()
                area = area_row[0].upper() if area_row and area_row[0] else ""
            area = area or infer_area_supabase(cur, nome, "")
            nivel = nivel_minimo(row["NIVEL"])
            descricao = txt(row.get("DESCRICAO", ""))
            estoque = int_or_zero(row["QUANTIDADE"])
            if existente:
                cur.execute(
                    """UPDATE cursos
                       SET area=%s, nivel=%s, descricao=%s, estoque_total=%s, ativo=TRUE
                       WHERE id=%s""",
                    (area, nivel, descricao, estoque, existente[0]),
                )
                for duplicado in duplicados:
                    cur.execute("DELETE FROM cursos WHERE id=%s", (duplicado[0],))
                atualizados += 1
            else:
                cur.execute(
                    """INSERT INTO cursos(curso,area,nivel,descricao,carga_horaria,owner_email,estoque_total)
                       VALUES(%s,%s,%s,%s,%s,%s,%s)""",
                    (nome, area, nivel, descricao, "", "", estoque),
                )
                criados += 1
    conn.commit()
    conn.close()
    print(f"Supabase BASE_CURSOS OK: {criados} criados, {atualizados} atualizados.")


def import_avaliacao_supabase(database_url: str, xlsx_path: Path) -> None:
    perguntas = read_base_avaliacao(xlsx_path)
    conn = postgres_conn(database_url)
    ensure_supabase_schema(conn)
    with conn.cursor() as cur:
        cur.execute("DELETE FROM perguntas_qualificacao")
        rows = []
        for idx, row in perguntas.iterrows():
            rows.append((
                txt(row["ID"]),
                txt(row["BLOCO"]),
                int_or_zero(row["ORDEM"]) or idx + 1,
                txt(row["PERGUNTA"]),
                txt(row["TIPO"]) or "Múltipla",
                txt(row["OPCAO_1"]),
                txt(row["OPCAO_2"]),
                txt(row["OPCAO_3"]),
                0,
                5,
                10,
            ))
        cur.executemany(
            """INSERT INTO perguntas_qualificacao(
                   id_externo,questionario,ordem,pergunta,tipo,opcao_1,opcao_2,opcao_3,
                   pontos_1,pontos_2,pontos_3)
               VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            rows,
        )
    conn.commit()
    conn.close()
    print(f"Supabase avaliação OK: {len(rows)} perguntas substituídas.")


def import_bpf_supabase(database_url: str, xlsx_path: Path) -> None:
    perguntas = read_base_bpf(xlsx_path)
    conn = postgres_conn(database_url)
    ensure_supabase_schema(conn)
    with conn.cursor() as cur:
        cur.execute("DELETE FROM perguntas_bpf")
        rows = []
        for idx, row in perguntas.iterrows():
            rows.append((
                txt(row["SECAO"]),
                txt(row["SUBSECAO"]),
                txt(row["CODIGOPERGUNTA"]),
                int_or_zero(row["ORDEM"]) or idx + 1,
                txt(row["PERGUNTA"]),
                txt(row["TIPORESPOSTA"]) or "Multipla",
                txt(row["OPCOES"]) or "S;N;P;NA",
                1,
            ))
        cur.executemany(
            """INSERT INTO perguntas_bpf(
                   secao,subsecao,codigo_pergunta,ordem,pergunta,tipo_resposta,opcoes,pontos_sim)
               VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",
            rows,
        )
    conn.commit()
    conn.close()
    print(f"Supabase BPF OK: {len(rows)} perguntas substituídas.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Importa Base_Soluções_Perguntas.xlsx para cursos/perguntas/alternativas.")
    parser.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    parser.add_argument("--cursos-xlsx", type=Path)
    parser.add_argument("--avaliacao-xlsx", type=Path)
    parser.add_argument("--bpf-xlsx", type=Path)
    parser.add_argument("--skip-solucoes", action="store_true", help="Não importa a Base_Soluções_Perguntas.")
    parser.add_argument("--sqlite", type=Path, default=DEFAULT_SQLITE)
    parser.add_argument("--target", choices=["sqlite", "supabase", "both"], default="sqlite")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL"))
    args = parser.parse_args()

    if args.target in {"sqlite", "both"}:
        if args.xlsx and not args.skip_solucoes:
            import_sqlite(args.sqlite, args.xlsx)
        if args.cursos_xlsx:
            import_cursos_sqlite(args.sqlite, args.cursos_xlsx)
        if args.avaliacao_xlsx:
            import_avaliacao_sqlite(args.sqlite, args.avaliacao_xlsx)
        if args.bpf_xlsx:
            import_bpf_sqlite(args.sqlite, args.bpf_xlsx)
    if args.target in {"supabase", "both"}:
        if not args.database_url:
            raise SystemExit("Informe --database-url ou defina DATABASE_URL/SUPABASE_DB_URL.")
        if args.xlsx and not args.skip_solucoes:
            import_supabase(args.database_url, args.xlsx)
        if args.cursos_xlsx:
            import_cursos_supabase(args.database_url, args.cursos_xlsx)
        if args.avaliacao_xlsx:
            import_avaliacao_supabase(args.database_url, args.avaliacao_xlsx)
        if args.bpf_xlsx:
            import_bpf_supabase(args.database_url, args.bpf_xlsx)


if __name__ == "__main__":
    main()
