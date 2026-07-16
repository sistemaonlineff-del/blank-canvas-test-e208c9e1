import sqlite3
import os
import re
import base64
from pathlib import Path
from datetime import datetime
import hashlib
import html
import math
import mimetypes
import secrets
import smtplib
import string
import unicodedata
import zipfile
from email.message import EmailMessage
from typing import Optional

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
from course_catalog_sync import sync_course_catalog

APP_TITLE = "Governança e Qualificação de Demandas - Bahia"
DB_PATH = Path("bahia.db")
APP_DIR = Path(__file__).resolve().parent
ASSETS_DIR = APP_DIR / "assets"
STORAGE_DIR = APP_DIR / "storage"
OS_UPLOAD_DIR = STORAGE_DIR / "os"
OS_TEMPLATE_PATH = ASSETS_DIR / "Modelo_OS.docx"
LEGACY_OS_TEMPLATE_PATH = Path(r"C:\Users\fabio\Downloads\bahia\Modelo OS.docx")
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
DB_BACKEND = os.getenv("APP_DB_BACKEND", "sqlite").strip().lower()
USE_POSTGRES = DB_BACKEND == "postgres" and bool(SUPABASE_DB_URL)
AUTO_SEED_DEMO_DATA = False
NIVEIS = ["Básico", "Intermediário", "Avançado"]
AREAS_CURSO = ["CIMATEC", "SEBRAE"]
NATUREZAS_JURIDICAS = ["Associação", "Cooperativa", "Cooperativa Central"]
TIPOLOGIAS_BENEFICIARIOS = [
    "Agricultores Familiares",
    "Comunidades Tradicionais",
    "Assentados da Reforma Agrária",
    "Extrativistas",
]
COMUNIDADES_TRADICIONAIS = ["Quilombolas", "Indígenas", "Fundos e Fechos de Pastos", "Povos de Terreiro", "Outro"]
CLASSIFICACOES_ENTIDADE = ["Iniciante", "Intermediário", "Avançado"]
CERTIFICACOES_ENTIDADE = ["ADAB", "SIM", "SIM CONSÓRCIO", "SUSAF", "MAPA", "ANVISA", "DIVISA", "VIGILÂNCIA MUNICIPAL"]
LICENCAS_AMBIENTAIS = ["Sim", "Não", "Não se aplica"]
STATUS_FLUXO = [
    "Validação Administrativa",
    "Análise Técnica",
    "Agendamento",
    "Execução",
    "Finalizado",
    "Cancelado",
    "Reprovado",
]
ETAPAS_APROVACAO = ["Administrativo", "Técnico", "Agendamento", "Executor"]

st.set_page_config(page_title=APP_TITLE, layout="wide", initial_sidebar_state="expanded")
px.defaults.template = "plotly_white"
px.defaults.color_discrete_sequence = ["#2563EB", "#059669", "#D97706", "#7C3AED", "#DB2777", "#0891B2", "#4B5563"]

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root {
  --bg:#F4F7FB;
  --surface:#FFFFFF;
  --surface-soft:#F8FAFC;
  --surface-strong:#EAF1F8;
  --text:#111827;
  --muted:#4B5563;
  --muted-2:#64748B;
  --line:#D9E2EC;
  --primary:#2563EB;
  --primary-dark:#1E3A8A;
  --green:#047857;
  --green-soft:#D1FAE5;
  --orange:#B45309;
  --orange-soft:#FEF3C7;
  --red:#B91C1C;
  --red-soft:#FEE2E2;
  --purple:#6D28D9;
  --purple-soft:#EDE9FE;
  --cyan:#0E7490;
  --cyan-soft:#CFFAFE;
  --shadow:0 12px 34px rgba(15,23,42,.08);
  --shadow-hover:0 18px 46px rgba(15,23,42,.13);
  --radius:14px;
}
html, body, [class*="css"] {
  font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.stApp {
  background:
    linear-gradient(135deg, rgba(37,99,235,.09) 0%, rgba(5,150,105,.06) 32%, transparent 58%),
    linear-gradient(180deg, #FFFFFF 0%, var(--bg) 46%, #EEF3F8 100%);
  color: var(--text);
}
.block-container { padding-top: 1.25rem; padding-bottom: 3.25rem; max-width: 1440px; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer { display:none !important; visibility:hidden !important; }
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapseButton"],
button[title="Collapse sidebar"],
button[title="Expand sidebar"],
button[aria-label="Collapse sidebar"],
button[aria-label="Expand sidebar"] {
  display: none !important;
  visibility: hidden !important;
  pointer-events: none !important;
}
[data-testid="stSidebar"] {
  display:block;
  background: rgba(255,255,255,.94);
  backdrop-filter: blur(18px);
  border-right: 1px solid var(--line);
  box-shadow: 10px 0 32px rgba(15,23,42,.07);
}
[data-testid="stSidebar"] > div { padding-top: 1.1rem; }
h1 {
  color: var(--text);
  font-size: clamp(1.65rem, 1.2vw + 1.25rem, 2.35rem);
  font-weight: 800;
  letter-spacing: 0;
  margin: 0 0 1rem;
}
h2 { color: var(--text); font-size: 1.35rem; font-weight: 750; letter-spacing: 0; margin-top: 1.35rem; }
h3 { color: var(--text); font-size: 1.05rem; font-weight: 700; letter-spacing: 0; }
.stMarkdown p, .stCaptionContainer, label, [data-testid="stWidgetLabel"], [data-testid="stMarkdownContainer"] {
  color: var(--text);
}
.stCaptionContainer, [data-testid="stCaptionContainer"], .small-muted { color: var(--muted) !important; }
hr { border-color: var(--line); margin: 1.5rem 0; }
.bahia-card {
  background: rgba(255,255,255,.96);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 20px;
  box-shadow: var(--shadow);
  transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
}
.bahia-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-hover);
  border-color: rgba(37,99,235,.38);
}
.topbar {
  background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 58%, #047857 100%);
  border:1px solid rgba(255,255,255,.18);
  border-radius: 18px;
  padding: 18px 20px;
  margin-bottom: 22px;
  box-shadow: 0 18px 46px rgba(15,23,42,.16);
  backdrop-filter: blur(18px);
}
.topbar-title { font-size: 22px; font-weight: 800; color: #FFFFFF; letter-spacing:0; }
.topbar-subtitle { font-size: 13px; color: #DCEAFE; margin-top: 4px; font-weight: 600; }
.sidebar-brand {
  display:block; padding: 8px 4px 16px; border-bottom: 1px solid var(--line); margin-bottom: 14px;
}
.brand-mark {
  width:42px; height:42px; border-radius:13px; display:grid; place-items:center;
  background: linear-gradient(135deg, var(--primary), var(--green)); color:#fff; font-weight:800; box-shadow: 0 10px 24px rgba(37,99,235,.30);
}
.brand-logos {
  display:grid;
  grid-template-columns: 1fr 1fr;
  gap:10px;
  align-items:center;
  margin-bottom:12px;
}
.brand-logo-box {
  min-height:54px;
  border:1px solid var(--line);
  border-radius:12px;
  background:#FFFFFF;
  display:grid;
  place-items:center;
  padding:8px;
  color:var(--muted);
  font-size:11px;
  font-weight:800;
  letter-spacing:0;
}
.brand-logo-box img {
  max-width:100%;
  max-height:42px;
  object-fit:contain;
  display:block;
}
.login-shell {
  position: relative;
  padding: 28px 28px 0;
}
.login-hero-bar {
  width: min(1180px, 92vw);
  margin: 0 auto 42px;
  padding: 24px 30px;
  border-radius: 18px;
  background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 48%, #047857 100%);
  box-shadow: 0 24px 58px rgba(15,23,42,.18);
  color: #FFFFFF;
}
.login-hero-title {
  font-size: clamp(1.6rem, 1.4vw + 1.2rem, 2.4rem);
  line-height: 1.12;
  font-weight: 850;
  color: #FFFFFF;
  letter-spacing: 0;
}
.login-hero-subtitle {
  margin-top: 8px;
  font-size: 14px;
  font-weight: 650;
  color: #DCEAFE;
}
.login-card {
  width: min(460px, 92vw);
  margin: 0 auto;
  padding: 28px 30px 30px;
  border-radius: 16px;
  background: rgba(255,255,255,.82);
  border: 1px solid rgba(217,226,236,.92);
  box-shadow: 0 24px 60px rgba(15,23,42,.12);
  backdrop-filter: blur(16px);
}
.login-card h3 {
  margin-top: 0;
  margin-bottom: 8px;
}
.login-card [data-testid="stCaptionContainer"] {
  margin-bottom: 18px;
}
.login-logo {
  position: fixed;
  bottom: 28px;
  width: 148px;
  min-height: 72px;
  border-radius: 16px;
  border: 1px solid rgba(217,226,236,.95);
  background: rgba(255,255,255,.86);
  box-shadow: 0 18px 44px rgba(15,23,42,.10);
  display: grid;
  place-items: center;
  padding: 12px;
  color: var(--muted);
  font-size: 12px;
  font-weight: 850;
  z-index: 10;
}
.login-logo img {
  max-width: 100%;
  max-height: 54px;
  object-fit: contain;
}
.login-logo-1 { left: 34px; }
.login-logo-2 { right: 34px; }
@media (max-width: 760px) {
  .login-shell { padding: 18px 12px 112px; }
  .login-hero-bar { margin-bottom: 24px; padding: 20px; }
  .login-logo { width: 116px; min-height: 58px; bottom: 18px; }
  .login-logo-1 { left: 16px; }
  .login-logo-2 { right: 16px; }
}
.brand-title { font-weight:800; color:var(--text); line-height:1.1; }
.brand-subtitle { font-size:12px; color:var(--muted); margin-top:3px; }
.user-chip {
  background: var(--surface-soft); border:1px solid var(--line); border-radius:14px; padding:12px; margin: 8px 0 18px;
}
.avatar {
  width:34px; height:34px; border-radius:50%; background:linear-gradient(135deg,var(--green),var(--cyan));
  display:inline-grid; place-items:center; margin-right:8px; color:#FFFFFF; font-weight:800;
}
.kpi { font-size: 34px; font-weight: 800; color: var(--text); letter-spacing:-.03em; }
.kpi-label { color: var(--muted); font-size: 13px; font-weight: 600; margin-top: 4px; }
.badge {
  display:inline-flex; align-items:center; gap:6px; padding:6px 10px; border-radius:999px;
  color:var(--text); font-size:12px; font-weight:800; border:1px solid rgba(15,23,42,.08);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.65);
}
.badge:before { content:"•"; font-size:16px; line-height:0; }
.badge-blue { background:#DBEAFE; color:#1E3A8A; }
.badge-red { background:var(--red-soft); color:var(--red); }
.badge-yellow { background:var(--orange-soft); color:var(--orange); }
.badge-green { background:var(--green-soft); color:var(--green); }
.badge-gray { background:#E5E7EB; color:#374151; }
.small-muted { font-size:13px; }
div[data-testid="stForm"], div[data-testid="stExpander"], div[data-testid="stVerticalBlockBorderWrapper"] {
  border-color: var(--line) !important;
  border-radius: 14px !important;
  background: rgba(255,255,255,.96) !important;
  box-shadow: var(--shadow);
}
div[data-testid="stForm"], div[data-testid="stVerticalBlockBorderWrapper"] {
  max-width: 1180px;
  margin-left: auto !important;
  margin-right: auto !important;
  padding: 22px 26px !important;
}
div[data-testid="stForm"] h2, div[data-testid="stForm"] h3,
div[data-testid="stVerticalBlockBorderWrapper"] h2, div[data-testid="stVerticalBlockBorderWrapper"] h3 {
  text-align: center;
  margin-bottom: 1rem;
}
div[data-testid="stForm"] [data-testid="stWidgetLabel"],
div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stWidgetLabel"] {
  padding-left: 2px;
}
div[data-testid="stForm"] div[data-testid="stRadio"],
div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stRadio"] {
  width: 100%;
  max-width: 100%;
  margin-left: auto;
  margin-right: auto;
  text-align: center;
  padding: 4px 0 28px;
  display: grid !important;
  place-items: center !important;
}
.question-text {
  max-width: 900px;
  margin: 26px auto 12px;
  text-align: center;
  color: var(--text);
  font-weight: 800;
  line-height: 1.42;
}
.question-text-geral {
  margin-top: 34px;
  margin-bottom: 14px;
  max-width: 760px;
}
.options-title {
  text-align: center;
  font-weight: 800;
  color: var(--text);
  margin: 0 auto 12px;
}
div[data-testid="stForm"] div[data-testid="stRadio"] > label,
div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stRadio"] > label {
  justify-content: center;
  text-align: center;
  width: 100%;
  display: flex;
}
div[data-testid="stForm"] div[data-testid="stRadio"] > label p,
div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stRadio"] > label p {
  width: 100%;
  text-align: center;
  font-weight: 700;
  line-height: 1.35;
  margin: 0 auto 10px;
  max-width: 900px;
}
div[data-testid="stForm"] div[role="radiogroup"],
div[data-testid="stVerticalBlockBorderWrapper"] div[role="radiogroup"] {
  width: auto !important;
  max-width: 100%;
  display: inline-flex !important;
  justify-content: center;
  align-items: center;
  gap: 12px 18px;
  flex-wrap: nowrap;
  margin: 0 auto !important;
}
div[data-testid="stForm"] div[data-testid="stRadio"] > div,
div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stRadio"] > div {
  display: flex !important;
  justify-content: center !important;
  width: 100% !important;
}
div[data-testid="stForm"] div[role="radiogroup"] label,
div[data-testid="stVerticalBlockBorderWrapper"] div[role="radiogroup"] label {
  margin: 0 !important;
  justify-content: center;
  text-align: center;
}
div[data-testid="stForm"] div[role="radiogroup"] label > div,
div[data-testid="stVerticalBlockBorderWrapper"] div[role="radiogroup"] label > div {
  margin-right: 6px;
  flex: 0 0 auto;
}
div[data-testid="stForm"] div[role="radiogroup"] p,
div[data-testid="stVerticalBlockBorderWrapper"] div[role="radiogroup"] p {
  text-align: center;
  white-space: normal;
}
@media (max-width: 760px) {
  div[data-testid="stForm"], div[data-testid="stVerticalBlockBorderWrapper"] {
    padding: 16px !important;
  }
  div[data-testid="stForm"] div[role="radiogroup"],
  div[data-testid="stVerticalBlockBorderWrapper"] div[role="radiogroup"] {
    flex-wrap: wrap;
  }
}
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
  border-radius: 12px;
  border: 1px solid rgba(37,99,235,.30);
  background: linear-gradient(180deg, #FFFFFF 0%, #EAF2FF 100%);
  color: #0F172A !important;
  font-weight: 800;
  min-height: 42px;
  box-shadow: 0 8px 20px rgba(15,23,42,.06);
  transition: transform .16s ease, box-shadow .16s ease, border-color .16s ease, background .16s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {
  transform: translateY(-1px);
  border-color: var(--primary);
  background: linear-gradient(180deg, #FFFFFF 0%, #DDEBFF 100%);
  color: #0F172A !important;
  box-shadow: var(--shadow-hover);
}
.stButton > button *, .stDownloadButton > button *, .stFormSubmitButton > button * {
  color: inherit !important;
}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
  background: linear-gradient(135deg, var(--primary), var(--primary-dark));
  color: #FFFFFF !important;
}
div[data-baseweb="tab-list"] { gap: 8px; }
button[data-baseweb="tab"] {
  background: #FFFFFF;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 9px 16px;
  transition: transform .16s ease, background .16s ease, border-color .16s ease;
}
button[data-baseweb="tab"] p { color: var(--muted); font-weight: 750; }
button[data-baseweb="tab"][aria-selected="true"] {
  background: #DBEAFE;
  border-color: rgba(37,99,235,.45);
}
button[data-baseweb="tab"][aria-selected="true"] p { color: #1E3A8A; }
button[data-baseweb="tab"]:hover { transform: translateY(-1px); background:var(--surface-soft); border-color:rgba(37,99,235,.55); }
div[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius: 10px; overflow:hidden; }
input, textarea, [data-baseweb="select"] > div, [data-baseweb="input"] > div, [data-baseweb="textarea"] {
  border-radius: 12px !important;
  border-color: var(--line) !important;
  background: #FFFFFF !important;
  color: #111827 !important;
  transition: border-color .16s ease, box-shadow .16s ease, background .16s ease;
}
input::placeholder, textarea::placeholder { color:#6B7280 !important; opacity:1; }
div[data-baseweb="select"] span, div[data-baseweb="select"] div,
[data-baseweb="input"] input, [data-baseweb="textarea"] textarea {
  color: #111827 !important;
}
input:focus, textarea:focus, [data-baseweb="select"] > div:focus-within {
  border-color: var(--primary) !important;
  box-shadow: 0 0 0 4px rgba(37,99,235,.16) !important;
}
[data-testid="stMetric"] {
  background: var(--surface);
  border:1px solid var(--line);
  border-radius:14px;
  padding:16px;
  box-shadow:var(--shadow);
}
[data-testid="stMetricValue"] { color:var(--text); font-weight:800; }
[data-testid="stMetricLabel"] { color:var(--muted); font-weight:650; }
[data-testid="stDataFrame"] div { font-size: 13px; }
section[data-testid="stSidebar"] .stRadio > label { display:none; }
section[data-testid="stSidebar"] [role="radiogroup"] { gap: 6px; }
section[data-testid="stSidebar"] [role="radio"] {
  border-radius: 12px;
  padding: 10px 12px;
  color: #111827 !important;
  transition: background .16s ease, transform .16s ease;
}
section[data-testid="stSidebar"] [role="radio"]:hover {
  background: var(--surface-soft);
  transform: translateX(2px);
}
section[data-testid="stSidebar"] [role="radio"][aria-checked="true"] {
  background: #DBEAFE;
  color: #1E3A8A !important;
  font-weight: 800;
}
section[data-testid="stSidebar"] [role="radio"] * {
  color: inherit !important;
}
[data-testid="stAlert"] {
  border-radius: 12px;
  border: 1px solid var(--line);
  box-shadow: 0 8px 18px rgba(15,23,42,.05);
}
[data-testid="stAlert"] * { color: #111827 !important; }
[data-testid="stExpander"] details summary p { color: var(--text) !important; font-weight: 750; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def force_sidebar_expanded():
    components.html(
        """
        <script>
        const expandSidebar = () => {
          const doc = window.parent.document;
          const expandButton =
            doc.querySelector('[data-testid="collapsedControl"]') ||
            doc.querySelector('[data-testid="stSidebarCollapsedControl"]') ||
            doc.querySelector('button[title="Expand sidebar"]') ||
            doc.querySelector('button[aria-label="Expand sidebar"]');
          const sidebar = doc.querySelector('[data-testid="stSidebar"]');
          const sidebarHidden = !sidebar || sidebar.getAttribute('aria-expanded') === 'false';
          if (expandButton && sidebarHidden) {
            expandButton.click();
          }
        };
        expandSidebar();
        setTimeout(expandSidebar, 150);
        setTimeout(expandSidebar, 600);
        setTimeout(expandSidebar, 1200);
        </script>
        """,
        height=0,
        width=0,
    )


force_sidebar_expanded()


def pg_sql(sql: str) -> str:
    sql = sql.replace("?", "%s")
    sql = re.sub(r"(?<!SET\s)(\b(?:\w+\.)?ativo)\s*=\s*1\b", r"\1::text IN ('1','true')", sql, flags=re.IGNORECASE)
    sql = re.sub(r"(?<!SET\s)(\b(?:\w+\.)?ativo)\s*=\s*0\b", r"\1::text IN ('0','false')", sql, flags=re.IGNORECASE)
    replacements = {
        "enviado=1": "enviado=true",
        "enviado = 1": "enviado = true",
        "enviado=0": "enviado=false",
        "enviado = 0": "enviado = false",
        "enviado,data_criacao) VALUES(%s,%s,%s,%s,0,%s)": "enviado,data_criacao) VALUES(%s,%s,%s,%s,false,%s)",
        "estoque_total,ativo) VALUES(%s,%s,%s,%s,%s,%s,%s,1)": "estoque_total,ativo) VALUES(%s,%s,%s,%s,%s,%s,%s,true)",
        "MAX(pontos_1,pontos_2,pontos_3)": "GREATEST(COALESCE(pontos_1,0),COALESCE(pontos_2,0),COALESCE(pontos_3,0))",
    }
    for old, new in replacements.items():
        sql = sql.replace(old, new)
    return sql


def pg_params(params=()):
    if params is None:
        return None
    return tuple(params)


class PostgresCursor:
    def __init__(self, cursor):
        self.cursor = cursor
        self.lastrowid = None

    def execute(self, sql, params=None):
        sql_text = pg_sql(sql)
        is_insert = sql_text.lstrip().lower().startswith("insert into ")
        if is_insert and " returning " not in sql_text.lower():
            sql_text = f"{sql_text} RETURNING id"
        self.cursor.execute(sql_text, pg_params(params or ()))
        self.lastrowid = None
        if is_insert:
            row = self.cursor.fetchone()
            self.lastrowid = row[0] if row else None
        return self

    def executemany(self, sql, rows):
        self.cursor.executemany(pg_sql(sql), [pg_params(row) for row in rows])
        self.lastrowid = None
        return self

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()

    @property
    def rowcount(self):
        return self.cursor.rowcount


class PostgresConnection:
    def __init__(self):
        import psycopg
        self.raw = psycopg.connect(SUPABASE_DB_URL)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self.raw.rollback()
        self.raw.close()

    def cursor(self):
        return PostgresCursor(self.raw.cursor())

    def execute(self, sql, params=None):
        cur = self.cursor()
        return cur.execute(sql, params)

    def executemany(self, sql, rows):
        cur = self.cursor()
        return cur.executemany(sql, rows)

    def commit(self):
        self.raw.commit()

    def rollback(self):
        self.raw.rollback()


def conn():
    if USE_POSTGRES:
        return PostgresConnection()
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=NORMAL")
    c.execute("PRAGMA temp_store=MEMORY")
    c.execute("PRAGMA cache_size=-20000")
    return c


def q(sql, params=()):
    with conn() as c:
        if USE_POSTGRES:
            return pd.read_sql_query(pg_sql(sql), c.raw, params=pg_params(params))
        return pd.read_sql_query(sql, c, params=params)


def exec_sql(sql, params=()):
    with conn() as c:
        c.execute(sql, params)
        c.commit()


def exec_many(sql, rows):
    with conn() as c:
        c.executemany(sql, rows)
        c.commit()


EDITABLE_TABLES = {
    "Entidades": "entidades",
    "Cursos": "cursos",
    "Perguntas de Qualificação": "perguntas_qualificacao",
    "Perguntas BPF": "perguntas_bpf",
    "Perguntas Curso": "perguntas_curso",
    "Alternativas Curso": "alternativas_curso",
    "Responsáveis por Área": "owners_area",
    "Usuários": "usuarios",
    "Notificações": "notificacoes",
}


def table_columns(table: str) -> list[str]:
    if USE_POSTGRES:
        with conn() as c:
            cur = c.cursor()
            cur.execute(
                """SELECT column_name
                   FROM information_schema.columns
                   WHERE table_schema='public' AND table_name=%s
                   ORDER BY ordinal_position""",
                (table,),
            )
            return [r[0] for r in cur.fetchall()]
    with conn() as c:
        return [r[1] for r in c.execute(f"PRAGMA table_info({table})").fetchall()]


def db_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, bool):
        return 1 if value else 0
    return value


def save_table_editor(table: str, edited: pd.DataFrame, original: pd.DataFrame):
    cols = table_columns(table)
    editable_cols = [c for c in cols if c != "id"]
    original_by_id = {}
    if not original.empty and "id" in original.columns:
        original_by_id = {int(r["id"]): r for _, r in original.dropna(subset=["id"]).iterrows()}

    inserts = updates = 0
    with conn() as c:
        cur = c.cursor()
        for _, row in edited.iterrows():
            row_id = row.get("id") if "id" in edited.columns else None
            has_id = row_id is not None and not pd.isna(row_id)
            values = {col: db_value(row.get(col)) for col in editable_cols if col in edited.columns}
            if not any(v not in (None, "") for v in values.values()):
                continue
            if has_id and int(row_id) in original_by_id:
                original_row = original_by_id[int(row_id)]
                changed = [
                    col for col in values
                    if db_value(original_row.get(col)) != values[col]
                ]
                if changed:
                    set_clause = ", ".join(f"{col}=?" for col in changed)
                    params = [values[col] for col in changed] + [int(row_id)]
                    cur.execute(f"UPDATE {table} SET {set_clause} WHERE id=?", params)
                    updates += 1
            elif not has_id:
                insert_cols = [col for col, value in values.items() if value not in (None, "")]
                if insert_cols:
                    placeholders = ", ".join("?" for _ in insert_cols)
                    cur.execute(
                        f"INSERT INTO {table}({', '.join(insert_cols)}) VALUES({placeholders})",
                        [values[col] for col in insert_cols],
                    )
                    inserts += 1
        c.commit()
    return inserts, updates


def scalar(sql, params=(), default=0):
    with conn() as c:
        row = c.execute(sql, params).fetchone()
        return row[0] if row and row[0] is not None else default


def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def bool_db(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "t", "sim", "yes"}
    return bool(value)


def gerar_senha_temporaria(size: int = 10) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(size))


def usuario_por_login(login_value: str) -> pd.DataFrame:
    login_value = txt_value(login_value).lower()
    if not login_value:
        return pd.DataFrame()
    return q(
        "SELECT * FROM usuarios WHERE ativo=1 AND (LOWER(usuario)=? OR LOWER(email)=?) LIMIT 1",
        (login_value, login_value),
    )


def emails_moderadores() -> list[str]:
    df = q(
        "SELECT email FROM usuarios WHERE ativo=1 AND perfil IN ('Administrador','Moderador') AND email IS NOT NULL AND email<>''"
    )
    if df.empty:
        return []
    return sorted(set(txt_value(v) for v in df["email"].tolist() if txt_value(v)))


def registrar_email_sistema(protocolo: str, destinatario: str, assunto: str, corpo: str):
    registrar_notificacao(protocolo, destinatario, assunto, corpo)
    ok, erro = tentar_enviar_email(destinatario, assunto, corpo)
    if ok:
        exec_sql("UPDATE notificacoes SET enviado=1,data_envio=?,erro='' WHERE id=(SELECT MAX(id) FROM notificacoes)", (now_str(),))
    else:
        exec_sql("UPDATE notificacoes SET erro=? WHERE id=(SELECT MAX(id) FROM notificacoes)", (erro,))
    return ok, erro


def criar_usuario_pendente(email: str) -> tuple[str, str]:
    email = txt_value(email).lower()
    temp = gerar_senha_temporaria()
    data = now_str()
    exec_sql(
        """INSERT INTO usuarios(nome,usuario,email,senha_hash,perfil,senha_temporaria,trocar_senha_obrigatorio,acesso_pendente,data_solicitacao,ativo)
           VALUES(?,?,?,?,?,?,?,?,?,1)""",
        (email, email, email, hash_pw(temp), "Pendente", True, True, True, data),
    )
    assunto = "Senha temporária - Sistema Bahia"
    corpo = f"Olá.\n\nCriamos um acesso temporário para o Sistema Bahia.\n\nE-mail: {email}\nSenha temporária: {temp}\n\nAo entrar, cadastre uma nova senha."
    registrar_email_sistema(f"ACESSO-{email}", email, assunto, corpo)
    return temp, data


def notificar_moderadores_novo_usuario(user: dict):
    assunto = "Novo usuário aguardando nível de acesso"
    corpo = (
        "Um novo usuário concluiu o primeiro acesso e precisa de definição de nível de acesso.\n\n"
        f"Nome: {user.get('nome') or '-'}\n"
        f"Usuário: {user.get('usuario') or '-'}\n"
        f"E-mail: {user.get('email') or '-'}\n"
        f"Data: {now_str()}"
    )
    for email in emails_moderadores():
        registrar_email_sistema(f"ACESSO-{user.get('id')}", email, assunto, corpo)


def ensure_os_storage():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    OS_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    if not OS_TEMPLATE_PATH.exists() and LEGACY_OS_TEMPLATE_PATH.exists():
        OS_TEMPLATE_PATH.write_bytes(LEGACY_OS_TEMPLATE_PATH.read_bytes())


def safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", name or "arquivo")
    return cleaned.strip("._") or "arquivo"


def protocolo_slug(protocolo: str) -> str:
    return safe_filename(protocolo).replace(".", "_")


def file_download_bytes(path_value: str | Path):
    if path_value is None or (isinstance(path_value, float) and math.isnan(path_value)):
        return None
    path = Path(path_value) if str(path_value).strip() else None
    if not path or not path.exists() or not path.is_file():
        return None
    return path.read_bytes()


@st.cache_data(show_spinner=False)
def cached_file_bytes(path_value: str) -> bytes | None:
    path = Path(path_value)
    if not path.exists() or not path.is_file():
        return None
    return path.read_bytes()


@st.cache_data(show_spinner=False)
def asset_data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    data = base64.b64encode(cached_file_bytes(str(path)) or b"").decode("ascii")
    return f"data:{mime};base64,{data}"


@st.cache_data(show_spinner=False)
def find_logo_asset(index: int) -> Optional[Path]:
    for ext in ("png", "jpg", "jpeg", "webp", "svg"):
        candidate = ASSETS_DIR / f"logo_{index}.{ext}"
        if candidate.exists():
            return candidate
    return None


def logo_box(index: int) -> str:
    logo = find_logo_asset(index)
    if logo:
        return f'<div class="brand-logo-box"><img src="{asset_data_uri(logo)}" alt="Logo {index}"></div>'
    return f'<div class="brand-logo-box">LOGO {index}</div>'


def login_logo(index: int) -> str:
    logo = find_logo_asset(index)
    if logo:
        return f'<div class="login-logo login-logo-{index}"><img src="{asset_data_uri(logo)}" alt="Logo {index}"></div>'
    return f'<div class="login-logo login-logo-{index}">LOGO {index}</div>'


def texto_chave(value: str) -> str:
    normalizado = unicodedata.normalize("NFKD", txt_value(value))
    return normalizado.encode("ascii", "ignore").decode("ascii").lower().strip()


def os_disponivel_no_fluxo(status: str) -> bool:
    chave = texto_chave(status)
    if chave.startswith("valida") and "administrativa" in chave:
        return False
    if chave.startswith("anal") and "tecnica" in chave:
        return False
    return True


def protocolo_os_anexos(protocolo: str) -> list[tuple[Path, str]]:
    anexos: list[tuple[Path, str]] = []
    dados = q(
        "SELECT os_preenchida_path, os_preenchida_nome FROM protocolos WHERE protocolo=? LIMIT 1",
        (protocolo,),
    )
    if not dados.empty:
        path = dados.iloc[0].get("os_preenchida_path")
        nome = dados.iloc[0].get("os_preenchida_nome") or "OS_preenchida"
        if path and Path(path).exists():
            anexos.append((Path(path), str(nome)))
    return anexos


def ensure_protocolos_os_modelo():
    exec_sql(
        "UPDATE protocolos SET os_modelo_nome=?, os_modelo_path=? WHERE os_modelo_path IS NULL OR os_modelo_path=''",
        ("Modelo_OS.docx", str(OS_TEMPLATE_PATH)),
    )


def docx_escape(value) -> str:
    return html.escape(txt_value(value) or "-", quote=False)


def docx_paragraph(text: str, *, bold: bool = False, size: int = 22, align: str = "left", shade: str = "") -> str:
    bold_xml = "<w:b/>" if bold else ""
    jc_xml = f"<w:jc w:val=\"{align}\"/>" if align else ""
    shade_xml = f"<w:shd w:fill=\"{shade}\"/>" if shade else ""
    return (
        f"<w:p><w:pPr>{jc_xml}{shade_xml}<w:spacing w:after=\"120\"/></w:pPr><w:r><w:rPr>"
        f"{bold_xml}<w:sz w:val=\"{size}\"/>"
        "</w:rPr>"
        f"<w:t>{docx_escape(text)}</w:t>"
        "</w:r></w:p>"
    )


def docx_table(rows: list[list[str]]) -> str:
    table_rows = []
    for row_idx, row in enumerate(rows):
        cells = []
        for cell_idx, cell in enumerate(row):
            fill = "EAF2FF" if cell_idx == 0 else "FFFFFF"
            cells.append(
                "<w:tc><w:tcPr><w:tcW w:w=\"5000\" w:type=\"dxa\"/>"
                f"<w:shd w:fill=\"{fill}\"/><w:tcMar><w:top w:w=\"90\" w:type=\"dxa\"/><w:left w:w=\"120\" w:type=\"dxa\"/><w:bottom w:w=\"90\" w:type=\"dxa\"/><w:right w:w=\"120\" w:type=\"dxa\"/></w:tcMar>"
                "</w:tcPr>"
                f"{docx_paragraph(cell, bold=cell_idx == 0, size=21)}"
                "</w:tc>"
            )
        table_rows.append(f"<w:tr>{''.join(cells)}</w:tr>")
    return (
        "<w:tbl><w:tblPr><w:tblW w:w=\"0\" w:type=\"auto\"/>"
        "<w:tblBorders>"
        "<w:top w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"BFBFBF\"/>"
        "<w:left w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"BFBFBF\"/>"
        "<w:bottom w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"BFBFBF\"/>"
        "<w:right w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"BFBFBF\"/>"
        "<w:insideH w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"BFBFBF\"/>"
        "<w:insideV w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"BFBFBF\"/>"
        "</w:tblBorders></w:tblPr>"
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
  <w:body>
    {body_xml}
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="708" w:footer="708" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", content_types)
        docx.writestr("_rels/.rels", rels)
        docx.writestr("word/document.xml", document)


def gerar_os_preenchida(protocolo: str, usuario: dict, data_movimento: str, observacao: str = "") -> tuple[Path, str] | tuple[None, None]:
    dados = q(
        """SELECT p.*, e.entidade, e.cnpj, e.email_responsavel, e.municipio_entidade,
                  e.territorio_identidade, e.endereco, e.telefone, c.curso
           FROM protocolos p
           LEFT JOIN entidades e ON e.id=p.entidade_id
           LEFT JOIN cursos c ON c.id=p.curso_id
           WHERE p.protocolo=?
           LIMIT 1""",
        (protocolo,),
    )
    if dados.empty:
        return None, None

    row = dados.iloc[0]
    ensure_os_storage()
    numero_os = f"OS-{datetime.now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(2).upper()}"
    data_br = datetime.now().strftime("%d/%m/%Y")
    solicitante = txt_value(usuario.get("nome")) or txt_value(usuario.get("usuario"))
    contato = txt_value(usuario.get("email")) or txt_value(usuario.get("usuario"))
    funcao = txt_value(usuario.get("perfil")) or "Analista Técnico"
    entidade = txt_value(row.get("entidade"))
    filename = f"{protocolo_slug(protocolo)}_{numero_os}.docx"
    destino = OS_UPLOAD_DIR / filename

    body = []
    body.append(docx_paragraph("ORDEM DE SERVIÇO", bold=True, size=32, align="center"))
    body.append(docx_paragraph("Governança e Qualificação de Demandas - Bahia", bold=True, size=22, align="center"))
    body.append(docx_section("1. IDENTIFICAÇÃO DA ORDEM DE SERVIÇO"))
    body.append(
        docx_table(
            [
                [f"Número da OS: {numero_os}", f"Data de Abertura: {data_br}"],
                ["Status: ( ) Aberta  ( ) Aprovada  ( X ) Agendamento  ( ) Em Execução  ( ) Concluída  ( ) Cancelada", ""],
                [f"Origem da Demanda: {entidade}", f"Número do Protocolo da Demanda: {protocolo}"],
            ]
        )
    )
    body.append(docx_section("2. DADOS DA ORGANIZAÇÃO PRODUTIVA"))
    body.append(
        docx_table(
            [
                [f"Nome da Organização: {entidade}", f"CNPJ/CPF: {row.get('cnpj') or '-'}"],
                [f"Município: {row.get('municipio_entidade') or '-'}", f"Território: {row.get('territorio_identidade') or '-'}"],
                [f"Responsável Local: {row.get('email_responsavel') or '-'}", f"E-mail: {row.get('email_responsavel') or '-'}"],
                [f"Endereço: {row.get('endereco') or '-'}", f"Telefone/WhatsApp: {row.get('telefone') or '-'}"],
            ]
        )
    )
    body.append(docx_section("3. SOLICITANTE DA DEMANDA"))
    body.append(
        docx_table(
            [
                [f"Nome do Coordenador/Demandante: {solicitante}", f"Função: {funcao}"],
                [f"Contato: {contato}", f"Data da Solicitação: {data_br}"],
            ]
        )
    )
    body.append(docx_section("4. DADOS DA DEMANDA"))
    body.append(
        docx_table(
            [
                [f"Curso/Solução: {row.get('curso') or '-'}", f"Área: {row.get('area') or '-'}"],
                [f"Observação da análise técnica: {observacao or '-'}", ""],
            ]
        )
    )
    write_simple_docx(destino, "".join(body))
    data = now_str()
    exec_sql(
        """UPDATE protocolos
           SET os_preenchida_nome=?, os_preenchida_path=?, os_preenchida_em=?, os_preenchida_por=?
           WHERE protocolo=?""",
        (filename, str(destino), data, usuario.get("usuario", ""), protocolo),
    )
    return destino, filename


def add_column_if_missing(cur, table: str, column: str, definition: str):
    cols = [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def ensure_postgres_schema():
    ddl = """
    CREATE TABLE IF NOT EXISTS usuarios (
        id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        nome text,
        usuario text UNIQUE,
        senha_hash text,
        perfil text,
        email text,
        senha_temporaria boolean DEFAULT false,
        trocar_senha_obrigatorio boolean DEFAULT false,
        acesso_pendente boolean DEFAULT false,
        data_solicitacao text,
        ativo boolean DEFAULT true
    );
    CREATE TABLE IF NOT EXISTS entidades (
        id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        entidade text,
        cnpj text,
        responsavel text,
        email_responsavel text,
        area text,
        caa text,
        can text,
        atep text,
        agente_negocio text,
        numero_convenio text,
        an_atep_ateg text,
        nome_ateg text,
        coordenador_tipo text,
        nome_coordenador text,
        natureza_juridica text,
        dap_caf text,
        territorio_identidade text,
        tipologia_beneficiarios text,
        comunidade_tradicional text,
        ativa_dinamica text,
        municipio_entidade text,
        classificacao text,
        certificacao text,
        licenca_ambiental text,
        telefone text,
        endereco text,
        status_qualificacao text DEFAULT 'BPF pendente',
        nivel text,
        pontuacao integer,
        pontuacao_q1 integer DEFAULT 0,
        pontuacao_q2 integer DEFAULT 0,
        data_cadastro text,
        cadastrado_por text,
        cadastrado_por_email text,
        ativo boolean DEFAULT true
    );
    CREATE TABLE IF NOT EXISTS perguntas_qualificacao (
        id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        id_externo text,
        questionario text,
        ordem integer,
        pergunta text,
        tipo text,
        opcao_1 text,
        opcao_2 text,
        opcao_3 text,
        pontos_1 integer DEFAULT 0,
        pontos_2 integer DEFAULT 5,
        pontos_3 integer DEFAULT 10,
        pontos_sim integer DEFAULT 1,
        ativo boolean DEFAULT true
    );
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
        ativo boolean DEFAULT true
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
        ativo boolean DEFAULT true
    );
    CREATE TABLE IF NOT EXISTS respostas_bpf (
        id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        entidade_id bigint,
        pergunta_id bigint,
        pergunta text,
        resposta text,
        pontuacao integer,
        data_resposta text
    );
    CREATE TABLE IF NOT EXISTS curso_questionarios (
        id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        curso_id bigint,
        id_questionario text,
        nome_questionario text,
        ativo boolean DEFAULT true
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
        ativo boolean DEFAULT true
    );
    CREATE TABLE IF NOT EXISTS perguntas_curso (
        id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        curso_id bigint,
        id_pergunta text,
        id_questionario text,
        questionario text,
        ordem integer,
        pergunta text,
        pontos_sim integer DEFAULT 1,
        ativo boolean DEFAULT true
    );
    CREATE TABLE IF NOT EXISTS protocolos (
        id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        protocolo text UNIQUE,
        entidade_id bigint,
        curso_id bigint,
        area text,
        pontuacao_curso integer,
        status text,
        etapa_atual text,
        responsavel_atual text,
        solicitante_nome text,
        solicitante_email text,
        data_abertura text,
        data_atualizacao text,
        data_agendada text,
        observacao text,
        os_modelo_nome text,
        os_modelo_path text,
        os_preenchida_nome text,
        os_preenchida_path text,
        os_preenchida_em text,
        os_preenchida_por text
    );
    CREATE TABLE IF NOT EXISTS respostas_entidade (
        id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        entidade_id bigint,
        questionario text,
        pergunta_id bigint,
        pergunta text,
        resposta text,
        pontuacao integer,
        data_resposta text
    );
    CREATE TABLE IF NOT EXISTS respostas_curso (
        id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        protocolo text,
        pergunta_id bigint,
        pergunta text,
        resposta text,
        pontuacao integer,
        data_resposta text
    );
    CREATE TABLE IF NOT EXISTS owners_area (
        id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        area text,
        etapa text,
        nome text,
        email text,
        usuario text,
        ativo boolean DEFAULT true
    );
    CREATE TABLE IF NOT EXISTS historico_fluxo (
        id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        protocolo text,
        status_anterior text,
        status_novo text,
        usuario text,
        data_movimento text,
        observacao text
    );
    CREATE TABLE IF NOT EXISTS notificacoes (
        id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        protocolo text,
        destinatario text,
        assunto text,
        corpo text,
        enviado boolean DEFAULT false,
        data_criacao text,
        data_envio text,
        erro text
    );
    CREATE TABLE IF NOT EXISTS importacoes_sistema (
        id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        chave text UNIQUE,
        arquivo text,
        hash_arquivo text,
        data_atualizacao text
    );
    ALTER TABLE cursos ADD COLUMN IF NOT EXISTS campo_link text;
    ALTER TABLE cursos ADD COLUMN IF NOT EXISTS id_questionario text;
    ALTER TABLE cursos ADD COLUMN IF NOT EXISTS questionario text;
    ALTER TABLE cursos ADD COLUMN IF NOT EXISTS status_mapeamento text;
    ALTER TABLE cursos ADD COLUMN IF NOT EXISTS descricao text;
    ALTER TABLE cursos ADD COLUMN IF NOT EXISTS carga_horaria text;
    ALTER TABLE cursos ADD COLUMN IF NOT EXISTS owner_email text;
    ALTER TABLE cursos ADD COLUMN IF NOT EXISTS estoque_total integer DEFAULT 0;
    ALTER TABLE cursos ADD COLUMN IF NOT EXISTS ativo boolean DEFAULT true;
    ALTER TABLE perguntas_curso ADD COLUMN IF NOT EXISTS id_pergunta text;
    ALTER TABLE perguntas_curso ADD COLUMN IF NOT EXISTS id_questionario text;
    ALTER TABLE perguntas_curso ADD COLUMN IF NOT EXISTS questionario text;
    ALTER TABLE alternativas_curso ADD COLUMN IF NOT EXISTS id_alternativa text;
    ALTER TABLE alternativas_curso ADD COLUMN IF NOT EXISTS id_pergunta text;
    ALTER TABLE alternativas_curso ADD COLUMN IF NOT EXISTS id_questionario text;
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS status_qualificacao text DEFAULT 'BPF pendente';
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS cnpj text;
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS responsavel text;
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS email_responsavel text;
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS caa text;
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS can text;
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS atep text;
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS agente_negocio text;
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS numero_convenio text;
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS an_atep_ateg text;
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS nome_ateg text;
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS coordenador_tipo text;
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS nome_coordenador text;
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS natureza_juridica text;
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS dap_caf text;
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS territorio_identidade text;
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS tipologia_beneficiarios text;
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS comunidade_tradicional text;
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS ativa_dinamica text;
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS municipio_entidade text;
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS classificacao text;
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS certificacao text;
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS licenca_ambiental text;
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS telefone text;
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS endereco text;
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS nivel text;
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS pontuacao integer;
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS pontuacao_q1 integer DEFAULT 0;
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS pontuacao_q2 integer DEFAULT 0;
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS data_cadastro text;
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS cadastrado_por text;
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS cadastrado_por_email text;
    ALTER TABLE entidades ADD COLUMN IF NOT EXISTS ativo boolean DEFAULT true;
    ALTER TABLE entidades ALTER COLUMN area DROP NOT NULL;
    ALTER TABLE entidades ALTER COLUMN nivel DROP NOT NULL;
    ALTER TABLE entidades ALTER COLUMN pontuacao DROP NOT NULL;
    ALTER TABLE entidades DROP CONSTRAINT IF EXISTS entidades_nivel_check;
    ALTER TABLE entidades ADD CONSTRAINT entidades_nivel_check
        CHECK (
            nivel IS NULL OR nivel IN (
                'Básico', 'Intermediário', 'Avançado',
                'Basico', 'Intermediario', 'Avancado',
                'BÃ¡sico', 'IntermediÃ¡rio', 'AvanÃ§ado'
            )
        );
    ALTER TABLE historico_fluxo DROP CONSTRAINT IF EXISTS historico_fluxo_protocolo_fkey;
    ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS email text;
    ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS senha_temporaria boolean DEFAULT false;
    ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS trocar_senha_obrigatorio boolean DEFAULT false;
    ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS acesso_pendente boolean DEFAULT false;
    ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS data_solicitacao text;
    ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS ativo boolean DEFAULT true;
    ALTER TABLE protocolos ADD COLUMN IF NOT EXISTS area text;
    ALTER TABLE protocolos ADD COLUMN IF NOT EXISTS etapa_atual text;
    ALTER TABLE protocolos ADD COLUMN IF NOT EXISTS solicitante_nome text;
    ALTER TABLE protocolos ADD COLUMN IF NOT EXISTS solicitante_email text;
    ALTER TABLE protocolos ADD COLUMN IF NOT EXISTS data_agendada text;
    ALTER TABLE protocolos ADD COLUMN IF NOT EXISTS os_modelo_nome text;
    ALTER TABLE protocolos ADD COLUMN IF NOT EXISTS os_modelo_path text;
    ALTER TABLE protocolos ADD COLUMN IF NOT EXISTS os_preenchida_nome text;
    ALTER TABLE protocolos ADD COLUMN IF NOT EXISTS os_preenchida_path text;
    ALTER TABLE protocolos ADD COLUMN IF NOT EXISTS os_preenchida_em text;
    ALTER TABLE protocolos ADD COLUMN IF NOT EXISTS os_preenchida_por text;
    """
    with conn() as c:
        cur = c.cursor()
        cur.cursor.execute(ddl)
        c.commit()


def ensure_db_indexes():
    sqlite_indexes = [
        "CREATE INDEX IF NOT EXISTS idx_usuarios_login ON usuarios(usuario, email, ativo)",
        "CREATE INDEX IF NOT EXISTS idx_entidades_status_ativo ON entidades(status_qualificacao, ativo)",
        "CREATE INDEX IF NOT EXISTS idx_entidades_nivel_ativo ON entidades(nivel, ativo)",
        "CREATE INDEX IF NOT EXISTS idx_entidades_cadastrado_por ON entidades(cadastrado_por, cadastrado_por_email)",
        "CREATE INDEX IF NOT EXISTS idx_protocolos_status ON protocolos(status)",
        "CREATE INDEX IF NOT EXISTS idx_protocolos_entidade ON protocolos(entidade_id)",
        "CREATE INDEX IF NOT EXISTS idx_protocolos_curso_status ON protocolos(curso_id, status)",
        "CREATE INDEX IF NOT EXISTS idx_historico_protocolo ON historico_fluxo(protocolo, id)",
        "CREATE INDEX IF NOT EXISTS idx_respostas_entidade ON respostas_entidade(entidade_id, id)",
        "CREATE INDEX IF NOT EXISTS idx_respostas_bpf ON respostas_bpf(entidade_id, id)",
        "CREATE INDEX IF NOT EXISTS idx_respostas_curso ON respostas_curso(protocolo, id)",
        "CREATE INDEX IF NOT EXISTS idx_cursos_area_nivel ON cursos(area, nivel, ativo)",
        "CREATE INDEX IF NOT EXISTS idx_perguntas_qualificacao ON perguntas_qualificacao(ativo, questionario, ordem)",
        "CREATE INDEX IF NOT EXISTS idx_perguntas_bpf ON perguntas_bpf(ativo, secao, subsecao, ordem)",
        "CREATE INDEX IF NOT EXISTS idx_perguntas_curso ON perguntas_curso(curso_id, ativo, ordem)",
        "CREATE INDEX IF NOT EXISTS idx_alternativas_curso ON alternativas_curso(pergunta_id, ativo, ordem)",
        "CREATE INDEX IF NOT EXISTS idx_owners_area_etapa ON owners_area(area, etapa, ativo)",
    ]
    with conn() as c:
        cur = c.cursor()
        for sql in sqlite_indexes:
            cur.execute(sql)
        c.commit()


def init_db():
    ensure_os_storage()
    if USE_POSTGRES:
        ensure_postgres_schema()
        ensure_db_indexes()
        ensure_protocolos_os_modelo()
        if scalar("SELECT COUNT(*) FROM usuarios", default=0) == 0:
            exec_many(
                "INSERT INTO usuarios(nome,usuario,senha_hash,perfil,email) VALUES(?,?,?,?,?)",
                [
                    ("Administrador", "admin", hash_pw("admin123"), "Administrador", ""),
                ],
            )
        with conn() as c:
            sync_course_catalog(c, APP_DIR, USE_POSTGRES)
            c.commit()
        return
    with conn() as c:
        cur = c.cursor()
        cur.executescript("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            usuario TEXT UNIQUE,
            senha_hash TEXT,
            perfil TEXT,
            email TEXT,
            senha_temporaria INTEGER DEFAULT 0,
            trocar_senha_obrigatorio INTEGER DEFAULT 0,
            acesso_pendente INTEGER DEFAULT 0,
            data_solicitacao TEXT,
            ativo INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS entidades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entidade TEXT,
            cnpj TEXT,
            responsavel TEXT,
            email_responsavel TEXT,
            area TEXT,
            caa TEXT,
            can TEXT,
            atep TEXT,
            agente_negocio TEXT,
            numero_convenio TEXT,
            an_atep_ateg TEXT,
            nome_ateg TEXT,
            coordenador_tipo TEXT,
            nome_coordenador TEXT,
            natureza_juridica TEXT,
            dap_caf TEXT,
            territorio_identidade TEXT,
            tipologia_beneficiarios TEXT,
            comunidade_tradicional TEXT,
            ativa_dinamica TEXT,
            municipio_entidade TEXT,
            classificacao TEXT,
            certificacao TEXT,
            licenca_ambiental TEXT,
            telefone TEXT,
            endereco TEXT,
            status_qualificacao TEXT DEFAULT 'BPF pendente',
            nivel TEXT,
            pontuacao INTEGER,
            pontuacao_q1 INTEGER DEFAULT 0,
            pontuacao_q2 INTEGER DEFAULT 0,
            data_cadastro TEXT,
            cadastrado_por TEXT,
            cadastrado_por_email TEXT,
            ativo INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS perguntas_qualificacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_externo TEXT,
            questionario TEXT DEFAULT 'Questionário 1',
            ordem INTEGER,
            pergunta TEXT,
            tipo TEXT DEFAULT 'Sim/Não',
            opcao_1 TEXT,
            opcao_2 TEXT,
            opcao_3 TEXT,
            pontos_1 INTEGER DEFAULT 0,
            pontos_2 INTEGER DEFAULT 5,
            pontos_3 INTEGER DEFAULT 10,
            pontos_sim INTEGER DEFAULT 1,
            ativo INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS cursos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            curso TEXT,
            area TEXT,
            nivel TEXT,
            campo_link TEXT,
            id_questionario TEXT,
            questionario TEXT,
            status_mapeamento TEXT,
            descricao TEXT,
            carga_horaria TEXT,
            owner_email TEXT,
            estoque_total INTEGER DEFAULT 0,
            ativo INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS perguntas_bpf (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            secao TEXT,
            subsecao TEXT,
            codigo_pergunta TEXT,
            ordem INTEGER,
            pergunta TEXT,
            tipo_resposta TEXT DEFAULT 'Multipla',
            opcoes TEXT DEFAULT 'S;N;P;NA',
            pontos_sim INTEGER DEFAULT 1,
            ativo INTEGER DEFAULT 1
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
        CREATE TABLE IF NOT EXISTS curso_questionarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            curso_id INTEGER,
            id_questionario TEXT,
            nome_questionario TEXT,
            ativo INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS alternativas_curso (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pergunta_id INTEGER,
            id_alternativa TEXT,
            id_pergunta TEXT,
            id_questionario TEXT,
            ordem INTEGER,
            alternativa TEXT,
            pontos INTEGER DEFAULT 0,
            ativo INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS perguntas_curso (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            curso_id INTEGER,
            id_pergunta TEXT,
            id_questionario TEXT,
            questionario TEXT,
            ordem INTEGER,
            pergunta TEXT,
            pontos_sim INTEGER DEFAULT 1,
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
            os_modelo_nome TEXT,
            os_modelo_path TEXT,
            os_preenchida_nome TEXT,
            os_preenchida_path TEXT,
            os_preenchida_em TEXT,
            os_preenchida_por TEXT
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
        CREATE TABLE IF NOT EXISTS importacoes_sistema (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chave TEXT UNIQUE,
            arquivo TEXT,
            hash_arquivo TEXT,
            data_atualizacao TEXT
        );
        """)
        # Migração para bancos antigos
        for table, cols in {
            "usuarios": [
                ("email", "TEXT"),
                ("senha_temporaria", "INTEGER DEFAULT 0"),
                ("trocar_senha_obrigatorio", "INTEGER DEFAULT 0"),
                ("acesso_pendente", "INTEGER DEFAULT 0"),
                ("data_solicitacao", "TEXT"),
            ],
            "entidades": [
                ("cnpj", "TEXT"), ("responsavel", "TEXT"), ("email_responsavel", "TEXT"),
                ("pontuacao_q1", "INTEGER DEFAULT 0"), ("pontuacao_q2", "INTEGER DEFAULT 0"),
                ("cadastrado_por", "TEXT"), ("cadastrado_por_email", "TEXT"), ("ativo", "INTEGER DEFAULT 1"),
                ("an_atep_ateg", "TEXT"), ("nome_ateg", "TEXT"), ("coordenador_tipo", "TEXT"),
                ("nome_coordenador", "TEXT"), ("natureza_juridica", "TEXT"), ("dap_caf", "TEXT"),
                ("territorio_identidade", "TEXT"), ("tipologia_beneficiarios", "TEXT"),
                ("comunidade_tradicional", "TEXT"), ("ativa_dinamica", "TEXT"),
                ("municipio_entidade", "TEXT"), ("classificacao", "TEXT"),
                ("certificacao", "TEXT"), ("licenca_ambiental", "TEXT"),
                ("telefone", "TEXT"), ("endereco", "TEXT"),
                ("status_qualificacao", "TEXT DEFAULT 'BPF pendente'"),
            ],
            "perguntas_qualificacao": [
                ("id_externo", "TEXT"), ("questionario", "TEXT DEFAULT 'Questionário 1'"),
                ("tipo", "TEXT DEFAULT 'Sim/Não'"), ("opcao_1", "TEXT"), ("opcao_2", "TEXT"),
                ("opcao_3", "TEXT"), ("pontos_1", "INTEGER DEFAULT 0"),
                ("pontos_2", "INTEGER DEFAULT 5"), ("pontos_3", "INTEGER DEFAULT 10"),
            ],
            "perguntas_bpf": [
                ("secao", "TEXT"), ("subsecao", "TEXT"), ("codigo_pergunta", "TEXT"),
                ("tipo_resposta", "TEXT DEFAULT 'Multipla'"), ("opcoes", "TEXT DEFAULT 'S;N;P;NA'"),
            ],
            "cursos": [
                ("descricao", "TEXT"), ("carga_horaria", "TEXT"), ("owner_email", "TEXT"),
                ("estoque_total", "INTEGER DEFAULT 0"), ("campo_link", "TEXT"),
                ("id_questionario", "TEXT"), ("questionario", "TEXT"), ("status_mapeamento", "TEXT"),
            ],
            "perguntas_curso": [("id_pergunta", "TEXT"), ("id_questionario", "TEXT"), ("questionario", "TEXT")],
            "alternativas_curso": [("id_alternativa", "TEXT"), ("id_pergunta", "TEXT"), ("id_questionario", "TEXT")],
            "protocolos": [
                ("area", "TEXT"), ("etapa_atual", "TEXT"), ("solicitante_nome", "TEXT"),
                ("solicitante_email", "TEXT"), ("data_agendada", "TEXT"),
                ("os_modelo_nome", "TEXT"), ("os_modelo_path", "TEXT"),
                ("os_preenchida_nome", "TEXT"), ("os_preenchida_path", "TEXT"),
                ("os_preenchida_em", "TEXT"), ("os_preenchida_por", "TEXT"),
            ],
        }.items():
            for col, definition in cols:
                add_column_if_missing(cur, table, col, definition)

        cur.execute("UPDATE cursos SET area='CIMATEC' WHERE area='SEMATEC'")
        cur.execute("UPDATE protocolos SET os_modelo_nome=?, os_modelo_path=? WHERE os_modelo_path IS NULL OR os_modelo_path=''", ("Modelo_OS.docx", str(OS_TEMPLATE_PATH)))
        cur.execute("UPDATE usuarios SET nome='Administrador', perfil='Administrador', ativo=1, acesso_pendente=0 WHERE usuario='admin'")
        cur.execute("UPDATE cursos SET estoque_total=10 WHERE estoque_total IS NULL OR estoque_total=0")
        cur.execute("UPDATE entidades SET status_qualificacao='Concluída' WHERE status_qualificacao IS NULL AND nivel IS NOT NULL")

        if cur.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] == 0:
            base_users = [
                ("Administrador", "admin", hash_pw("admin123"), "Administrador", ""),
            ]
            cur.executemany("INSERT INTO usuarios(nome,usuario,senha_hash,perfil,email) VALUES(?,?,?,?,?)", base_users)

        if AUTO_SEED_DEMO_DATA and cur.execute("SELECT COUNT(*) FROM perguntas_qualificacao").fetchone()[0] == 0:
            perguntas = [
                ("Questionário 1", 1, "A entidade possui equipe responsável pela execução das demandas?", 5),
                ("Questionário 1", 2, "A entidade possui documentação regularizada?", 5),
                ("Questionário 1", 3, "A entidade possui estrutura física mínima para atendimento?", 5),
                ("Questionário 1", 4, "A entidade possui responsável formal pelo acompanhamento?", 5),
                ("Questionário 2", 1, "A entidade possui histórico de participação em projetos anteriores?", 5),
                ("Questionário 2", 2, "A entidade possui capacidade de mobilização do público-alvo?", 5),
                ("Questionário 2", 3, "A entidade possui indicadores ou registros de acompanhamento?", 5),
                ("Questionário 2", 4, "A entidade possui experiência em ações de capacitação?", 5),
            ]
            cur.executemany("INSERT INTO perguntas_qualificacao(questionario,ordem,pergunta,pontos_sim) VALUES(?,?,?,?)", perguntas)

        if AUTO_SEED_DEMO_DATA and cur.execute("SELECT COUNT(*) FROM cursos").fetchone()[0] == 0:
            cursos = [
                ("Gestão Básica de Demandas", "SEBRAE", "Básico", "Curso introdutório para organização de demandas.", "8h", "", 10),
                ("Planejamento e Controle", "SEBRAE", "Intermediário", "Planejamento, acompanhamento e controle operacional.", "12h", "", 10),
                ("Governança Avançada", "SEBRAE", "Avançado", "Governança, indicadores e gestão avançada.", "16h", "", 10),
                ("Introdução à Tecnologia", "CIMATEC", "Básico", "Fundamentos de tecnologia e inovação.", "8h", "", 10),
                ("Gestão de Projetos Tecnológicos", "CIMATEC", "Intermediário", "Projetos, escopo, prazo e entregáveis técnicos.", "12h", "", 10),
                ("Inovação e Dados", "CIMATEC", "Avançado", "Uso de dados, inovação e melhoria contínua.", "16h", "", 10),
            ]
            cur.executemany("INSERT INTO cursos(curso,area,nivel,descricao,carga_horaria,owner_email,estoque_total) VALUES(?,?,?,?,?,?,?)", cursos)

        if AUTO_SEED_DEMO_DATA and cur.execute("SELECT COUNT(*) FROM perguntas_bpf").fetchone()[0] == 0:
            perguntas_bpf = [
                (1, "A entidade possui boas práticas formalizadas de gestão?", 5),
                (2, "A entidade mantém registros atualizados de atendimento e execução?", 5),
                (3, "A entidade possui rotina de prestação de contas?", 5),
                (4, "A entidade possui governança mínima para receber novas soluções?", 5),
            ]
            cur.executemany("INSERT INTO perguntas_bpf(ordem,pergunta,pontos_sim) VALUES(?,?,?)", perguntas_bpf)

        if AUTO_SEED_DEMO_DATA and cur.execute("SELECT COUNT(*) FROM perguntas_curso").fetchone()[0] == 0:
            ids = cur.execute("SELECT id FROM cursos").fetchall()
            perguntas_curso = []
            for (cid,) in ids:
                perguntas_curso += [
                    (cid, 1, "A demanda possui objetivo claro?", 5),
                    (cid, 2, "Existe público-alvo definido?", 5),
                    (cid, 3, "A execução possui prazo viável?", 5),
                    (cid, 4, "A entidade possui responsável disponível para acompanhar o curso?", 5),
                ]
            cur.executemany("INSERT INTO perguntas_curso(curso_id,ordem,pergunta,pontos_sim) VALUES(?,?,?,?)", perguntas_curso)

        if AUTO_SEED_DEMO_DATA and cur.execute("SELECT COUNT(*) FROM owners_area").fetchone()[0] == 0:
            owners = []
            for area in AREAS_CURSO:
                owners += [
                    (area, "Administrativo", "Owner Administrativo", "", "administrativo"),
                    (area, "Técnico", "Owner Técnico", "", "tecnico"),
                    (area, "Agendamento", "Owner Agendamento", "", "agendamento"),
                    (area, "Executor", "Owner Execução", "", "executor"),
                ]
            cur.executemany("INSERT INTO owners_area(area,etapa,nome,email,usuario) VALUES(?,?,?,?,?)", owners)
        c.commit()
    ensure_db_indexes()
    with conn() as c:
        sync_course_catalog(c, APP_DIR, USE_POSTGRES)
        c.commit()


def nivel_por_pontos(p: int) -> str:
    max_pontos = int(scalar("SELECT COALESCE(SUM(MAX(pontos_1,pontos_2,pontos_3)),0) FROM perguntas_qualificacao WHERE ativo=1", default=0))
    if max_pontos >= 100:
        if p <= math.floor(max_pontos * 0.35):
            return "Básico"
        if p <= math.floor(max_pontos * 0.70):
            return "Intermediário"
        return "Avançado"
    if p <= 20:
        return "Básico"
    if p <= 35:
        return "Intermediário"
    return "Avançado"


def niveis_permitidos(nivel: str):
    return {
        "Básico": ["Básico"],
        "Intermediário": ["Básico", "Intermediário"],
        "Avançado": ["Básico", "Intermediário", "Avançado"],
    }.get(nivel, ["Básico"])


def estoque_em_uso(curso_id: int) -> int:
    return int(scalar(
        """SELECT COUNT(*) FROM protocolos
           WHERE curso_id=? AND status NOT IN ('Cancelado','Reprovado')""",
        (curso_id,),
    ))


def estoque_disponivel(curso_id: int, estoque_total: int) -> int:
    return max(int(estoque_total or 0) - estoque_em_uso(curso_id), 0)


def render_perguntas_sim_nao(perguntas: pd.DataFrame, prefixo: str) -> dict:
    respostas = {}
    for _, r in perguntas.iterrows():
        respostas[int(r.id)] = st.radio(r.pergunta, ["Não", "Sim"], horizontal=True, key=f"{prefixo}_{int(r.id)}")
    return respostas


def pontuar_sim_nao(perguntas: pd.DataFrame, respostas: dict) -> int:
    return sum(int(r.pontos_sim) for _, r in perguntas.iterrows() if respostas.get(int(r.id)) == "Sim")


def opcoes_qualificacao(row) -> list[tuple[str, int]]:
    opcoes = []
    for idx in (1, 2, 3):
        label = txt_value(row.get(f"opcao_{idx}", ""))
        if label:
            opcoes.append((label, int(row.get(f"pontos_{idx}", 0) or 0)))
    if opcoes:
        return opcoes
    return [("Não", 0), ("Sim", int(row.get("pontos_sim", 1) or 1))]


def txt_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def centered_radio(label: str, options: list[str], key: str, horizontal: bool = True):
    st.markdown(f'<div class="question-text">{html.escape(str(label))}</div>', unsafe_allow_html=True)
    left, middle, right = st.columns([1, 1, 1])
    with middle:
        return st.radio("Opções", options, horizontal=horizontal, key=key, label_visibility="collapsed")


def centered_radio_geral(label: str, options: list[str], key: str):
    st.markdown(f'<div class="question-text question-text-geral">{html.escape(str(label))}</div>', unsafe_allow_html=True)
    st.markdown('<div class="options-title">Opções</div>', unsafe_allow_html=True)
    estimated_width = sum(len(str(option)) * 7 for option in options) + (len(options) * 44) + max(len(options) - 1, 0) * 18
    center_fraction = min(max(estimated_width / 980, 0.24), 0.62)
    side_fraction = (1 - center_fraction) / 2
    left, middle, right = st.columns([side_fraction, center_fraction, side_fraction])
    with middle:
        return st.radio("", options, horizontal=True, key=key, label_visibility="collapsed")


def render_perguntas_qualificacao(perguntas: pd.DataFrame, prefixo: str) -> tuple[dict, dict]:
    respostas = {}
    pontos = {}
    for _, r in perguntas.iterrows():
        opcoes = opcoes_qualificacao(r)
        labels = [label for label, _ in opcoes]
        resposta = centered_radio_geral(r.pergunta, labels, key=f"{prefixo}_{int(r.id)}")
        respostas[int(r.id)] = resposta
        pontos[int(r.id)] = next((pts for label, pts in opcoes if label == resposta), 0)
    return respostas, pontos


def opcoes_bpf(row) -> list[str]:
    raw = txt_value(row.get("opcoes", "")) or "S;N;P;NA"
    return [item.strip() for item in raw.split(";") if item.strip()]


def pontuar_bpf(resposta: str) -> int:
    return 1 if resposta == "S" else 0


def render_perguntas_bpf(perguntas: pd.DataFrame, prefixo: str) -> tuple[dict, dict]:
    respostas = {}
    pontos = {}
    for _, r in perguntas.iterrows():
        codigo = txt_value(r.get("codigo_pergunta", "")) or str(int(r.id))
        label = f"{codigo} - {r.pergunta}" if codigo else r.pergunta
        resp = centered_radio(label, opcoes_bpf(r), key=f"{prefixo}_{int(r.id)}", horizontal=True)
        respostas[int(r.id)] = resp
        pontos[int(r.id)] = pontuar_bpf(resp)
    return respostas, pontos


def curso_perguntas_com_alternativas(curso_id: int) -> pd.DataFrame:
    perguntas = q("SELECT * FROM perguntas_curso WHERE curso_id=? AND ativo=1 ORDER BY ordem", (curso_id,))
    if perguntas.empty:
        return perguntas
    alt = q("SELECT * FROM alternativas_curso WHERE ativo=1 ORDER BY pergunta_id, ordem")
    perguntas = perguntas.copy()
    perguntas["alternativas"] = [[] for _ in range(len(perguntas))]
    for idx, row in perguntas.iterrows():
        itens = alt[alt.pergunta_id == int(row.id)] if not alt.empty else pd.DataFrame()
        perguntas.at[idx, "alternativas"] = itens.to_dict("records") if not itens.empty else []
    return perguntas


def badge(status: str) -> str:
    cls = "badge-blue"
    if status in ["Cancelado", "Reprovado"]:
        cls = "badge-red"
    elif status in ["Agendamento", "Execução"]:
        cls = "badge-yellow"
    elif status == "Finalizado":
        cls = "badge-green"
    elif status == "Validação Administrativa":
        cls = "badge-gray"
    return f'<span class="badge {cls}">{status}</span>'


def next_step(status: str) -> tuple[str, str]:
    mapa = {
        "Validação Administrativa": ("Análise Técnica", "Técnico"),
        "Análise Técnica": ("Agendamento", "Agendamento"),
        "Agendamento": ("Execução", "Executor"),
        "Execução": ("Finalizado", "Finalizado"),
    }
    return mapa.get(status, (status, ""))


def perfil_pode_atuar(perfil: str, status: str) -> bool:
    if status_final_fluxo(status):
        return False
    if texto_chave(perfil) in {"administrador", "moderador"}:
        return True
    permissao = {
        "Validação Administrativa": "Administrativo",
        "Análise Técnica": "Técnico",
        "Agendamento": "Agendamento",
        "Execução": "Executor",
    }
    return permissao.get(status) == perfil


def status_final_fluxo(status: str) -> bool:
    chave = texto_chave(status)
    return chave in {"reprovado", "cancelado", "finalizado"}


def parse_data_agendada(value):
    if not txt_value(value):
        return datetime.now()
    parsed = pd.to_datetime(value, errors="coerce", dayfirst=False)
    if pd.isna(parsed):
        return datetime.now()
    return parsed.to_pydatetime()


def get_owner(area: str, etapa: str) -> dict:
    df = q("SELECT * FROM owners_area WHERE area=? AND etapa=? AND ativo=1 LIMIT 1", (area, etapa))
    if df.empty:
        return {"nome": etapa, "email": "", "usuario": etapa}
    return dict(df.iloc[0])


def render_ordem_servico(row, allow_upload: bool = True, show_downloads: bool = True):
    if not os_disponivel_no_fluxo(row.status):
        return

    protocolo = row.protocolo
    os_path_value = txt_value(getattr(row, "os_preenchida_path", ""))
    os_nome = txt_value(getattr(row, "os_preenchida_nome", "")) or "OS_preenchida"

    st.markdown("### Ordem de Serviço")
    st.caption("Gerada automaticamente quando a Análise Técnica avança para Agendamento.")
    if show_downloads:
        os_bytes = file_download_bytes(os_path_value)
        if os_bytes:
            st.download_button(
                "Baixar OS gerada",
                os_bytes,
                file_name=os_nome,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
                key=f"download_os_preenchida_{protocolo}",
            )
            st.caption(f"Gerada por {getattr(row, 'os_preenchida_por', '') or '-'} em {getattr(row, 'os_preenchida_em', '') or '-'}")
        else:
            st.info("A OS ainda não foi gerada. Ela será criada ao avançar da Análise Técnica para Agendamento.")


def dataframe_respostas(df: pd.DataFrame):
    if df.empty:
        st.info("Nenhuma resposta encontrada para este formulário.")
        return
    renomeado = df.rename(
        columns={
            "questionario": "Formulário",
            "pergunta": "Pergunta",
            "resposta": "Resposta",
            "pontuacao": "Pontuação",
            "data_resposta": "Data Resposta",
        }
    )
    st.dataframe(renomeado, use_container_width=True, hide_index=True)


def render_formularios_protocolo(row):
    prot = row.protocolo
    detail_key = f"aprov_formulario_aberto_{prot}"
    if detail_key not in st.session_state:
        st.session_state[detail_key] = ""

    st.markdown("### Formulários e documentos")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("Formulário Geral", use_container_width=True, key=f"btn_form_geral_{prot}"):
        st.session_state[detail_key] = "geral"
    if c2.button("Formulário BPF", use_container_width=True, key=f"btn_form_bpf_{prot}"):
        st.session_state[detail_key] = "bpf"
    if c3.button("Formulário do Curso", use_container_width=True, key=f"btn_form_curso_{prot}"):
        st.session_state[detail_key] = "curso"

    os_path = txt_value(getattr(row, "os_preenchida_path", ""))
    os_nome = txt_value(getattr(row, "os_preenchida_nome", "")) or "OS_preenchida"
    os_bytes = file_download_bytes(os_path)
    if os_disponivel_no_fluxo(row.status) and os_bytes:
        c4.download_button(
            "Baixar OS",
            os_bytes,
            file_name=os_nome,
            mime=mimetypes.guess_type(os_nome)[0] or "application/octet-stream",
            use_container_width=True,
            key=f"btn_download_os_aprov_{prot}",
        )
    else:
        c4.button("Baixar OS", use_container_width=True, disabled=True, key=f"btn_download_os_disabled_{prot}")

    detalhe = st.session_state.get(detail_key, "")
    if detalhe == "geral":
        st.subheader("Respostas do Formulário Geral")
        respostas = q(
            "SELECT questionario,pergunta,resposta,pontuacao,data_resposta FROM respostas_entidade WHERE entidade_id=? ORDER BY questionario, id",
            (int(row.entidade_id),),
        )
        dataframe_respostas(respostas)
    elif detalhe == "bpf":
        st.subheader("Respostas do Formulário BPF")
        respostas = q(
            "SELECT pergunta,resposta,pontuacao,data_resposta FROM respostas_bpf WHERE entidade_id=? ORDER BY id",
            (int(row.entidade_id),),
        )
        dataframe_respostas(respostas)
    elif detalhe == "curso":
        st.subheader("Respostas do Formulário do Curso")
        respostas = q(
            "SELECT pergunta,resposta,pontuacao,data_resposta FROM respostas_curso WHERE protocolo=? ORDER BY id",
            (prot,),
        )
        dataframe_respostas(respostas)

    if os_disponivel_no_fluxo(row.status):
        render_ordem_servico(row, allow_upload=True)


def historico_protocolo_df(protocolo: str) -> pd.DataFrame:
    hist = q(
        "SELECT status_anterior,status_novo,usuario,data_movimento,observacao FROM historico_fluxo WHERE protocolo=? ORDER BY id",
        (protocolo,),
    )
    if hist.empty:
        return hist

    hist = hist.copy()
    movimentos = pd.to_datetime(hist["data_movimento"], errors="coerce")
    proximos = movimentos.shift(-1).fillna(pd.Timestamp.now())
    dias = ((proximos - movimentos).dt.total_seconds() / 86400).fillna(0)
    hist["dias_etapa"] = dias.clip(lower=0).round(1)
    return hist.rename(
        columns={
            "status_anterior": "Saída",
            "status_novo": "Entrada",
            "usuario": "Usuário",
            "data_movimento": "Data Movimento",
            "observacao": "Observação",
            "dias_etapa": "Dias na etapa",
        }
    )[["Saída", "Entrada", "Dias na etapa", "Usuário", "Data Movimento", "Observação"]]


def registrar_notificacao(protocolo: str, destinatario: str, assunto: str, corpo: str):
    exec_sql(
        "INSERT INTO notificacoes(protocolo,destinatario,assunto,corpo,enviado,data_criacao) VALUES(?,?,?,?,0,?)",
        (protocolo, destinatario or "", assunto, corpo, now_str()),
    )


def tentar_enviar_email(destinatario: str, assunto: str, corpo: str, anexos: Optional[list[tuple[Path, str]]] = None) -> tuple[bool, str]:
    """
    Para ativar envio real, crie .streamlit/secrets.toml:
    [smtp]
    host="smtp.office365.com"
    port=587
    user="seu_email@dominio.com"
    password="sua_senha_ou_app_password"
    from_email="seu_email@dominio.com"
    """
    if not destinatario:
        return False, "Destinatário não cadastrado. Notificação ficou registrada no sistema."
    try:
        smtp_cfg = st.secrets.get("smtp", None)
    except Exception:
        smtp_cfg = None
    if not smtp_cfg:
        return False, "SMTP não configurado. Notificação ficou registrada no sistema."
    try:
        msg = EmailMessage()
        msg["From"] = smtp_cfg.get("from_email", smtp_cfg.get("user"))
        msg["To"] = destinatario
        msg["Subject"] = assunto
        msg.set_content(corpo)
        for path, filename in anexos or []:
            if not path.exists() or not path.is_file():
                continue
            mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            maintype, subtype = mime_type.split("/", 1)
            msg.add_attachment(path.read_bytes(), maintype=maintype, subtype=subtype, filename=filename)
        with smtplib.SMTP(smtp_cfg["host"], int(smtp_cfg.get("port", 587))) as server:
            server.starttls()
            server.login(smtp_cfg["user"], smtp_cfg["password"])
            server.send_message(msg)
        return True, "Enviado"
    except Exception as e:
        return False, str(e)


def notificar_etapa(protocolo: str, area: str, etapa: str, status: str, solicitante_email: str = "", obs: str = ""):
    anexos_os = protocolo_os_anexos(protocolo) if os_disponivel_no_fluxo(status) else []
    if etapa == "Finalizado":
        assunto = f"Protocolo {protocolo} finalizado"
        corpo = f"O protocolo {protocolo} foi finalizado.\n\nObservação: {obs}"
        destinatarios = [solicitante_email] + [get_owner(area, e).get("email", "") for e in ETAPAS_APROVACAO]
        for destinatario in sorted(set(d for d in destinatarios if d)):
            registrar_notificacao(protocolo, destinatario, assunto, corpo)
            ok, erro = tentar_enviar_email(destinatario, assunto, corpo, anexos_os)
            if ok:
                exec_sql("UPDATE notificacoes SET enviado=1,data_envio=?,erro='' WHERE id=(SELECT MAX(id) FROM notificacoes)", (now_str(),))
            else:
                exec_sql("UPDATE notificacoes SET erro=? WHERE id=(SELECT MAX(id) FROM notificacoes)", (erro,))
        return
    elif status in ["Cancelado", "Reprovado"]:
        assunto = f"Protocolo {protocolo} {status.lower()}"
        corpo = f"O protocolo {protocolo} foi {status.lower()}.\n\nObservação: {obs}"
        destinatarios = [solicitante_email] + [get_owner(area, e).get("email", "") for e in ETAPAS_APROVACAO]
        for destinatario in sorted(set(d for d in destinatarios if d)):
            registrar_notificacao(protocolo, destinatario, assunto, corpo)
            ok, erro = tentar_enviar_email(destinatario, assunto, corpo, anexos_os)
            if ok:
                exec_sql("UPDATE notificacoes SET enviado=1,data_envio=?,erro='' WHERE id=(SELECT MAX(id) FROM notificacoes)", (now_str(),))
            else:
                exec_sql("UPDATE notificacoes SET erro=? WHERE id=(SELECT MAX(id) FROM notificacoes)", (erro,))
        return
    else:
        owner = get_owner(area, etapa)
        destinatario = owner.get("email", "")
        assunto = f"Nova demanda para {status} - {protocolo}"
        corpo = f"Existe uma nova demanda aguardando sua atuação.\n\nProtocolo: {protocolo}\nÁrea: {area}\nStatus: {status}\n\nObservação: {obs}"
    registrar_notificacao(protocolo, destinatario, assunto, corpo)
    ok, erro = tentar_enviar_email(destinatario, assunto, corpo, anexos_os)
    if ok:
        exec_sql("UPDATE notificacoes SET enviado=1,data_envio=?,erro='' WHERE id=(SELECT MAX(id) FROM notificacoes)", (now_str(),))
    else:
        exec_sql("UPDATE notificacoes SET erro=? WHERE id=(SELECT MAX(id) FROM notificacoes)", (erro,))


def login():
    st.markdown(
        f"""
        <div class="login-shell">
          <div class="login-hero-bar">
            <div class="login-hero-title">{APP_TITLE}</div>
            <div class="login-hero-subtitle">Sistema Bahia</div>
          </div>
          {login_logo(1)}
          {login_logo(2)}
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns([1, 1.05, 1])
    with c2:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("### Acesso ao sistema")
        st.caption("Entre para acompanhar qualificações, cursos e fluxos.")
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar", use_container_width=True):
            u = q("SELECT * FROM usuarios WHERE usuario=? AND ativo=1", (usuario,))
            if not u.empty and u.iloc[0]["senha_hash"] == hash_pw(senha):
                st.session_state.user = dict(u.iloc[0])
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")
        st.markdown('</div>', unsafe_allow_html=True)


def go_to_main():
    st.session_state.next_nav_page = "Tela principal"
    st.session_state.pop("nav_page", None)
    st.session_state.pop("bpf_entidade_id", None)
    st.session_state.pop("geral_entidade_id", None)
    st.rerun()


def clear_state_prefix(prefix: str):
    for key in list(st.session_state.keys()):
        if str(key).startswith(prefix):
            st.session_state.pop(key, None)


def is_admin_or_moderador(user: dict) -> bool:
    return texto_chave(user.get("perfil")) in {"administrador", "moderador"}


def perfil_tem_aprovacoes(user: dict) -> bool:
    return texto_chave(user.get("perfil")) in {"administrador", "moderador", "administrativo", "tecnico", "agendamento", "executor"}


def filtrar_minhas_entidades(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    user = st.session_state.get("user", {})
    if is_admin_or_moderador(user):
        return df
    usuario = txt_value(user.get("usuario"))
    email = txt_value(user.get("email")).lower()
    mask = pd.Series(False, index=df.index)
    if "cadastrado_por" in df.columns and usuario:
        mask = mask | (df["cadastrado_por"].fillna("").astype(str) == usuario)
    if "cadastrado_por_email" in df.columns and email:
        mask = mask | (df["cadastrado_por_email"].fillna("").astype(str).str.lower() == email)
    return df[mask]


def top_nav():
    user = st.session_state.user
    initials = "".join(part[:1] for part in str(user["nome"]).split()[:2]).upper() or "U"
    st.sidebar.markdown(
        f"""
        <div class="sidebar-brand">
          <div class="brand-logos">{logo_box(1)}{logo_box(2)}</div>
          <div>
            <div class="brand-title">Sistema Bahia</div>
            <div class="brand-subtitle">Governança & Qualificação</div>
          </div>
        </div>
        <div class="user-chip">
          <div><span class="avatar">{initials}</span><strong>{user['nome']}</strong></div>
          <div class="brand-subtitle">{user['perfil']} · {user['usuario']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    menu = ["Tela principal", "Qualificar Nova Entidade", "Cursos", "Consultar Status", "Minhas Aprovações"]
    if user["perfil"] == "Administrador":
        menu += ["Configurações"]
    current_page = st.session_state.pop("next_nav_page", st.session_state.get("nav_radio", "Tela principal"))
    if current_page not in menu:
        current_page = "Tela principal"
    st.session_state.nav_radio = current_page
    page = st.sidebar.radio("Menu principal", menu, index=menu.index(current_page), key="nav_radio", label_visibility="collapsed")
    if st.sidebar.button("Sair", key="logout_top", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    st.markdown(
        f"""
        <div class="topbar">
          <div class="topbar-title">{page}</div>
          <div class="topbar-subtitle">Sistema Bahia · {user['perfil']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return page


def dashboard():
    st.title(APP_TITLE)
    entidades = q("SELECT * FROM entidades WHERE ativo=1")
    prot = q("SELECT * FROM protocolos")
    cursos = q("SELECT * FROM cursos WHERE ativo=1")
    k1, k2, k3, k4, k5 = st.columns(5)
    vals = [
        (len(entidades), "Entidades"),
        (len(cursos), "Cursos ativos"),
        (len(prot[~prot.status.isin(['Finalizado','Cancelado','Reprovado'])]) if not prot.empty else 0, "Em andamento"),
        (len(prot[prot.status == 'Finalizado']) if not prot.empty else 0, "Finalizados"),
        (len(prot[prot.status.isin(['Cancelado','Reprovado'])]) if not prot.empty else 0, "Cancelados/Reprovados"),
    ]
    for col, (v, l) in zip([k1, k2, k3, k4, k5], vals):
        with col:
            st.markdown(f'<div class="bahia-card"><div class="kpi">{v}</div><div class="kpi-label">{l}</div></div>', unsafe_allow_html=True)
    st.divider()
    if not prot.empty:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(px.pie(prot, names="status", title="Protocolos por status"), use_container_width=True)
        with col2:
            if not entidades.empty:
                st.plotly_chart(px.histogram(entidades, x="nivel", title="Entidades por nível"), use_container_width=True)
        st.subheader("Últimas demandas")
        df = q("""SELECT p.protocolo,e.entidade,c.curso,p.area,p.status,p.data_abertura,p.data_atualizacao
                  FROM protocolos p
                  LEFT JOIN entidades e ON e.id=p.entidade_id
                  LEFT JOIN cursos c ON c.id=p.curso_id
                  ORDER BY p.id DESC LIMIT 10""")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Ainda não existem protocolos. Cadastre uma entidade e envie uma demanda.")


def tela_principal():
    st.title("Tela principal")
    entidades = q("SELECT * FROM entidades WHERE ativo=1")
    protocolos = q("SELECT * FROM protocolos")
    cursos = q("SELECT * FROM cursos WHERE ativo=1")

    cursos_disponiveis = 0
    if not cursos.empty:
        cursos = cursos.copy()
        cursos["estoque_disponivel"] = cursos.apply(
            lambda r: estoque_disponivel(int(r.id), int(r.estoque_total or 0)),
            axis=1,
        )
        cursos_disponiveis = len(cursos[cursos.estoque_disponivel > 0])

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    indicadores = [
        (len(entidades), "Entidades cadastradas"),
        (len(entidades[entidades.status_qualificacao == "Concluída"]) if not entidades.empty else 0, "Entidades qualificadas"),
        (len(entidades[entidades.status_qualificacao == FORM_GERAL_PENDENTE]) if not entidades.empty else 0, "Form. geral pendentes"),
        (len(entidades[entidades.status_qualificacao == "BPF pendente"]) if not entidades.empty else 0, "BPF pendentes"),
        (cursos_disponiveis, "Cursos disponíveis"),
        (len(protocolos[~protocolos.status.isin(["Finalizado", "Cancelado", "Reprovado"])]) if not protocolos.empty else 0, "Fluxos em andamento"),
    ]
    for col, (valor, label) in zip([c1, c2, c3, c4, c5, c6], indicadores):
        with col:
            st.markdown(
                f'<div class="bahia-card"><div class="kpi">{valor}</div><div class="kpi-label">{label}</div></div>',
                unsafe_allow_html=True,
            )

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if entidades.empty:
            st.info("Ainda não existem entidades cadastradas.")
        else:
            nivel_df = entidades["nivel"].fillna("Sem nível").value_counts().reset_index()
            nivel_df.columns = ["Nível", "Quantidade"]
            st.plotly_chart(
                px.bar(nivel_df, x="Nível", y="Quantidade", title="Entidades por nível de qualificação"),
                use_container_width=True,
            )
    with col2:
        if cursos.empty:
            st.info("Ainda não existem cursos ativos.")
        else:
            cursos_area = cursos.groupby("area", dropna=False).agg(
                ativos=("id", "count"),
                disponiveis=("estoque_disponivel", lambda serie: int((serie > 0).sum())),
            ).reset_index()
            cursos_area["area"] = cursos_area["area"].fillna("Sem área")
            st.plotly_chart(
                px.bar(cursos_area, x="area", y=["ativos", "disponiveis"], barmode="group", title="Cursos por área"),
                use_container_width=True,
            )

    if not protocolos.empty:
        st.plotly_chart(px.pie(protocolos, names="status", title="Protocolos por status"), use_container_width=True)
        ultimas = q("""SELECT p.protocolo,e.entidade,c.curso,p.area,p.status,p.data_abertura,p.data_atualizacao
                       FROM protocolos p
                       LEFT JOIN entidades e ON e.id=p.entidade_id
                       LEFT JOIN cursos c ON c.id=p.curso_id
                       ORDER BY p.id DESC LIMIT 10""")
        st.subheader("Últimas demandas")
        st.dataframe(ultimas, use_container_width=True, hide_index=True)


def entidades_page():
    st.title("Entidades")
    aba_cadastro, aba_base = st.tabs(["Cadastrar Nova entidade", "Base cadastral"])

    with aba_cadastro:
        st.subheader("Cadastrar Nova entidade")
        entidade_nonce = st.session_state.get("entidade_minima_nonce", 0)
        with st.form(f"cadastrar_entidade_minima_{entidade_nonce}"):
            entidade = st.text_input("Nome da Entidade *", key=f"entidade_minima_nome_{entidade_nonce}")
            salvar = st.form_submit_button("Salvar", use_container_width=True)
        if salvar:
            if not entidade.strip():
                st.error("Informe o nome da entidade.")
            else:
                data = now_str()
                exec_sql(
                    """INSERT INTO entidades(entidade,status_qualificacao,data_cadastro,cadastrado_por,cadastrado_por_email,ativo)
                       VALUES(?,?,?,?,?,?)""",
                    (
                        entidade.strip(),
                        CADASTRO_INICIAL,
                        data,
                        st.session_state.user["usuario"],
                        st.session_state.user.get("email", ""),
                        True,
                    ),
                )
                st.session_state.entidade_minima_nonce = entidade_nonce + 1
                go_to_main()

    with aba_base:
        df = q("SELECT * FROM entidades WHERE ativo=1 ORDER BY id DESC")
        busca = st.text_input("Buscar entidade")
        if busca and not df.empty:
            df = df[df["entidade"].str.contains(busca, case=False, na=False)]

        if df.empty:
            st.info("Nenhuma entidade encontrada.")
            return

        base_cols = [
            "id",
            "entidade",
            "cnpj",
            "territorio_identidade",
            "municipio_entidade",
            "certificacao",
            "licenca_ambiental",
            "telefone",
            "endereco",
            "email_responsavel",
            "atep",
            "agente_negocio",
            "numero_convenio",
            "an_atep_ateg",
            "nome_ateg",
            "coordenador_tipo",
            "nome_coordenador",
            "natureza_juridica",
            "dap_caf",
            "tipologia_beneficiarios",
            "comunidade_tradicional",
            "ativa_dinamica",
            "status_qualificacao",
            "nivel",
            "pontuacao",
            "pontuacao_q1",
            "pontuacao_q2",
            "data_cadastro",
            "cadastrado_por_email",
            "cadastrado_por",
        ]
        rename_cols = {
            "id": "ID",
            "entidade": "Entidade",
            "cnpj": "CNPJ",
            "territorio_identidade": "Territorio da entidade",
            "municipio_entidade": "Municipio da entidade",
            "certificacao": "Certificacao",
            "licenca_ambiental": "Licenca ambiental",
            "telefone": "Telefone",
            "endereco": "Endereco",
            "email_responsavel": "E-mail responsavel",
            "atep": "ATEP",
            "agente_negocio": "Agente de negocio",
            "numero_convenio": "Numero do convenio",
            "an_atep_ateg": "AN ou ATEP/ATEG",
            "nome_ateg": "Nome ATEG",
            "coordenador_tipo": "Tipo de coordenador",
            "nome_coordenador": "Nome do coordenador",
            "natureza_juridica": "Natureza juridica",
            "dap_caf": "DAP ou CAF",
            "tipologia_beneficiarios": "Tipologia de beneficiarios",
            "comunidade_tradicional": "Comunidade tradicional",
            "ativa_dinamica": "Ativa ou dinamica",
            "status_qualificacao": "Status qualificacao",
            "nivel": "Nivel",
            "pontuacao": "Pontuacao geral",
            "pontuacao_q1": "Pontuacao Bloco 1",
            "pontuacao_q2": "Pontuacao Bloco 2",
            "data_cadastro": "Data cadastro",
            "cadastrado_por_email": "Cadastrado por e-mail",
            "cadastrado_por": "Cadastrado por",
        }
        display_cols = [col for col in base_cols if col in df.columns]

        st.subheader("Base cadastral")
        st.dataframe(df[display_cols].rename(columns=rename_cols), use_container_width=True, hide_index=True)

        entidade_nome = st.selectbox("Ver respostas da entidade", df["entidade"].tolist())
        ent_id = int(df[df.entidade == entidade_nome].iloc[0].id)
        respostas = q("SELECT questionario,pergunta,resposta,pontuacao,data_resposta FROM respostas_entidade WHERE entidade_id=? ORDER BY questionario, id", (ent_id,))
        if not respostas.empty:
            st.subheader("Respostas registradas")
            st.dataframe(respostas, use_container_width=True, hide_index=True)


def nova_qualificacao():
    st.title("Qualificar Nova Entidade")
    if "bpf_entidade_id" in st.session_state:
        st.info("Qualificação salva. Finalize o BPF para concluir o cadastro da entidade.")
        bpf_pendentes(entidade_id=st.session_state.bpf_entidade_id)
        return
    aba_nova, aba_pendentes = st.tabs(["Nova qualificação", "Aguardando finalizar"])
    with aba_nova:
        nova_qualificacao_form_v2()
    with aba_pendentes:
        bpf_pendentes()


def nova_qualificacao_form():
    form_nonce = st.session_state.get("qual_form_nonce", 0)
    field_key = lambda name: f"qual_form_{form_nonce}_{name}"
    perguntas = q("SELECT * FROM perguntas_qualificacao WHERE ativo=1 ORDER BY questionario, ordem")
    with st.container(border=True):
        st.subheader("Dados cadastrais")
        c1, c2, c3 = st.columns(3)
        with c1:
            entidade = st.text_input("Entidade *", key=field_key("entidade"))
            convenio = st.text_input("Número do Convênio")
            an_atep_ateg = st.selectbox("AN ou ATEP / ATEG", ["AN", "ATEP/ATEG"], key=field_key("an_atep_ateg"))
            agente = st.text_input("Nome do Agente de Negócio") if an_atep_ateg == "AN" else ""
            atep = st.text_input("Nome ATEP", key=field_key("atep")) if an_atep_ateg == "ATEP/ATEG" else ""
            nome_ateg = st.text_input("Nome ATEG", key=field_key("nome_ateg")) if an_atep_ateg == "ATEP/ATEG" else ""
        with c2:
            coordenador_tipo = st.selectbox("Coordenação", ["Coordenador de Negócio", "Coordenador de Mercado"])
            nome_coordenador = st.text_input("Nome do Coordenador")
            natureza = st.selectbox("Natureza Jurídica da Entidade", NATUREZAS_JURIDICAS)
            cnpj = st.text_input("Nº CNPJ")
            dap_caf = st.text_input("Nº DAP ou CAF")
        with c3:
            territorio = st.text_input("Território de Identidade")
            email_resp = st.text_input("Email")
            tipologia = st.selectbox("Tipologia de Beneficiários", TIPOLOGIAS_BENEFICIARIOS)
            comunidade = st.selectbox("Comunidades Tradicionais", COMUNIDADES_TRADICIONAIS) if tipologia == "Comunidades Tradicionais" else ""
            ativa_dinamica = st.selectbox("Ativa ou Dinâmica", ["Ativa", "Dinâmica"])
        st.divider()
        respostas = {}
        pontos_respostas = {}
        if perguntas.empty:
            st.warning("Nenhuma pergunta de qualificação cadastrada.")
        else:
            for bloco, bloco_df in perguntas.groupby("questionario", sort=False):
                st.subheader(bloco)
                bloco_respostas, bloco_pontos = render_perguntas_qualificacao(bloco_df, f"qual_{bloco}")
                respostas.update(bloco_respostas)
                pontos_respostas.update(bloco_pontos)
        c_cancelar, c_salvar = st.columns(2)
        cancelar = c_cancelar.button("Cancelar", use_container_width=True, key="cancelar_qualificacao")
        salvar = c_salvar.button("Salvar e abrir BPF", use_container_width=True, key="salvar_qualificacao")
    if cancelar:
        st.info("Cadastro cancelado. Como ele ainda não foi salvo, não há pendência para finalizar.")
    if salvar:
        if not entidade.strip():
            st.error("Informe o nome da entidade.")
            return
        pontos_por_bloco = {
            bloco: sum(pontos_respostas.get(int(r.id), 0) for _, r in bloco_df.iterrows())
            for bloco, bloco_df in perguntas.groupby("questionario", sort=False)
        }
        p_q1 = sum(pontos_por_bloco.values())
        p_q2 = 0
        pontos = p_q1
        nivel = nivel_por_pontos(pontos)
        data = now_str()
        with conn() as c:
            cur = c.cursor()
            cur.execute("""INSERT INTO entidades(
                               entidade,cnpj,email_responsavel,atep,agente_negocio,numero_convenio,
                               an_atep_ateg,nome_ateg,coordenador_tipo,nome_coordenador,natureza_juridica,
                               dap_caf,territorio_identidade,tipologia_beneficiarios,comunidade_tradicional,
                               ativa_dinamica,status_qualificacao,nivel,pontuacao,pontuacao_q1,pontuacao_q2,
                               data_cadastro,cadastrado_por,cadastrado_por_email)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            entidade, cnpj, email_resp, atep, agente, convenio, an_atep_ateg, nome_ateg,
                            coordenador_tipo, nome_coordenador, natureza, dap_caf, territorio, tipologia,
                            comunidade, ativa_dinamica, "BPF pendente", nivel, pontos, p_q1, p_q2, data,
                            st.session_state.user["usuario"],
                            st.session_state.user.get("email", ""),
                        ))
            entidade_id = cur.lastrowid
            rows = []
            for _, r in perguntas.iterrows():
                resp = respostas.get(int(r.id), "Não")
                pts = pontos_respostas.get(int(r.id), 0)
                rows.append((entidade_id, r.questionario, int(r.id), r.pergunta, resp, pts, data))
            cur.executemany("""INSERT INTO respostas_entidade(entidade_id,questionario,pergunta_id,pergunta,resposta,pontuacao,data_resposta)
                               VALUES(?,?,?,?,?,?,?)""", rows)
            c.commit()
        st.session_state.bpf_entidade_id = int(entidade_id)
        detalhes = " | ".join(f"{bloco}: {pts}" for bloco, pts in pontos_por_bloco.items())
        st.success(f"Entidade salva como {nivel}. Pontuação: {pontos}. {detalhes}. Abrindo o BPF agora.")
        st.rerun()


def nova_qualificacao_form_v2():
    form_nonce = st.session_state.get("qual_form_nonce", 0)

    def field_key(name: str) -> str:
        return f"qual_form_{form_nonce}_{name}"

    perguntas = q("SELECT * FROM perguntas_qualificacao WHERE ativo=1 ORDER BY questionario, ordem")
    with st.container(border=True):
        st.subheader("Dados cadastrais")
        c1, c2, c3 = st.columns(3)
        with c1:
            entidade = st.text_input("Entidade *", key=field_key("entidade"))
            convenio = st.text_input("Numero do Convenio", key=field_key("convenio"))
            an_atep_ateg = st.selectbox("AN ou ATEP / ATEG", ["AN", "ATEP/ATEG"], key=field_key("an_atep_ateg"))
            agente = st.text_input("Nome do Agente de Negocio", key=field_key("agente")) if an_atep_ateg == "AN" else ""
            atep = st.text_input("Nome ATEP", key=field_key("atep")) if an_atep_ateg == "ATEP/ATEG" else ""
            nome_ateg = st.text_input("Nome ATEG", key=field_key("nome_ateg")) if an_atep_ateg == "ATEP/ATEG" else ""
        with c2:
            coordenador_tipo = st.selectbox("Coordenacao", ["Coordenador de Negocio", "Coordenador de Mercado"], key=field_key("coordenador_tipo"))
            nome_coordenador = st.text_input("Nome do Coordenador", key=field_key("nome_coordenador"))
            natureza = st.selectbox("Natureza Juridica da Entidade", NATUREZAS_JURIDICAS, key=field_key("natureza"))
            cnpj = st.text_input("No CNPJ", key=field_key("cnpj"))
            dap_caf = st.text_input("No DAP ou CAF", key=field_key("dap_caf"))
        with c3:
            territorio = st.text_input("Territorio de Identidade", key=field_key("territorio"))
            email_resp = st.text_input("Email", key=field_key("email_resp"))
            tipologia = st.selectbox("Tipologia de Beneficiarios", TIPOLOGIAS_BENEFICIARIOS, key=field_key("tipologia"))
            comunidade = st.selectbox("Comunidades Tradicionais", COMUNIDADES_TRADICIONAIS, key=field_key("comunidade")) if tipologia == "Comunidades Tradicionais" else ""
            ativa_dinamica = st.selectbox("Ativa ou Dinamica", ["Ativa", "Dinamica"], key=field_key("ativa_dinamica"))

        st.divider()
        respostas = {}
        pontos_respostas = {}
        if perguntas.empty:
            st.warning("Nenhuma pergunta de qualificacao cadastrada.")
        else:
            for bloco_idx, (bloco, bloco_df) in enumerate(perguntas.groupby("questionario", sort=False), start=1):
                with st.expander(str(bloco), expanded=True):
                    bloco_respostas, bloco_pontos = render_perguntas_qualificacao(bloco_df, f"qual_v2_{form_nonce}_{bloco_idx}")
                    respostas.update(bloco_respostas)
                    pontos_respostas.update(bloco_pontos)

        c_cancelar, c_salvar = st.columns(2)
        cancelar = c_cancelar.button("Cancelar", use_container_width=True, key=field_key("cancelar"))
        salvar = c_salvar.button("Salvar e abrir BPF", use_container_width=True, key=field_key("salvar"))

    if cancelar:
        st.session_state.qual_form_nonce = form_nonce + 1
        st.info("Formulario limpo.")
        go_to_main()
    if salvar:
        if not entidade.strip():
            st.error("Informe o nome da entidade.")
            return
        pontos_por_bloco = {
            bloco: sum(pontos_respostas.get(int(r.id), 0) for _, r in bloco_df.iterrows())
            for bloco, bloco_df in perguntas.groupby("questionario", sort=False)
        }
        p_q1 = sum(pontos_por_bloco.values())
        p_q2 = 0
        pontos = p_q1
        nivel = nivel_por_pontos(pontos)
        data = now_str()
        with conn() as c:
            cur = c.cursor()
            cur.execute("""INSERT INTO entidades(
                               entidade,cnpj,email_responsavel,atep,agente_negocio,numero_convenio,
                               an_atep_ateg,nome_ateg,coordenador_tipo,nome_coordenador,natureza_juridica,
                               dap_caf,territorio_identidade,tipologia_beneficiarios,comunidade_tradicional,
                               ativa_dinamica,status_qualificacao,nivel,pontuacao,pontuacao_q1,pontuacao_q2,
                               data_cadastro,cadastrado_por,cadastrado_por_email)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            entidade, cnpj, email_resp, atep, agente, convenio, an_atep_ateg, nome_ateg,
                            coordenador_tipo, nome_coordenador, natureza, dap_caf, territorio, tipologia,
                            comunidade, ativa_dinamica, "BPF pendente", nivel, pontos, p_q1, p_q2, data,
                            st.session_state.user["usuario"],
                            st.session_state.user.get("email", ""),
                        ))
            entidade_id = cur.lastrowid
            rows = []
            for _, r in perguntas.iterrows():
                resp = respostas.get(int(r.id), "Nao")
                pts = pontos_respostas.get(int(r.id), 0)
                rows.append((entidade_id, r.questionario, int(r.id), r.pergunta, resp, pts, data))
            cur.executemany("""INSERT INTO respostas_entidade(entidade_id,questionario,pergunta_id,pergunta,resposta,pontuacao,data_resposta)
                               VALUES(?,?,?,?,?,?,?)""", rows)
            c.commit()
        st.session_state.bpf_entidade_id = int(entidade_id)
        detalhes = " | ".join(f"{bloco}: {pts}" for bloco, pts in pontos_por_bloco.items())
        st.success(f"Entidade salva como {nivel}. Pontuacao: {pontos}. {detalhes}. Abrindo o BPF agora.")
        st.rerun()


CADASTRO_INICIAL = "Cadastro inicial"
FORM_GERAL_PENDENTE = "Formulario geral pendente"


def nova_qualificacao_fluxo():
    st.title("Qualificar Nova Entidade")
    if "bpf_entidade_id" in st.session_state:
        st.info("Formulario geral salvo. Finalize o BPF para concluir o cadastro.")
        bpf_pendentes(entidade_id=st.session_state.bpf_entidade_id)
        return
    if "geral_entidade_id" in st.session_state:
        st.info("Dados cadastrais salvos. Finalize o Formulario Geral para seguir ao BPF.")
        formulario_geral_pendente(entidade_id=st.session_state.geral_entidade_id)
        return

    aba_cadastro, aba_geral, aba_bpf = st.tabs([
        "Selecionar entidade da base",
        "Aguardando Finalizar Formulario Geral",
        "Aguardando Finalizar Formulario BPF",
    ])
    with aba_cadastro:
        dados_cadastrais_form()
    with aba_geral:
        formulario_geral_pendente()
    with aba_bpf:
        bpf_pendentes()


def dados_cadastrais_form():
    form_nonce = st.session_state.get("cadastro_form_nonce", 0)

    def field_key(name: str) -> str:
        return f"cadastro_form_{form_nonce}_{name}"

    entidades_base = q(
        """SELECT * FROM entidades
           WHERE ativo=1
             AND COALESCE(status_qualificacao, '') NOT IN (?, ?)
           ORDER BY entidade""",
        (FORM_GERAL_PENDENTE, "BPF pendente"),
    )
    entidades_base = filtrar_minhas_entidades(entidades_base)
    if entidades_base.empty:
        st.info("Nenhuma entidade disponível para iniciar qualificação. Entidades já em andamento aparecem nas abas de pendência.")
        return

    with st.container(border=True):
        st.subheader("Dados cadastrais")
        st.info("Selecione uma entidade já cadastrada na base. Para criar uma nova opção nesta lista, acesse Entidades > Cadastrar Nova entidade.")
        labels = [f"{int(r.id)} | {r.entidade}" for _, r in entidades_base.iterrows()]
        entidade_label = st.selectbox("Entidade cadastrada na base *", labels, key=field_key("entidade_select"))
        entidade_id = int(entidade_label.split(" | ")[0])
        entidade_atual = entidades_base[entidades_base.id == entidade_id].iloc[0]
        entidade = str(entidade_atual.entidade)

        c1, c2, c3 = st.columns(3)
        with c1:
            cnpj = st.text_input("CNPJ", value=txt_value(entidade_atual.get("cnpj")), key=field_key("cnpj"))
            territorio = st.text_input("Territorio da Entidade", value=txt_value(entidade_atual.get("territorio_identidade")), key=field_key("territorio"))
            certificacao_atual = txt_value(entidade_atual.get("certificacao"))
            certificacao = st.selectbox(
                "Certificacao",
                CERTIFICACOES_ENTIDADE,
                index=CERTIFICACOES_ENTIDADE.index(certificacao_atual) if certificacao_atual in CERTIFICACOES_ENTIDADE else 0,
                key=field_key("certificacao"),
            )
            convenio = st.text_input("Numero do Convenio", value=txt_value(entidade_atual.get("numero_convenio")), key=field_key("convenio"))
            an_atep_ateg = st.selectbox("AN ou ATEP / ATEG", ["AN", "ATEP/ATEG"], key=field_key("an_atep_ateg"))
            agente = st.text_input("Nome do Agente de Negocio", key=field_key("agente")) if an_atep_ateg == "AN" else ""
            atep = st.text_input("Nome ATEP", key=field_key("atep")) if an_atep_ateg == "ATEP/ATEG" else ""
            nome_ateg = st.text_input("Nome ATEG", key=field_key("nome_ateg")) if an_atep_ateg == "ATEP/ATEG" else ""
        with c2:
            municipio = st.text_input("Municipio da Entidade", value=txt_value(entidade_atual.get("municipio_entidade")), key=field_key("municipio"))
            licenca_atual = txt_value(entidade_atual.get("licenca_ambiental"))
            licenca_ambiental = st.selectbox(
                "Licenca ambiental",
                LICENCAS_AMBIENTAIS,
                index=LICENCAS_AMBIENTAIS.index(licenca_atual) if licenca_atual in LICENCAS_AMBIENTAIS else 0,
                key=field_key("licenca_ambiental"),
            )
            coordenador_tipo = st.selectbox("Coordenacao", ["Coordenador de Negocio", "Coordenador de Mercado"], key=field_key("coordenador_tipo"))
            nome_coordenador = st.text_input("Nome do Coordenador", key=field_key("nome_coordenador"))
            natureza = st.selectbox("Natureza Juridica da Entidade", NATUREZAS_JURIDICAS, key=field_key("natureza"))
            dap_caf = st.text_input("No DAP ou CAF", key=field_key("dap_caf"))
        with c3:
            email_resp = st.text_input("Email", value=txt_value(entidade_atual.get("email_responsavel")), key=field_key("email_resp"))
            telefone = st.text_input("Telefone", value=txt_value(entidade_atual.get("telefone")), key=field_key("telefone"))
            endereco = st.text_input("Endereco", value=txt_value(entidade_atual.get("endereco")), key=field_key("endereco"))
            tipologia = st.selectbox("Tipologia de Beneficiarios", TIPOLOGIAS_BENEFICIARIOS, key=field_key("tipologia"))
            comunidade = st.selectbox("Comunidades Tradicionais", COMUNIDADES_TRADICIONAIS, key=field_key("comunidade")) if tipologia == "Comunidades Tradicionais" else ""
            ativa_dinamica = st.selectbox("Ativa ou Dinamica", ["Ativa", "Dinamica"], key=field_key("ativa_dinamica"))

        c_cancelar, c_salvar = st.columns(2)
        cancelar = c_cancelar.button("Cancelar", use_container_width=True, key=field_key("cancelar"))
        salvar = c_salvar.button("Salvar dados cadastrais", use_container_width=True, key=field_key("salvar"))

    if cancelar:
        st.session_state.cadastro_form_nonce = form_nonce + 1
        go_to_main()
    if salvar:
        data = now_str()
        with conn() as c:
            cur = c.cursor()
            cur.execute("""UPDATE entidades
                           SET cnpj=?,email_responsavel=?,atep=?,agente_negocio=?,numero_convenio=?,
                               an_atep_ateg=?,nome_ateg=?,coordenador_tipo=?,nome_coordenador=?,natureza_juridica=?,
                               dap_caf=?,territorio_identidade=?,municipio_entidade=?,certificacao=?,
                               licenca_ambiental=?,telefone=?,endereco=?,tipologia_beneficiarios=?,comunidade_tradicional=?,
                               ativa_dinamica=?,status_qualificacao=?,cadastrado_por=?,cadastrado_por_email=?
                           WHERE id=?""",
                        (
                            cnpj, email_resp, atep, agente, convenio, an_atep_ateg, nome_ateg,
                            coordenador_tipo, nome_coordenador, natureza, dap_caf, territorio, municipio,
                            certificacao, licenca_ambiental, telefone, endereco, tipologia, comunidade,
                            ativa_dinamica, FORM_GERAL_PENDENTE,
                            st.session_state.user["usuario"],
                            st.session_state.user.get("email", ""),
                            entidade_id,
                        ))
            c.commit()
        st.session_state.geral_entidade_id = int(entidade_id)
        st.session_state.cadastro_form_nonce = form_nonce + 1
        clear_state_prefix(f"cadastro_form_{form_nonce}_")
        st.success("Dados cadastrais salvos. Abrindo Formulario Geral.")
        st.rerun()


def formulario_geral_pendente(entidade_id: Optional[int] = None):
    pendentes = q(
        "SELECT * FROM entidades WHERE ativo=1 AND status_qualificacao=? ORDER BY id DESC",
        (FORM_GERAL_PENDENTE,),
    )
    pendentes = filtrar_minhas_entidades(pendentes)
    if pendentes.empty:
        st.info("Nenhuma entidade aguardando Formulario Geral.")
        st.session_state.pop("geral_entidade_id", None)
        return
    if entidade_id is not None:
        entidade_match = pendentes[pendentes.id == int(entidade_id)]
        if entidade_match.empty:
            st.session_state.pop("geral_entidade_id", None)
            st.info("Esta entidade nao esta mais aguardando Formulario Geral.")
            return
        ent = entidade_match.iloc[0]
        st.markdown(f'<span class="badge badge-blue">Formulario Geral de {ent.entidade}</span>', unsafe_allow_html=True)
    else:
        default_idx = 0
        if "geral_entidade_id" in st.session_state:
            matches = pendentes.index[pendentes.id == st.session_state.geral_entidade_id].tolist()
            if matches:
                default_idx = pendentes.index.get_loc(matches[0])
        entidade_nome = st.selectbox("Entidade aguardando Formulario Geral", pendentes.entidade.tolist(), index=default_idx)
        ent = pendentes[pendentes.entidade == entidade_nome].iloc[0]

    perguntas = q("SELECT * FROM perguntas_qualificacao WHERE ativo=1 ORDER BY questionario, ordem")
    if perguntas.empty:
        st.warning("Nenhuma pergunta de qualificacao cadastrada.")
        return

    with st.form(f"formulario_geral_{int(ent.id)}"):
        st.subheader("Formulario Geral")
        respostas = {}
        pontos_respostas = {}
        for bloco_idx, (bloco, bloco_df) in enumerate(perguntas.groupby("questionario", sort=False), start=1):
            with st.expander(str(bloco), expanded=True):
                bloco_respostas, bloco_pontos = render_perguntas_qualificacao(bloco_df, f"geral_{int(ent.id)}_{bloco_idx}")
                respostas.update(bloco_respostas)
                pontos_respostas.update(bloco_pontos)
        c_cancelar, c_salvar = st.columns(2)
        cancelar = c_cancelar.form_submit_button("Cancelar e manter pendente", use_container_width=True)
        salvar = c_salvar.form_submit_button("Salvar Formulario Geral e abrir BPF", use_container_width=True)

    if cancelar:
        go_to_main()
    if salvar:
        pontos_por_bloco = {
            bloco: sum(pontos_respostas.get(int(r.id), 0) for _, r in bloco_df.iterrows())
            for bloco, bloco_df in perguntas.groupby("questionario", sort=False)
        }
        p_q1 = sum(pontos_por_bloco.values())
        p_q2 = 0
        pontos = p_q1
        nivel = nivel_por_pontos(pontos)
        data = now_str()
        with conn() as c:
            cur = c.cursor()
            cur.execute("DELETE FROM respostas_entidade WHERE entidade_id=?", (int(ent.id),))
            rows = []
            for _, r in perguntas.iterrows():
                resp = respostas.get(int(r.id), "Nao")
                pts = pontos_respostas.get(int(r.id), 0)
                rows.append((int(ent.id), r.questionario, int(r.id), r.pergunta, resp, pts, data))
            cur.executemany("""INSERT INTO respostas_entidade(entidade_id,questionario,pergunta_id,pergunta,resposta,pontuacao,data_resposta)
                               VALUES(?,?,?,?,?,?,?)""", rows)
            cur.execute(
                """UPDATE entidades
                   SET status_qualificacao='BPF pendente', nivel=?, pontuacao=?, pontuacao_q1=?, pontuacao_q2=?
                   WHERE id=?""",
                (nivel, pontos, p_q1, p_q2, int(ent.id)),
            )
            c.commit()
        st.session_state.pop("geral_entidade_id", None)
        st.session_state.bpf_entidade_id = int(ent.id)
        detalhes = " | ".join(f"{bloco}: {pts}" for bloco, pts in pontos_por_bloco.items())
        st.success(f"Formulario Geral salvo. Entidade classificada como {nivel}. Pontuacao: {pontos}. {detalhes}. Abrindo BPF.")
        st.rerun()


def bpf_pendentes(entidade_id: Optional[int] = None):
    pendentes = q("SELECT * FROM entidades WHERE ativo=1 AND status_qualificacao='BPF pendente' ORDER BY id DESC")
    pendentes = filtrar_minhas_entidades(pendentes)
    if pendentes.empty:
        st.info("Nenhuma qualificação aguardando BPF.")
        return
    if entidade_id is not None:
        entidade_match = pendentes[pendentes.id == int(entidade_id)]
        if entidade_match.empty:
            st.session_state.pop("bpf_entidade_id", None)
            st.info("Esta entidade nÃ£o estÃ¡ mais aguardando BPF.")
            return
        ent = entidade_match.iloc[0]
        st.markdown(
            f'<span class="badge badge-blue">BPF de {ent.entidade}</span>',
            unsafe_allow_html=True,
        )
    else:
        default_idx = 0
        if "bpf_entidade_id" in st.session_state:
            matches = pendentes.index[pendentes.id == st.session_state.bpf_entidade_id].tolist()
            if matches:
                default_idx = pendentes.index.get_loc(matches[0])
        entidade_nome = st.selectbox("Entidade aguardando BPF", pendentes.entidade.tolist(), index=default_idx)
        ent = pendentes[pendentes.entidade == entidade_nome].iloc[0]
    perguntas = q("SELECT * FROM perguntas_bpf WHERE ativo=1 ORDER BY ordem")
    if perguntas.empty:
        st.warning("Nenhuma pergunta BPF cadastrada.")
        return
    with st.form("bpf"):
        st.subheader("Formulário BPF")
        respostas = {}
        pontos_respostas = {}
        for secao, secao_df in perguntas.groupby("secao", sort=False):
            with st.expander(secao or "BPF", expanded=False):
                for subsecao, sub_df in secao_df.groupby("subsecao", sort=False):
                    st.markdown(f"**{subsecao}**")
                    sub_respostas, sub_pontos = render_perguntas_bpf(sub_df, f"bpf_{int(ent.id)}_{subsecao}")
                    respostas.update(sub_respostas)
                    pontos_respostas.update(sub_pontos)
        observacao = st.text_area("Observação do BPF")
        c_cancelar, c_salvar = st.columns(2)
        cancelar = c_cancelar.form_submit_button("Cancelar e manter pendente", use_container_width=True)
        salvar = c_salvar.form_submit_button("Salvar BPF e concluir qualificação", use_container_width=True)
    if cancelar:
        st.info("BPF mantido em Aguardando finalizar.")
        go_to_main()
    if salvar:
        data = now_str()
        pontos_bpf = sum(pontos_respostas.values())
        with conn() as c:
            cur = c.cursor()
            rows = []
            for _, r in perguntas.iterrows():
                resp = respostas.get(int(r.id), "NA")
                pts = pontos_respostas.get(int(r.id), 0)
                rows.append((int(ent.id), int(r.id), r.pergunta, resp, pts, data))
            cur.executemany("INSERT INTO respostas_bpf(entidade_id,pergunta_id,pergunta,resposta,pontuacao,data_resposta) VALUES(?,?,?,?,?,?)", rows)
            cur.execute(
                "UPDATE entidades SET status_qualificacao='Concluída', pontuacao=COALESCE(pontuacao,0)+? WHERE id=?",
                (pontos_bpf, int(ent.id)),
            )
            cur.execute(
                "INSERT INTO historico_fluxo(protocolo,status_anterior,status_novo,usuario,data_movimento,observacao) VALUES(?,?,?,?,?,?)",
                (f"ENT-{int(ent.id)}", "BPF pendente", "Qualificação concluída", st.session_state.user["usuario"], data, observacao),
            )
            c.commit()
        st.success("BPF salvo. A entidade está qualificada e liberada para cursos.")
        st.session_state.pop("bpf_entidade_id", None)
        st.rerun()


def cursos_demandas():
    st.title("Cursos")
    aba_novo, aba_pendentes = st.tabs(["Novo curso", "Formulários pendentes"])
    with aba_novo:
        novo_curso_form()
    with aba_pendentes:
        pend = q("""SELECT p.protocolo,e.entidade,c.curso,p.status,p.data_abertura
                    FROM protocolos p
                    LEFT JOIN entidades e ON e.id=p.entidade_id
                    LEFT JOIN cursos c ON c.id=p.curso_id
                    WHERE p.status='Rascunho'
                    ORDER BY p.id DESC""")
        st.dataframe(pend, use_container_width=True, hide_index=True)


def novo_curso_form():
    ents = q("SELECT * FROM entidades WHERE ativo=1 AND nivel IS NOT NULL AND status_qualificacao='Concluída' ORDER BY entidade")
    if ents.empty:
        st.warning("Cadastre e finalize a qualificação/BPF de uma entidade primeiro.")
        return
    col1, col2, col3 = st.columns(3)
    with col1:
        entidade_nome = st.selectbox("1. Entidade", ents["entidade"].tolist())
    ent = ents[ents.entidade == entidade_nome].iloc[-1]
    with col2:
        area = st.selectbox("2. Área do curso", AREAS_CURSO)
    with col3:
        st.metric("Nível da entidade", ent.nivel)
    niveis = niveis_permitidos(ent.nivel)
    cursos = q("SELECT * FROM cursos WHERE area=? AND ativo=1 ORDER BY nivel,curso", (area,))
    cursos = cursos[cursos["nivel"].isin(niveis)]
    st.caption(f"Cursos liberados para nível {ent.nivel}: {', '.join(niveis)}")
    if not cursos.empty:
        cursos = cursos.copy()
        cursos["estoque_disponivel"] = cursos.apply(lambda r: estoque_disponivel(int(r.id), int(r.estoque_total or 0)), axis=1)
        cursos = cursos[cursos.estoque_disponivel > 0]
    if cursos.empty:
        st.warning("Não existem cursos com estoque disponível para essa área/nível.")
        return
    opcoes = [f"{r.curso} | {r.nivel} | estoque {int(r.estoque_disponivel)}" for _, r in cursos.iterrows()]
    escolha = st.selectbox("3. Curso disponível", opcoes)
    curso_nome = escolha.split(" | ")[0]
    curso = cursos[cursos.curso == curso_nome].iloc[0]
    with st.expander("Detalhes do curso", expanded=True):
        st.write(f"**Área:** {curso.area} | **Nível mínimo:** {curso.nivel} | **Carga horária:** {curso.carga_horaria or '-'} | **Estoque:** {int(curso.estoque_disponivel)}")
        st.write(curso.descricao or "Sem descrição cadastrada.")
    perguntas = curso_perguntas_com_alternativas(int(curso.id))
    with st.form("demanda"):
        st.subheader("Questionário da demanda")
        respostas = {}
        pontos_resposta = {}
        for _, r in perguntas.iterrows():
            alternativas = r.alternativas if "alternativas" in perguntas.columns else []
            if alternativas:
                labels = [a["alternativa"] for a in alternativas]
                escolha_resp = st.radio(r.pergunta, labels, horizontal=False, key=f"pc_alt_{r.id}")
                respostas[int(r.id)] = escolha_resp
                pontos_resposta[int(r.id)] = int(next(a["pontos"] for a in alternativas if a["alternativa"] == escolha_resp))
            else:
                resp = st.radio(r.pergunta, ["Não", "Sim"], horizontal=True, key=f"pc_{r.id}")
                respostas[int(r.id)] = resp
                pontos_resposta[int(r.id)] = int(r.pontos_sim) if resp == "Sim" else 0
        obs = st.text_area("Observação inicial")
        c_cancelar, c_enviar = st.columns(2)
        cancelar = c_cancelar.form_submit_button("Cancelar", use_container_width=True)
        enviar = c_enviar.form_submit_button("Salvar e iniciar fluxo", use_container_width=True)
    if cancelar:
        st.info("Formulário cancelado. Nenhum fluxo foi iniciado.")
        go_to_main()
    if enviar:
        if estoque_disponivel(int(curso.id), int(curso.estoque_total or 0)) <= 0:
            st.error("Este curso ficou sem estoque disponível. Escolha outro curso.")
            return
        pontos = sum(pontos_resposta.values())
        protocolo = f"BA-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        data = now_str()
        owner = get_owner(area, "Administrativo")
        with conn() as c:
            cur = c.cursor()
            cur.execute("""INSERT INTO protocolos(protocolo,entidade_id,curso_id,area,pontuacao_curso,status,etapa_atual,responsavel_atual,solicitante_nome,solicitante_email,data_abertura,data_atualizacao,observacao,os_modelo_nome,os_modelo_path)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (protocolo, int(ent.id), int(curso.id), area, pontos, "Validação Administrativa", "Administrativo", owner.get("usuario", "Administrativo"), st.session_state.user["nome"], st.session_state.user.get("email", ""), data, data, obs, "Modelo_OS.docx", str(OS_TEMPLATE_PATH)))
            rows = []
            for _, r in perguntas.iterrows():
                resp = respostas.get(int(r.id), "Não")
                pts = pontos_resposta.get(int(r.id), 0)
                rows.append((protocolo, int(r.id), r.pergunta, resp, pts, data))
            cur.executemany("INSERT INTO respostas_curso(protocolo,pergunta_id,pergunta,resposta,pontuacao,data_resposta) VALUES(?,?,?,?,?,?)", rows)
            cur.execute("INSERT INTO historico_fluxo(protocolo,status_anterior,status_novo,usuario,data_movimento,observacao) VALUES(?,?,?,?,?,?)", (protocolo, "", "Validação Administrativa", st.session_state.user["usuario"], data, obs))
            c.commit()
        notificar_etapa(protocolo, area, "Administrativo", "Validação Administrativa", st.session_state.user.get("email", ""), obs)
        st.success(f"Protocolo criado: {protocolo}. A demanda foi enviada para validação administrativa.")
        go_to_main()


def consultar_status():
    st.title("Consultar Status")
    df = q("""SELECT p.protocolo,e.entidade,c.curso,p.area,p.pontuacao_curso,p.status,p.responsavel_atual,p.data_abertura,p.data_atualizacao,p.data_agendada,p.observacao,
                     p.os_modelo_nome,p.os_modelo_path,p.os_preenchida_nome,p.os_preenchida_path,p.os_preenchida_em,p.os_preenchida_por
              FROM protocolos p
              LEFT JOIN entidades e ON e.id=p.entidade_id
              LEFT JOIN cursos c ON c.id=p.curso_id
              ORDER BY p.id DESC""")
    if df.empty:
        st.info("Nenhum fluxo iniciado.")
        return
    status = st.multiselect("Filtrar Status", STATUS_FLUXO, default=[], placeholder="Filtrar Status")
    view = df[df.status.isin(status)] if status else df
    resumo_cols = ["protocolo", "entidade", "curso", "area", "status", "responsavel_atual", "data_atualizacao"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Protocolos", len(view))
    c2.metric("Em andamento", len(view[~view.status.isin(["Finalizado", "Cancelado", "Reprovado"])]))
    c3.metric("Finalizados", len(view[view.status == "Finalizado"]))
    c4.metric("Cancelados", len(view[view.status.isin(["Cancelado", "Reprovado"])]))
    tabela = view[resumo_cols].rename(
        columns={
            "protocolo": "Protocolo",
            "entidade": "Entidade",
            "curso": "Curso",
            "area": "Área",
            "status": "Status",
            "responsavel_atual": "Responsável atual",
            "data_atualizacao": "Data Atualização",
        }
    )
    st.dataframe(tabela, use_container_width=True, hide_index=True)
    return
    st.subheader("Detalhar")
    for _, row in view.iterrows():
        titulo = f"{row.protocolo} · {row.entidade or '-'} · {row.status}"
        with st.expander(titulo, expanded=False):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Área", row.area or "-")
            c2.metric("Pontuação", int(row.pontuacao_curso or 0))
            c3.metric("Responsável", row.responsavel_atual or "-")
            c4.metric("Agendamento", row.data_agendada or "-")
            st.write(f"**Curso:** {row.curso or '-'}")
            st.write(f"**Observação:** {row.observacao or '-'}")
            render_ordem_servico(row, allow_upload=False)
            hist = q("SELECT status_anterior,status_novo,usuario,data_movimento,observacao FROM historico_fluxo WHERE protocolo=? ORDER BY id", (row.protocolo,))
            st.dataframe(hist, use_container_width=True, hide_index=True)


def aprovacoes_page():
    st.title("Minhas Aprovações")
    user = st.session_state.user
    df = q("""SELECT p.*, e.entidade, e.nivel AS nivel_entidade,
                     COALESCE(e.pontuacao_q1,0) + COALESCE(e.pontuacao_q2,0) AS pontuacao_geral,
                     COALESCE(bpf.pontuacao_bpf,0) AS pontuacao_bpf,
                     c.curso, c.nivel AS nivel_curso
              FROM protocolos p
              LEFT JOIN entidades e ON e.id=p.entidade_id
              LEFT JOIN cursos c ON c.id=p.curso_id
              LEFT JOIN (
                  SELECT entidade_id, SUM(COALESCE(pontuacao,0)) AS pontuacao_bpf
                  FROM respostas_bpf
                  GROUP BY entidade_id
              ) bpf ON bpf.entidade_id=p.entidade_id
              ORDER BY p.id DESC""")
    if df.empty:
        st.warning("Nenhum protocolo criado.")
        return
    if not is_admin_or_moderador(user):
        df = df[df["status"].apply(lambda s: perfil_pode_atuar(user["perfil"], s))]
        if "responsavel_atual" in df.columns:
            df = df[
                (df["responsavel_atual"].isna())
                | (df["responsavel_atual"] == "")
                | (df["responsavel_atual"] == user["usuario"])
                | (df["responsavel_atual"] == user["perfil"])
            ]
    if df.empty:
        st.info("Nenhuma demanda pendente para o seu perfil.")
        return
    c1, c2, c3 = st.columns(3)
    c1.metric("Pendentes", len(df))
    c2.metric("Perfil", user["perfil"])
    c3.metric("Usuário", user["usuario"])
    status_filtro = st.multiselect("Filtrar Status", sorted(df.status.unique().tolist()), placeholder="Filtrar Status")
    view = df[df.status.isin(status_filtro)] if status_filtro else df
    tabela_aprovacoes = view[[
        "protocolo",
        "entidade",
        "nivel_entidade",
        "curso",
        "area",
        "pontuacao_geral",
        "pontuacao_bpf",
        "pontuacao_curso",
        "status",
        "responsavel_atual",
        "data_abertura",
    ]].rename(
        columns={
            "protocolo": "Protocolo",
            "entidade": "Entidade",
            "nivel_entidade": "Nível qualificação",
            "curso": "Curso",
            "area": "Área",
            "pontuacao_geral": "Pontuação Geral",
            "pontuacao_bpf": "Pontuação BPF",
            "pontuacao_curso": "Pontuação curso",
            "status": "Status",
            "responsavel_atual": "Responsável atual",
            "data_abertura": "Data Abertura",
        }
    )
    st.dataframe(tabela_aprovacoes, use_container_width=True, hide_index=True)
    if view.empty:
        st.info("Nenhum protocolo encontrado para o filtro selecionado.")
        return
    prot = st.selectbox("Selecionar protocolo", view.protocolo.tolist(), index=None, placeholder="Selecionar protocolo")
    if not prot:
        return
    row = df[df.protocolo == prot].iloc[0]
    st.markdown(f"### {prot} {badge(row.status)}", unsafe_allow_html=True)
    st.write(f"**Entidade:** {row.entidade} | **Nível entidade:** {row.nivel_entidade} | **Curso:** {row.curso} | **Área:** {row.area}")
    render_formularios_protocolo(row)
    st.subheader("Histórico")
    st.dataframe(historico_protocolo_df(prot), use_container_width=True, hide_index=True)
    st.divider()
    # Ordem de serviço agora fica dentro do bloco de formulários e documentos.
    if status_final_fluxo(row.status):
        st.warning("Este protocolo está encerrado e não permite novas ações.")
        return
    data_agendada = None
    if row.status == "Agendamento":
        data_base = parse_data_agendada(row.data_agendada)
        col_data, col_hora = st.columns(2)
        data_sel = col_data.date_input("Data agendada", value=data_base.date(), format="DD/MM/YYYY")
        hora_sel = col_hora.time_input("Hora agendada", value=data_base.time().replace(second=0, microsecond=0))
        data_agendada = datetime.combine(data_sel, hora_sel).strftime("%Y-%m-%d %H:%M:%S")
    obs = st.text_area("Observação da decisão")
    pode = perfil_pode_atuar(user["perfil"], row.status)
    if not pode:
        st.warning("Seu perfil não pode movimentar essa etapa.")
        return
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Aprovar / Avançar", use_container_width=True):
            novo_status, nova_etapa = next_step(row.status)
            owner = get_owner(row.area, nova_etapa) if nova_etapa != "Finalizado" else {"usuario": "Finalizado"}
            data = now_str()
            extra = ", data_agendada=?" if row.status == "Agendamento" else ""
            if row.status == "Agendamento":
                exec_sql(f"UPDATE protocolos SET status=?, etapa_atual=?, responsavel_atual=?, data_atualizacao=?{extra} WHERE protocolo=?", (novo_status, nova_etapa, owner.get("usuario", nova_etapa), data, data_agendada, prot))
            else:
                exec_sql("UPDATE protocolos SET status=?, etapa_atual=?, responsavel_atual=?, data_atualizacao=? WHERE protocolo=?", (novo_status, nova_etapa, owner.get("usuario", nova_etapa), data, prot))
            if texto_chave(row.status) == "analise tecnica" and novo_status == "Agendamento":
                gerar_os_preenchida(prot, user, data, obs)
            exec_sql("INSERT INTO historico_fluxo(protocolo,status_anterior,status_novo,usuario,data_movimento,observacao) VALUES(?,?,?,?,?,?)", (prot, row.status, novo_status, user["usuario"], data, obs))
            notificar_etapa(prot, row.area, nova_etapa, novo_status, row.solicitante_email or "", obs)
            st.success("Fluxo atualizado.")
            st.rerun()
    with c2:
        if st.button("Reprovar", use_container_width=True):
            data = now_str()
            exec_sql("UPDATE protocolos SET status='Reprovado', etapa_atual='Reprovado', responsavel_atual='Reprovado', data_atualizacao=? WHERE protocolo=?", (data, prot))
            exec_sql("INSERT INTO historico_fluxo(protocolo,status_anterior,status_novo,usuario,data_movimento,observacao) VALUES(?,?,?,?,?,?)", (prot, row.status, "Reprovado", user["usuario"], data, obs))
            notificar_etapa(prot, row.area, "Reprovado", "Reprovado", row.solicitante_email or "", obs)
            st.error("Protocolo reprovado.")
            st.rerun()
    with c3:
        if st.button("Cancelar", use_container_width=True):
            data = now_str()
            exec_sql("UPDATE protocolos SET status='Cancelado', etapa_atual='Cancelado', responsavel_atual='Cancelado', data_atualizacao=? WHERE protocolo=?", (data, prot))
            exec_sql("INSERT INTO historico_fluxo(protocolo,status_anterior,status_novo,usuario,data_movimento,observacao) VALUES(?,?,?,?,?,?)", (prot, row.status, "Cancelado", user["usuario"], data, obs))
            notificar_etapa(prot, row.area, "Cancelado", "Cancelado", row.solicitante_email or "", obs)
            st.error("Protocolo cancelado.")
            st.rerun()
    return


def relatorios():
    st.title("Relatórios")
    df = q("""SELECT p.*, e.entidade, e.nivel AS nivel_entidade, c.curso, c.nivel AS nivel_curso
              FROM protocolos p
              LEFT JOIN entidades e ON e.id=p.entidade_id
              LEFT JOIN cursos c ON c.id=p.curso_id""")
    if df.empty:
        st.info("Sem dados para relatório.")
        return
    st.download_button("Baixar protocolos CSV", df.to_csv(index=False, sep=";").encode("utf-8-sig"), "protocolos_bahia.csv", "text/csv")
    st.plotly_chart(px.bar(df, x="status", title="Quantidade por status"), use_container_width=True)
    st.plotly_chart(px.bar(df, x="area", color="status", title="Protocolos por área"), use_container_width=True)
    st.dataframe(df, use_container_width=True, hide_index=True)


def save_table_editor_grid(table: str, edited: pd.DataFrame, original: pd.DataFrame):
    inserts, updates = save_table_editor(table, edited, original)
    deletes = 0
    if original.empty or "id" not in original.columns or "id" not in edited.columns:
        return inserts, updates, deletes

    original_ids = {int(v) for v in original["id"].dropna().tolist()}
    edited_ids = {int(v) for v in edited["id"].dropna().tolist() if not pd.isna(v)}
    removed_ids = sorted(original_ids - edited_ids)
    if not removed_ids:
        return inserts, updates, deletes

    cols = table_columns(table)
    with conn() as c:
        cur = c.cursor()
        for row_id in removed_ids:
            if "ativo" in cols:
                cur.execute(f"UPDATE {table} SET ativo=? WHERE id=?", (False, row_id))
            else:
                cur.execute(f"DELETE FROM {table} WHERE id=?", (row_id,))
            deletes += 1
        c.commit()
    return inserts, updates, deletes


def render_cadastro_grid(label: str, table: str, sql: str | None = None, disabled: list[str] | None = None):
    df = q(sql or f"SELECT * FROM {table} ORDER BY id DESC")
    st.caption("Edite direto na tabela. Para adicionar, use a linha nova no final. Para remover, apague a linha e salve.")
    edited = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        disabled=disabled or (["id"] if "id" in df.columns else None),
        key=f"cadastro_grid_{table}_{label}",
    )
    if st.button("Salvar tabela", use_container_width=True, key=f"salvar_grid_{table}_{label}"):
        inserts, updates, deletes = save_table_editor_grid(table, edited, df)
        st.success(f"Alterações salvas. {updates} atualizados, {inserts} adicionados, {deletes} removidos/desativados.")
        st.rerun()


def cadastros_base():
    st.title("Cadastros Base")
    t1, t2, t3, t4, t5, t6, t7 = st.tabs(["Cursos", "Perguntas Entidade", "Perguntas BPF", "Perguntas Curso", "Alternativas Curso", "Owners por Área", "Entidades"])
    with t1:
        render_cadastro_grid("Cursos", "cursos", "SELECT * FROM cursos ORDER BY area,nivel,curso")
    with t2:
        render_cadastro_grid("Perguntas Entidade", "perguntas_qualificacao", "SELECT * FROM perguntas_qualificacao ORDER BY questionario,ordem")
    with t3:
        render_cadastro_grid("Perguntas BPF", "perguntas_bpf", "SELECT * FROM perguntas_bpf ORDER BY secao,subsecao,ordem")
    with t4:
        render_cadastro_grid("Perguntas Curso", "perguntas_curso", "SELECT * FROM perguntas_curso ORDER BY curso_id,ordem")
    with t5:
        render_cadastro_grid("Alternativas Curso", "alternativas_curso", "SELECT * FROM alternativas_curso ORDER BY pergunta_id,ordem")
    with t6:
        render_cadastro_grid("Owners por Área", "owners_area", "SELECT * FROM owners_area ORDER BY area,etapa,nome")
    with t7:
        render_cadastro_grid("Entidades", "entidades", "SELECT * FROM entidades ORDER BY entidade")
    return
    with t2:
        with st.form("add_pq"):
            questionario = st.selectbox("Questionário", ["Questionário 1", "Questionário 2"])
            ordem = st.number_input("Ordem", 1, 999, 1)
            pergunta = st.text_area("Pergunta")
            pontos = st.number_input("Pontos SIM", 0, 100, 5)
            if st.form_submit_button("Cadastrar pergunta") and pergunta:
                exec_sql("INSERT INTO perguntas_qualificacao(questionario,ordem,pergunta,pontos_sim) VALUES(?,?,?,?)", (questionario, ordem, pergunta, pontos))
                st.success("Pergunta cadastrada.")
                st.rerun()
        st.dataframe(q("SELECT * FROM perguntas_qualificacao ORDER BY questionario,ordem"), use_container_width=True, hide_index=True)
    with t3:
        with st.form("add_bpf"):
            ordem = st.number_input("Ordem BPF", 1, 999, 1)
            pergunta = st.text_area("Pergunta BPF")
            pontos = st.number_input("Pontos SIM BPF", 0, 100, 5)
            if st.form_submit_button("Cadastrar pergunta BPF") and pergunta:
                exec_sql("INSERT INTO perguntas_bpf(ordem,pergunta,pontos_sim) VALUES(?,?,?)", (ordem, pergunta, pontos))
                st.success("Pergunta BPF cadastrada.")
                st.rerun()
        st.dataframe(q("SELECT * FROM perguntas_bpf ORDER BY ordem"), use_container_width=True, hide_index=True)
    with t4:
        cursos = q("SELECT * FROM cursos WHERE ativo=1 ORDER BY curso")
        if not cursos.empty:
            with st.form("add_pc"):
                curso_nome = st.selectbox("Curso", cursos.curso.tolist())
                ordem = st.number_input("Ordem ", 1, 999, 1)
                pergunta = st.text_area("Pergunta ")
                pontos = st.number_input("Pontos SIM ", 0, 100, 5)
                if st.form_submit_button("Cadastrar pergunta do curso") and pergunta:
                    cid = int(cursos[cursos.curso == curso_nome].iloc[0].id)
                    exec_sql("INSERT INTO perguntas_curso(curso_id,ordem,pergunta,pontos_sim) VALUES(?,?,?,?)", (cid, ordem, pergunta, pontos))
                    st.success("Pergunta cadastrada.")
                    st.rerun()
        st.dataframe(q("SELECT pc.id,c.curso,pc.ordem,pc.pergunta,pc.pontos_sim,pc.ativo FROM perguntas_curso pc LEFT JOIN cursos c ON c.id=pc.curso_id ORDER BY c.curso,pc.ordem"), use_container_width=True, hide_index=True)
    with t5:
        perguntas = q("""SELECT pc.id, c.curso, pc.ordem, pc.pergunta
                         FROM perguntas_curso pc
                         LEFT JOIN cursos c ON c.id=pc.curso_id
                         WHERE pc.ativo=1
                         ORDER BY c.curso, pc.ordem""")
        if not perguntas.empty:
            with st.form("add_alt"):
                labels = [f"{int(r.id)} | {r.curso} | {r.pergunta}" for _, r in perguntas.iterrows()]
                pergunta_label = st.selectbox("Pergunta", labels)
                pergunta_id = int(pergunta_label.split(" | ")[0])
                ordem = st.number_input("Ordem alternativa", 1, 999, 1)
                alternativa = st.text_input("Alternativa")
                pontos = st.number_input("Pontuação da alternativa", 0, 1000, 0)
                if st.form_submit_button("Cadastrar alternativa") and alternativa:
                    exec_sql("INSERT INTO alternativas_curso(pergunta_id,ordem,alternativa,pontos) VALUES(?,?,?,?)", (pergunta_id, ordem, alternativa, pontos))
                    st.success("Alternativa cadastrada.")
                    st.rerun()
        st.dataframe(q("""SELECT a.id, c.curso, pc.pergunta, a.ordem, a.alternativa, a.pontos, a.ativo
                          FROM alternativas_curso a
                          LEFT JOIN perguntas_curso pc ON pc.id=a.pergunta_id
                          LEFT JOIN cursos c ON c.id=pc.curso_id
                          ORDER BY c.curso, pc.ordem, a.ordem"""), use_container_width=True, hide_index=True)
    with t6:
        with st.form("add_owner"):
            c1, c2, c3 = st.columns(3)
            with c1:
                area = st.selectbox("Área ", AREAS_CURSO)
                etapa = st.selectbox("Etapa", ETAPAS_APROVACAO)
            with c2:
                nome = st.text_input("Nome do owner")
                email = st.text_input("E-mail")
            with c3:
                usuario = st.text_input("Usuário do sistema")
            if st.form_submit_button("Cadastrar owner") and nome:
                exec_sql("INSERT INTO owners_area(area,etapa,nome,email,usuario) VALUES(?,?,?,?,?)", (area, etapa, nome, email, usuario))
                st.success("Owner cadastrado.")
                st.rerun()
        st.dataframe(q("SELECT * FROM owners_area ORDER BY area,etapa"), use_container_width=True, hide_index=True)
    with t7:
        entidades = q("SELECT id,entidade,nivel,status_qualificacao,pontuacao,email_responsavel,ativo FROM entidades ORDER BY entidade")
        if entidades.empty:
            st.info("Nenhuma entidade cadastrada.")
        else:
            with st.form("edit_entidade"):
                labels = [f"{int(r.id)} | {r.entidade}" for _, r in entidades.iterrows()]
                entidade_label = st.selectbox("Entidade", labels)
                entidade_id = int(entidade_label.split(" | ")[0])
                atual = entidades[entidades.id == entidade_id].iloc[0]
                nivel = st.selectbox("Nível", NIVEIS, index=NIVEIS.index(atual.nivel) if atual.nivel in NIVEIS else 0)
                status = st.selectbox("Status da qualificação", ["BPF pendente", "Concluída", "Cancelada"], index=["BPF pendente", "Concluída", "Cancelada"].index(atual.status_qualificacao) if atual.status_qualificacao in ["BPF pendente", "Concluída", "Cancelada"] else 1)
                ativo = st.checkbox("Ativa", value=bool(atual.ativo))
                if st.form_submit_button("Atualizar entidade"):
                    exec_sql("UPDATE entidades SET nivel=?,status_qualificacao=?,ativo=? WHERE id=?", (nivel, status, 1 if ativo else 0, entidade_id))
                    st.success("Entidade atualizada.")
                    st.rerun()
            st.dataframe(entidades, use_container_width=True, hide_index=True)


def usuarios_page():
    st.title("Usuários")
    with st.form("user"):
        c1, c2, c3 = st.columns(3)
        with c1:
            nome = st.text_input("Nome")
            usuario = st.text_input("Usuário")
        with c2:
            email = st.text_input("E-mail")
            senha = st.text_input("Senha", type="password")
        with c3:
            perfil = st.selectbox("Perfil", ["Administrador", "Administrativo", "Técnico", "Agendamento", "Executor", "Consulta"])
        if st.form_submit_button("Criar usuário") and nome and usuario and senha:
            try:
                exec_sql("INSERT INTO usuarios(nome,usuario,senha_hash,perfil,email) VALUES(?,?,?,?,?)", (nome, usuario, hash_pw(senha), perfil, email))
                st.success("Usuário criado.")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("Usuário já existe.")
    st.dataframe(q("SELECT id,nome,usuario,email,perfil,ativo FROM usuarios ORDER BY id"), use_container_width=True, hide_index=True)


def notificacoes_page():
    st.title("Movimentações e Notificações")
    aba_mov, aba_email = st.tabs(["Movimentações", "E-mails"])
    with aba_mov:
        hist = q("""SELECT h.protocolo,h.status_anterior,h.status_novo,h.usuario,h.data_movimento,h.observacao,
                           e.entidade,c.curso
                    FROM historico_fluxo h
                    LEFT JOIN protocolos p ON p.protocolo=h.protocolo
                    LEFT JOIN entidades e ON e.id=p.entidade_id
                    LEFT JOIN cursos c ON c.id=p.curso_id
                    ORDER BY h.id DESC""")
        if hist.empty:
            st.info("Nenhuma movimentação registrada.")
        else:
            st.dataframe(hist, use_container_width=True, hide_index=True)
    with aba_email:
        df = q("SELECT * FROM notificacoes ORDER BY id DESC")
        if df.empty:
            st.info("Nenhuma notificação registrada.")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)


def editor_tabelas_page():
    st.title("Editor de Dados")
    st.caption("Edite registros existentes ou adicione novas linhas nas tabelas administrativas.")
    tabela_label = st.selectbox("Tabela", list(EDITABLE_TABLES.keys()))
    table = EDITABLE_TABLES[tabela_label]
    df = q(f"SELECT * FROM {table} ORDER BY id DESC")
    busca = st.text_input("Buscar nesta tabela", key=f"busca_{table}")
    view = df.copy()
    if busca and not view.empty:
        mask = pd.Series(False, index=view.index)
        for col in view.columns:
            mask = mask | view[col].astype(str).str.contains(busca, case=False, na=False)
        view = view[mask]

    st.markdown(f'<span class="badge badge-blue">{len(view)} registros</span>', unsafe_allow_html=True)
    edited = st.data_editor(
        view,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        disabled=["id"] if "id" in view.columns else None,
        key=f"editor_{table}",
    )
    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("Salvar tabela", use_container_width=True, key=f"salvar_{table}"):
            inserts, updates = save_table_editor(table, edited, df)
            st.success(f"Alterações salvas. {updates} atualizados, {inserts} adicionados.")
            st.rerun()
    with c2:
        st.info("Para remover um registro sem apagar histórico, prefira alterar a coluna ativo para 0 quando existir.")


def configuracoes_page():
    st.title("Configurações")
    tabs = st.tabs(["Cadastros Base", "Editor de Dados", "Usuários", "Notificações"])
    with tabs[0]:
        cadastros_base()
    with tabs[1]:
        editor_tabelas_page()
    with tabs[2]:
        usuarios_page()
    with tabs[3]:
        notificacoes_page()


def usuarios_page():
    st.title("Usuários")
    perfis = ["Pendente", "Administrador", "Moderador", "Administrativo", "Técnico", "Agendamento", "Executor", "Consulta"]
    with st.form("user"):
        c1, c2, c3 = st.columns(3)
        with c1:
            nome = st.text_input("Nome")
            usuario = st.text_input("Usuário")
        with c2:
            email = st.text_input("E-mail")
            senha = st.text_input("Senha", type="password")
        with c3:
            perfil = st.selectbox("Perfil", perfis, index=perfis.index("Pendente"))
        if st.form_submit_button("Criar usuário") and nome and usuario and senha:
            try:
                pendente = perfil == "Pendente"
                exec_sql(
                    """INSERT INTO usuarios(nome,usuario,senha_hash,perfil,email,acesso_pendente,ativo)
                       VALUES(?,?,?,?,?,?,?)""",
                    (nome, usuario, hash_pw(senha), perfil, email, pendente, True),
                )
                st.success("Usuário criado.")
                st.rerun()
            except Exception:
                st.error("Usuário já existe ou não pôde ser criado.")

    users = q("SELECT id,nome,usuario,email,perfil,acesso_pendente,trocar_senha_obrigatorio,ativo FROM usuarios ORDER BY id")
    if users.empty:
        st.info("Nenhum usuário cadastrado.")
        return

    st.subheader("Liberar e ajustar acessos")
    edited = st.data_editor(
        users,
        use_container_width=True,
        hide_index=True,
        disabled=["id", "usuario", "trocar_senha_obrigatorio"],
        column_config={
            "perfil": st.column_config.SelectboxColumn("Perfil", options=perfis, required=True),
            "ativo": st.column_config.CheckboxColumn("Ativo"),
            "acesso_pendente": st.column_config.CheckboxColumn("Acesso pendente"),
        },
        key="usuarios_editor_acesso",
    )
    if st.button("Salvar alterações de usuários", use_container_width=True):
        original = users.set_index("id")
        updates = 0
        with conn() as c:
            cur = c.cursor()
            for _, row in edited.iterrows():
                user_id = int(row["id"])
                perfil = txt_value(row.get("perfil")) or "Pendente"
                acesso_pendente = bool_db(row.get("acesso_pendente")) or perfil == "Pendente"
                ativo = bool_db(row.get("ativo"))
                original_row = original.loc[user_id]
                changed = (
                    txt_value(original_row.get("nome")) != txt_value(row.get("nome"))
                    or txt_value(original_row.get("email")) != txt_value(row.get("email"))
                    or txt_value(original_row.get("perfil")) != perfil
                    or bool_db(original_row.get("acesso_pendente")) != acesso_pendente
                    or bool_db(original_row.get("ativo")) != ativo
                )
                if changed:
                    cur.execute(
                        "UPDATE usuarios SET nome=?, email=?, perfil=?, acesso_pendente=?, ativo=? WHERE id=?",
                        (row.get("nome"), row.get("email"), perfil, acesso_pendente, ativo, user_id),
                    )
                    updates += 1
            c.commit()
        st.success(f"Alterações salvas. {updates} usuário(s) atualizado(s).")
        st.rerun()


def login():
    st.markdown(f"# {APP_TITLE}")
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown('<div class="bahia-card">', unsafe_allow_html=True)
        st.markdown("### Acesso ao sistema")
        st.caption("Entre para acompanhar qualificações, cursos e fluxos.")

        reset_user_id = st.session_state.get("password_reset_user_id")
        if reset_user_id:
            u_reset = q("SELECT * FROM usuarios WHERE id=? AND ativo=1", (int(reset_user_id),))
            if u_reset.empty:
                st.session_state.pop("password_reset_user_id", None)
                st.error("Sessão de troca de senha expirada.")
                st.rerun()
            reset_user = dict(u_reset.iloc[0])
            st.info(f"Cadastre uma nova senha para {reset_user.get('email') or reset_user.get('usuario')}.")
            nova_senha = st.text_input("Nova senha", type="password")
            confirmar_senha = st.text_input("Confirmar nova senha", type="password")
            if st.button("Salvar nova senha", use_container_width=True):
                if len(nova_senha or "") < 6:
                    st.error("A nova senha precisa ter pelo menos 6 caracteres.")
                elif nova_senha != confirmar_senha:
                    st.error("As senhas não conferem.")
                else:
                    exec_sql(
                        """UPDATE usuarios
                           SET senha_hash=?, senha_temporaria=0, trocar_senha_obrigatorio=0
                           WHERE id=?""",
                        (hash_pw(nova_senha), int(reset_user["id"])),
                    )
                    atualizado = dict(q("SELECT * FROM usuarios WHERE id=?", (int(reset_user["id"]),)).iloc[0])
                    notificar_moderadores_novo_usuario(atualizado)
                    st.session_state.pop("password_reset_user_id", None)
                    st.session_state.user = atualizado
                    st.success("Senha cadastrada. Seu acesso está aguardando definição de perfil por um moderador.")
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            return

        usuario = st.text_input("E-mail ou usuário")
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar", use_container_width=True):
            u = usuario_por_login(usuario)
            if u.empty and "@" in txt_value(usuario):
                temp, _ = criar_usuario_pendente(usuario)
                st.success("Primeiro acesso criado. Enviamos uma senha temporária para seu e-mail.")
                if not emails_moderadores():
                    st.caption(f"Ambiente local: senha temporária {temp}")
            elif not u.empty and u.iloc[0]["senha_hash"] == hash_pw(senha):
                user = dict(u.iloc[0])
                if bool_db(user.get("trocar_senha_obrigatorio")) or bool_db(user.get("senha_temporaria")):
                    st.session_state.password_reset_user_id = int(user["id"])
                    st.rerun()
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")
        st.caption("Demo: admin / admin123")
        st.markdown('</div>', unsafe_allow_html=True)


def top_nav():
    user = st.session_state.user
    initials = "".join(part[:1] for part in str(user.get("nome", "")).split()[:2]).upper() or "U"
    st.sidebar.markdown(
        f"""
        <div class="sidebar-brand">
          <div class="brand-logos">{logo_box(1)}{logo_box(2)}</div>
          <div>
            <div class="brand-title">Sistema Bahia</div>
            <div class="brand-subtitle">Governança & Qualificação</div>
          </div>
        </div>
        <div class="user-chip">
          <div><span class="avatar">{initials}</span><strong>{user.get('nome') or user.get('email') or user.get('usuario')}</strong></div>
          <div class="brand-subtitle">{user.get('perfil')} · {user.get('usuario')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    menu = ["Tela principal", "Qualificar Nova Entidade", "Cursos", "Consultar Status"]
    if perfil_tem_aprovacoes(user):
        menu += ["Minhas Aprovações"]
    if is_admin_or_moderador(user):
        menu += ["Entidades", "Configurações"]
    current_page = st.session_state.pop("next_nav_page", st.session_state.get("nav_radio", "Tela principal"))
    if current_page not in menu:
        current_page = "Tela principal"
    st.session_state.nav_radio = current_page
    page = st.sidebar.radio("Menu principal", menu, index=menu.index(current_page), key="nav_radio", label_visibility="collapsed")
    if bool_db(user.get("acesso_pendente")):
        st.sidebar.info("Acesso aguardando definição de perfil por um moderador.")
    if st.sidebar.button("Sair", key="logout_top", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    st.markdown(
        f"""
        <div class="topbar">
          <div class="topbar-title">{APP_TITLE}</div>
          <div class="topbar-subtitle">Sistema Bahia · {user.get('perfil')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return page


def login():
    st.markdown(
        f"""
        <div class="login-shell">
          <div class="login-hero-bar">
            <div class="login-hero-title">{APP_TITLE}</div>
            <div class="login-hero-subtitle">Sistema Bahia</div>
          </div>
          {login_logo(1)}
          {login_logo(2)}
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns([1, 1.05, 1])
    with c2:
        st.markdown("### Acesso ao sistema")
        st.caption("Entre para acompanhar qualificações, cursos e fluxos.")

        reset_user_id = st.session_state.get("password_reset_user_id")
        if reset_user_id:
            u_reset = q("SELECT * FROM usuarios WHERE id=? AND ativo=1", (int(reset_user_id),))
            if u_reset.empty:
                st.session_state.pop("password_reset_user_id", None)
                st.error("Sessão de troca de senha expirada.")
                st.rerun()
            reset_user = dict(u_reset.iloc[0])
            st.info(f"Cadastre uma nova senha para {reset_user.get('email') or reset_user.get('usuario')}.")
            nova_senha = st.text_input("Nova senha", type="password")
            confirmar_senha = st.text_input("Confirmar nova senha", type="password")
            if st.button("Salvar nova senha", use_container_width=True):
                if len(nova_senha or "") < 6:
                    st.error("A nova senha precisa ter pelo menos 6 caracteres.")
                elif nova_senha != confirmar_senha:
                    st.error("As senhas não conferem.")
                else:
                    exec_sql(
                        """UPDATE usuarios
                           SET senha_hash=?, senha_temporaria=0, trocar_senha_obrigatorio=0
                           WHERE id=?""",
                        (hash_pw(nova_senha), int(reset_user["id"])),
                    )
                    atualizado = dict(q("SELECT * FROM usuarios WHERE id=?", (int(reset_user["id"]),)).iloc[0])
                    notificar_moderadores_novo_usuario(atualizado)
                    st.session_state.pop("password_reset_user_id", None)
                    st.session_state.user = atualizado
                    st.success("Senha cadastrada. Seu acesso está aguardando definição de perfil por um moderador.")
                    st.rerun()
            return

        usuario = st.text_input("E-mail ou usuário")
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar", use_container_width=True):
            u = usuario_por_login(usuario)
            if u.empty and "@" in txt_value(usuario):
                temp, _ = criar_usuario_pendente(usuario)
                st.success("Primeiro acesso criado. Enviamos uma senha temporária para seu e-mail.")
                if not emails_moderadores():
                    st.caption(f"Ambiente local: senha temporária {temp}")
            elif not u.empty and u.iloc[0]["senha_hash"] == hash_pw(senha):
                user = dict(u.iloc[0])
                if bool_db(user.get("trocar_senha_obrigatorio")) or bool_db(user.get("senha_temporaria")):
                    st.session_state.password_reset_user_id = int(user["id"])
                    st.rerun()
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")


init_db()
if "user" not in st.session_state:
    login()
else:
    page = top_nav()
    pages = {
        "Tela principal": tela_principal,
        "Qualificar Nova Entidade": nova_qualificacao_fluxo,
        "Cursos": cursos_demandas,
        "Consultar Status": consultar_status,
        "Minhas Aprovações": aprovacoes_page,
        "Entidades": entidades_page,
        "Configurações": configuracoes_page,
    }
    pages[page]()
