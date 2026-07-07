import argparse
import hashlib
import os
import sqlite3
from pathlib import Path


TABLES = [
    "respostas_curso",
    "respostas_bpf",
    "respostas_entidade",
    "historico_fluxo",
    "notificacoes",
    "protocolos",
    "entidades",
    "alternativas_curso",
    "perguntas_curso",
    "curso_questionarios",
    "cursos",
    "perguntas_bpf",
    "perguntas_qualificacao",
    "owners_area",
    "usuarios",
]


def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def reset_sqlite(path: Path, admin_password: str):
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys=OFF")
    for table in TABLES:
        cur.execute(f"DELETE FROM {table}")
    placeholders = ",".join("?" for _ in TABLES)
    cur.execute(f"DELETE FROM sqlite_sequence WHERE name IN ({placeholders})", TABLES)
    cur.execute(
        """INSERT INTO usuarios(nome, usuario, senha_hash, perfil, email, senha_temporaria,
                  trocar_senha_obrigatorio, acesso_pendente, ativo)
           VALUES(?,?,?,?,?,?,?,?,?)""",
        ("Administrador", "admin", hash_pw(admin_password), "Administrador", "", 0, 0, 0, 1),
    )
    conn.commit()
    conn.close()


def reset_postgres(database_url: str, admin_password: str):
    import psycopg

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE " + ", ".join(TABLES) + " RESTART IDENTITY CASCADE")
            cur.execute(
                """INSERT INTO usuarios(nome, usuario, senha_hash, perfil, email, senha_temporaria,
                          trocar_senha_obrigatorio, acesso_pendente, ativo)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                ("Administrador", "admin", hash_pw(admin_password), "Administrador", "", False, False, False, True),
            )
        conn.commit()


def main():
    parser = argparse.ArgumentParser(description="Limpa dados do Sistema Bahia e deixa apenas o admin.")
    parser.add_argument("--target", choices=["sqlite", "postgres"], default="sqlite")
    parser.add_argument("--sqlite", default="bahia.db")
    parser.add_argument("--database-url", default=os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL"))
    parser.add_argument("--admin-password", default="admin123")
    args = parser.parse_args()

    if args.target == "sqlite":
        reset_sqlite(Path(args.sqlite), args.admin_password)
    else:
        if not args.database_url:
            raise SystemExit("Informe --database-url ou defina SUPABASE_DB_URL/DATABASE_URL.")
        reset_postgres(args.database_url, args.admin_password)
    print("Base limpa. Usuario admin recriado.")


if __name__ == "__main__":
    main()
