import hashlib
import os
import re
import unicodedata
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_WORKBOOK_NAME = "BASE_CURSOS_CIMATEC_SEBRAE.xlsx"
IMPORT_KEY = "cursos_planilha"


def text_key(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("\n", " ")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text)).strip()


def clean_text(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\n", " ")).strip()


def course_match_key(value: Any) -> str:
    text = clean_text(value)
    try:
        text = text.encode("latin-1").decode("utf-8")
    except Exception:
        pass
    text = text_key(text)
    text = re.sub(r"^\d+\s*", "", text)
    return text.strip()


def default_workbook_candidates(app_dir: Path) -> list[Path]:
    configured = clean_text(os.getenv("CURSOS_XLSX_PATH"))
    candidates: list[Path] = []
    if configured:
        candidates.append(Path(configured))
    base_dirs = [
        app_dir,
        app_dir / "data",
        app_dir / "assets",
        Path.home() / "Downloads",
        Path(r"C:\Users\fabio\Downloads"),
    ]
    for base_dir in base_dirs:
        candidates.append(base_dir / DEFAULT_WORKBOOK_NAME)
        if base_dir.exists():
            candidates.extend(sorted(base_dir.glob("BASE_CURSOS_CIMATEC_SEBRAE*.xlsx"), key=lambda path: path.stat().st_mtime, reverse=True))
    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def locate_workbook(app_dir: Path) -> Path | None:
    configured = clean_text(os.getenv("CURSOS_XLSX_PATH"))
    if configured:
        path = Path(configured)
        return path if path.exists() else None
    existing = [candidate for candidate in default_workbook_candidates(app_dir) if candidate.exists()]
    if existing:
        return max(existing, key=lambda path: path.stat().st_mtime)
    return None


def workbook_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _matching_column(columns: list[str], *aliases: str) -> str:
    normalized = {col: text_key(col) for col in columns}
    for alias in aliases:
        alias_key = text_key(alias)
        for col, col_key in normalized.items():
            if col_key == alias_key:
                return col
        for col, col_key in normalized.items():
            if alias_key and alias_key in col_key:
                return col
    raise KeyError(f"Coluna não encontrada para aliases: {aliases}")


def _sheet_by_name(xls: pd.ExcelFile, expected_name: str) -> str:
    target = text_key(expected_name)
    for sheet_name in xls.sheet_names:
        if text_key(sheet_name) == target:
            return sheet_name
    for sheet_name in xls.sheet_names:
        if target in text_key(sheet_name):
            return sheet_name
    raise KeyError(f"Aba não encontrada: {expected_name}")


def _row_value(row: pd.Series, column: str, default: Any = "") -> Any:
    value = row.get(column, default)
    if isinstance(value, float) and pd.isna(value):
        return default
    return value


def load_course_catalog(workbook_path: Path) -> dict[str, Any]:
    xls = pd.ExcelFile(workbook_path)
    questions_sheet = _sheet_by_name(xls, "PERGUNTAS_SOLUÇÕES")
    stock_sheet = _sheet_by_name(xls, "ESTOQUE_SOLUÇÕES")

    questions_df = pd.read_excel(xls, sheet_name=questions_sheet).dropna(how="all")
    stock_df = pd.read_excel(xls, sheet_name=stock_sheet).dropna(how="all")
    questions_df.columns = [str(col) for col in questions_df.columns]
    stock_df.columns = [str(col) for col in stock_df.columns]

    solution_col = _matching_column(list(questions_df.columns), "SOLUÇÃO", "SOLUCOES", "SOLUCAO")
    description_col = _matching_column(list(questions_df.columns), "DESCRIÇÃO", "DESCRICAO")
    area_col = _matching_column(list(questions_df.columns), "AREA")
    level_col = _matching_column(list(questions_df.columns), "QUALIFICAÇÃO", "QUALIFICACAO")
    question_col = _matching_column(list(questions_df.columns), "PERGUNTA")
    alternative_col = _matching_column(list(questions_df.columns), "ALTERNATIVA")
    value_col = _matching_column(list(questions_df.columns), "VALOR")

    stock_solution_col = _matching_column(list(stock_df.columns), "SOLUÇÕES", "SOLUCOES", "SOLUÇÃO", "SOLUCAO")
    quantity_col = _matching_column(list(stock_df.columns), "QUANTIDADE")

    stock_lookup: dict[str, int] = {}
    stock_raw_lookup: dict[str, int] = {}
    for _, row in stock_df.iterrows():
        solution_name = clean_text(_row_value(row, stock_solution_col))
        if not solution_name:
            continue
        quantity_value = _row_value(row, quantity_col, 0)
        try:
            quantity = int(float(quantity_value or 0))
        except Exception:
            quantity = 0
        key = text_key(solution_name)
        stock_lookup[key] = stock_lookup.get(key, 0) + quantity
        stock_raw_lookup[solution_name] = quantity

    courses: list[dict[str, Any]] = []
    missing_stock: list[str] = []
    for solution_name, course_rows in questions_df.groupby(solution_col, sort=False):
        course_name = clean_text(solution_name)
        if not course_name:
            continue
        valid_rows = course_rows[
            course_rows[question_col].notna()
            & course_rows[alternative_col].notna()
        ].copy()
        if valid_rows.empty:
            continue
        first_row = valid_rows.iloc[0]
        course_key = text_key(course_name)
        stock_total = stock_lookup.get(course_key)
        if stock_total is None and stock_lookup:
            candidates = sorted(
                stock_lookup.keys(),
                key=lambda key: SequenceMatcher(None, course_key, key).ratio(),
                reverse=True,
            )
            if candidates:
                best_key = candidates[0]
                if SequenceMatcher(None, course_key, best_key).ratio() >= 0.82:
                    stock_total = stock_lookup[best_key]
        if stock_total is None:
            stock_total = 0
            missing_stock.append(course_name)

        questions: list[dict[str, Any]] = []
        question_index = 0
        for question_text, question_rows in valid_rows.groupby(question_col, sort=False):
            question_label = clean_text(question_text)
            if not question_label:
                continue
            question_index += 1
            alternatives: list[dict[str, Any]] = []
            for alternative_index, (_, alt_row) in enumerate(question_rows.iterrows(), start=1):
                alternative_text = clean_text(_row_value(alt_row, alternative_col))
                if not alternative_text:
                    continue
                raw_points = _row_value(alt_row, value_col, 0)
                try:
                    points = int(float(raw_points or 0))
                except Exception:
                    points = 0
                alternatives.append(
                    {
                        "ordem": alternative_index,
                        "alternativa": alternative_text,
                        "pontos": points,
                    }
                )
            if not alternatives:
                continue
            questions.append(
                {
                    "ordem": question_index,
                    "pergunta": question_label,
                    "alternativas": alternatives,
                }
            )

        if not questions:
            continue
        courses.append(
            {
                "curso": course_name,
                "curso_key": course_key,
                "descricao": clean_text(_row_value(first_row, description_col)),
                "area": clean_text(_row_value(first_row, area_col)).upper() or "CIMATEC",
                "nivel": clean_text(_row_value(first_row, level_col)),
                "questionario": course_name,
                "id_questionario": course_key.replace(" ", "_"),
                "status_mapeamento": "Importado da planilha",
                "estoque_total": stock_total,
                "questions": questions,
            }
        )

    return {
        "courses": courses,
        "missing_stock": missing_stock,
        "areas": sorted({course["area"] for course in courses}),
    }


def _sql(sql: str, use_postgres: bool) -> str:
    return sql.replace("?", "%s") if use_postgres else sql


def _fetch_value(row: Any, key: str | int, default: Any = None) -> Any:
    if row is None:
        return default
    if isinstance(row, dict):
        return row.get(key, default)
    try:
        return row[key]
    except Exception:
        return default


def _execute(cursor: Any, sql: str, params: tuple[Any, ...], use_postgres: bool):
    cursor.execute(_sql(sql, use_postgres), params)


def _insert_and_get_id(cursor: Any, sql: str, params: tuple[Any, ...], use_postgres: bool) -> int:
    if use_postgres:
        cursor.execute(_sql(f"{sql} RETURNING id", use_postgres), params)
        row = cursor.fetchone()
        return int(_fetch_value(row, "id", _fetch_value(row, 0, 0)) or 0)
    cursor.execute(sql, params)
    return int(getattr(cursor, "lastrowid", 0) or 0)


def sync_course_catalog(db_conn: Any, app_dir: Path, use_postgres: bool) -> dict[str, Any]:
    workbook_path = locate_workbook(app_dir)
    if not workbook_path:
        return {"found": False, "updated": False, "reason": "workbook_not_found"}

    fingerprint = workbook_hash(workbook_path)
    cursor = db_conn.cursor()
    if use_postgres:
        _execute(
            cursor,
            """CREATE TABLE IF NOT EXISTS importacoes_sistema (
                   id bigint generated by default as identity primary key,
                   chave text unique,
                   arquivo text,
                   hash_arquivo text,
                   data_atualizacao text
               )""",
            (),
            True,
        )
    else:
        _execute(
            cursor,
            """CREATE TABLE IF NOT EXISTS importacoes_sistema (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   chave TEXT UNIQUE,
                   arquivo TEXT,
                   hash_arquivo TEXT,
                   data_atualizacao TEXT
               )""",
            (),
            False,
        )
    _execute(
        cursor,
        "SELECT hash_arquivo FROM importacoes_sistema WHERE chave=?",
        (IMPORT_KEY,),
        use_postgres,
    )
    existing_import = cursor.fetchone()
    previous_hash = _fetch_value(existing_import, "hash_arquivo", _fetch_value(existing_import, 0))
    if previous_hash == fingerprint:
        return {"found": True, "updated": False, "workbook": str(workbook_path)}

    payload = load_course_catalog(workbook_path)
    courses = payload["courses"]
    if not courses:
        return {"found": True, "updated": False, "workbook": str(workbook_path), "reason": "no_courses"}

    _execute(
        cursor,
        "SELECT id, curso, area FROM cursos",
        (),
        use_postgres,
    )
    existing_courses = cursor.fetchall()
    _execute(
        cursor,
        "SELECT curso_id, COUNT(*) AS total FROM perguntas_curso GROUP BY curso_id",
        (),
        use_postgres,
    )
    question_counts = {
        int(_fetch_value(row, "curso_id", _fetch_value(row, 0, 0)) or 0): int(_fetch_value(row, "total", _fetch_value(row, 1, 0)) or 0)
        for row in cursor.fetchall()
    }
    course_bucket: dict[tuple[str, str], list[int]] = {}
    for row in existing_courses:
        key = (
            text_key(_fetch_value(row, "area", _fetch_value(row, 2, ""))),
            course_match_key(_fetch_value(row, "curso", _fetch_value(row, 1, ""))),
        )
        course_bucket.setdefault(key, []).append(int(_fetch_value(row, "id", _fetch_value(row, 0, 0)) or 0))
    course_map = {
        key: sorted(ids, key=lambda course_id: (-question_counts.get(course_id, 0), course_id))[0]
        for key, ids in course_bucket.items()
    }

    synced = 0
    for course in courses:
        course_key = (text_key(course["area"]), course_match_key(course["curso"]))
        course_id = course_map.get(course_key)
        if course_id:
            _execute(
                cursor,
                """UPDATE cursos
                   SET curso=?, area=?, nivel=?, descricao=?, id_questionario=?, questionario=?, status_mapeamento=?, estoque_total=?, ativo=?
                   WHERE id=?""",
                (
                    course["curso"],
                    course["area"],
                    course["nivel"],
                    course["descricao"],
                    course["id_questionario"],
                    course["questionario"],
                    course["status_mapeamento"],
                    course["estoque_total"],
                    True if use_postgres else 1,
                    course_id,
                ),
                use_postgres,
            )
        else:
            course_id = _insert_and_get_id(
                cursor,
                """INSERT INTO cursos(curso,area,nivel,descricao,id_questionario,questionario,status_mapeamento,estoque_total,ativo)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    course["curso"],
                    course["area"],
                    course["nivel"],
                    course["descricao"],
                    course["id_questionario"],
                    course["questionario"],
                    course["status_mapeamento"],
                    course["estoque_total"],
                    True if use_postgres else 1,
                ),
                use_postgres,
            )
            course_map[course_key] = course_id
            course_bucket.setdefault(course_key, []).append(course_id)

        duplicate_ids = [existing_id for existing_id in course_bucket.get(course_key, []) if existing_id != course_id]
        for duplicate_id in duplicate_ids:
            _execute(
                cursor,
                "UPDATE cursos SET ativo=? WHERE id=?",
                (False if use_postgres else 0, duplicate_id),
                use_postgres,
            )

        _execute(
            cursor,
            "SELECT id, pergunta FROM perguntas_curso WHERE curso_id=?",
            (course_id,),
            use_postgres,
        )
        existing_questions = cursor.fetchall()
        question_map = {
            text_key(_fetch_value(row, "pergunta", _fetch_value(row, 1, ""))): int(_fetch_value(row, "id", _fetch_value(row, 0, 0)) or 0)
            for row in existing_questions
        }

        for question in course["questions"]:
            question_key = text_key(question["pergunta"])
            question_id = question_map.get(question_key)
            if question_id:
                _execute(
                    cursor,
                    """UPDATE perguntas_curso
                       SET id_pergunta=?, id_questionario=?, questionario=?, ordem=?, pergunta=?, pontos_sim=?, ativo=?
                       WHERE id=?""",
                    (
                        f"{course['id_questionario']}_p{question['ordem']}",
                        course["id_questionario"],
                        course["questionario"],
                        question["ordem"],
                        question["pergunta"],
                        0,
                        True if use_postgres else 1,
                        question_id,
                    ),
                    use_postgres,
                )
            else:
                question_id = _insert_and_get_id(
                    cursor,
                    """INSERT INTO perguntas_curso(curso_id,id_pergunta,id_questionario,questionario,ordem,pergunta,pontos_sim,ativo)
                       VALUES(?,?,?,?,?,?,?,?)""",
                    (
                        course_id,
                        f"{course['id_questionario']}_p{question['ordem']}",
                        course["id_questionario"],
                        course["questionario"],
                        question["ordem"],
                        question["pergunta"],
                        0,
                        True if use_postgres else 1,
                    ),
                    use_postgres,
                )
                question_map[question_key] = question_id

            _execute(
                cursor,
                "SELECT id, alternativa FROM alternativas_curso WHERE pergunta_id=?",
                (question_id,),
                use_postgres,
            )
            existing_alternatives = cursor.fetchall()
            alternative_map = {
                text_key(_fetch_value(row, "alternativa", _fetch_value(row, 1, ""))): int(_fetch_value(row, "id", _fetch_value(row, 0, 0)) or 0)
                for row in existing_alternatives
            }
            for alternative in question["alternativas"]:
                alternative_key = text_key(alternative["alternativa"])
                alternative_id = alternative_map.get(alternative_key)
                if alternative_id:
                    _execute(
                        cursor,
                        """UPDATE alternativas_curso
                           SET id_alternativa=?, id_pergunta=?, id_questionario=?, ordem=?, alternativa=?, pontos=?, ativo=?
                           WHERE id=?""",
                        (
                            f"{course['id_questionario']}_p{question['ordem']}_a{alternative['ordem']}",
                            f"{course['id_questionario']}_p{question['ordem']}",
                            course["id_questionario"],
                            alternative["ordem"],
                            alternative["alternativa"],
                            alternative["pontos"],
                            True if use_postgres else 1,
                            alternative_id,
                        ),
                        use_postgres,
                    )
                else:
                    _execute(
                        cursor,
                        """INSERT INTO alternativas_curso(pergunta_id,id_alternativa,id_pergunta,id_questionario,ordem,alternativa,pontos,ativo)
                           VALUES(?,?,?,?,?,?,?,?)""",
                        (
                            question_id,
                            f"{course['id_questionario']}_p{question['ordem']}_a{alternative['ordem']}",
                            f"{course['id_questionario']}_p{question['ordem']}",
                            course["id_questionario"],
                            alternative["ordem"],
                            alternative["alternativa"],
                            alternative["pontos"],
                            True if use_postgres else 1,
                        ),
                        use_postgres,
                    )
        synced += 1

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if existing_import:
        _execute(
            cursor,
            "UPDATE importacoes_sistema SET arquivo=?, hash_arquivo=?, data_atualizacao=? WHERE chave=?",
            (workbook_path.name, fingerprint, now, IMPORT_KEY),
            use_postgres,
        )
    else:
        _execute(
            cursor,
            "INSERT INTO importacoes_sistema(chave,arquivo,hash_arquivo,data_atualizacao) VALUES(?,?,?,?)",
            (IMPORT_KEY, workbook_path.name, fingerprint, now),
            use_postgres,
        )

    return {
        "found": True,
        "updated": True,
        "workbook": str(workbook_path),
        "courses": synced,
        "areas": payload["areas"],
        "missing_stock": payload["missing_stock"],
    }
