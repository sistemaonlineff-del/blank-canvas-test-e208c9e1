import sqlite3
from pathlib import Path
from datetime import datetime
import hashlib

import pandas as pd
import plotly.express as px
import streamlit as st

APP_TITLE = "Governança e Qualificação de Demandas - Bahia"
DB_PATH = Path("bahia.db")

st.set_page_config(page_title=APP_TITLE, page_icon="🏛️", layout="wide")

CSS = """
<style>
:root { --bg:#0b1220; --card:#111827; --muted:#94a3b8; --line:#243044; --accent:#38bdf8; }
.stApp { background: radial-gradient(circle at top left, #13213a 0, #0b1220 35%, #050816 100%); color: #e5e7eb; }
.block-container { padding-top: 1.3rem; }
[data-testid="stSidebar"] { background: #07101f; border-right: 1px solid #1f2937; }
h1, h2, h3 { color: #f8fafc; }
.bahia-card { background: rgba(17,24,39,.88); border: 1px solid #273244; border-radius: 18px; padding: 18px; box-shadow: 0 10px 28px rgba(0,0,0,.25); }
.kpi { font-size: 34px; font-weight: 800; color: #f8fafc; }
.kpi-label { color: #94a3b8; font-size: 13px; }
.badge { display:inline-block; padding:6px 10px; border-radius:999px; background:#0f766e; color:white; font-size:12px; font-weight:700; }
.badge-blue { background:#0369a1; }
.badge-red { background:#b91c1c; }
.badge-yellow { background:#a16207; }
hr { border-color: #243044; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def q(sql, params=()):
    with conn() as c:
        return pd.read_sql_query(sql, c, params=params)


def exec_sql(sql, params=()):
    with conn() as c:
        c.execute(sql, params)
        c.commit()


def hash_pw(pw):
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()


def init_db():
    with conn() as c:
        cur = c.cursor()
        cur.executescript("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, usuario TEXT UNIQUE, senha_hash TEXT, perfil TEXT, ativo INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS entidades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entidade TEXT, area TEXT, caa TEXT, can TEXT, atep TEXT, agente_negocio TEXT, numero_convenio TEXT,
            nivel TEXT, pontuacao INTEGER, data_cadastro TEXT
        );
        CREATE TABLE IF NOT EXISTS perguntas_qualificacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT, ordem INTEGER, pergunta TEXT, pontos_sim INTEGER DEFAULT 1, ativo INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS cursos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, curso TEXT, area TEXT, nivel TEXT, ativo INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS perguntas_curso (
            id INTEGER PRIMARY KEY AUTOINCREMENT, curso_id INTEGER, ordem INTEGER, pergunta TEXT, pontos_sim INTEGER DEFAULT 1, ativo INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS protocolos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            protocolo TEXT UNIQUE, entidade_id INTEGER, curso_id INTEGER, pontuacao_curso INTEGER,
            status TEXT, responsavel_atual TEXT, data_abertura TEXT, data_atualizacao TEXT, observacao TEXT
        );
        CREATE TABLE IF NOT EXISTS historico_fluxo (
            id INTEGER PRIMARY KEY AUTOINCREMENT, protocolo TEXT, status_anterior TEXT, status_novo TEXT, usuario TEXT, data_movimento TEXT, observacao TEXT
        );
        """)
        usuarios = cur.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
        if usuarios == 0:
            base_users = [
                ("Administrador", "admin", hash_pw("admin123"), "Administrador"),
                ("Validação Administrativa", "administrativo", hash_pw("adm123"), "Administrativo"),
                ("Análise Técnica", "tecnico", hash_pw("tec123"), "Técnico"),
                ("Agendamento", "agendamento", hash_pw("age123"), "Agendamento"),
                ("Execução", "executor", hash_pw("exe123"), "Executor"),
            ]
            cur.executemany("INSERT INTO usuarios(nome,usuario,senha_hash,perfil) VALUES(?,?,?,?)", base_users)
        if cur.execute("SELECT COUNT(*) FROM perguntas_qualificacao").fetchone()[0] == 0:
            perguntas = [
                (1, "A entidade possui equipe responsável pela execução das demandas?", 5),
                (2, "A entidade possui estrutura física mínima para atendimento?", 5),
                (3, "A entidade possui histórico de participação em projetos anteriores?", 5),
                (4, "A entidade possui capacidade de mobilização do público-alvo?", 5),
                (5, "A entidade possui documentação regularizada?", 5),
                (6, "A entidade possui indicadores ou registros de acompanhamento?", 5),
                (7, "A entidade possui experiência em ações de capacitação?", 5),
            ]
            cur.executemany("INSERT INTO perguntas_qualificacao(ordem,pergunta,pontos_sim) VALUES(?,?,?)", perguntas)
        if cur.execute("SELECT COUNT(*) FROM cursos").fetchone()[0] == 0:
            cursos = [
                ("Gestão Básica de Demandas", "SEBRAE", "Básico"),
                ("Planejamento e Controle", "SEBRAE", "Intermediário"),
                ("Governança Avançada", "SEBRAE", "Avançado"),
                ("Introdução à Tecnologia", "SEMATEC", "Básico"),
                ("Gestão de Projetos Tecnológicos", "SEMATEC", "Intermediário"),
                ("Inovação e Dados", "SEMATEC", "Avançado"),
            ]
            cur.executemany("INSERT INTO cursos(curso,area,nivel) VALUES(?,?,?)", cursos)
        if cur.execute("SELECT COUNT(*) FROM perguntas_curso").fetchone()[0] == 0:
            ids = cur.execute("SELECT id FROM cursos").fetchall()
            perguntas_curso = []
            for (cid,) in ids:
                perguntas_curso += [(cid, 1, "A demanda possui objetivo claro?", 5), (cid, 2, "Existe público-alvo definido?", 5), (cid, 3, "A execução possui prazo viável?", 5)]
            cur.executemany("INSERT INTO perguntas_curso(curso_id,ordem,pergunta,pontos_sim) VALUES(?,?,?,?)", perguntas_curso)
        c.commit()


def nivel_por_pontos(p):
    if p <= 15:
        return "Básico"
    if p <= 30:
        return "Intermediário"
    return "Avançado"


def niveis_permitidos(nivel):
    return {"Básico": ["Básico"], "Intermediário": ["Básico", "Intermediário"], "Avançado": ["Básico", "Intermediário", "Avançado"]}.get(nivel, ["Básico"])


def badge(status):
    cls = "badge-blue"
    if status in ["Cancelado"]: cls = "badge-red"
    if status in ["Agendamento", "Execução"]: cls = "badge-yellow"
    return f'<span class="badge {cls}">{status}</span>'


def login():
    st.markdown(f"# 🏛️ {APP_TITLE}")
    st.markdown("Acesso restrito")
    c1, c2, c3 = st.columns([1,1.2,1])
    with c2:
        st.markdown('<div class="bahia-card">', unsafe_allow_html=True)
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar", use_container_width=True):
            u = q("SELECT * FROM usuarios WHERE usuario=? AND ativo=1", (usuario,))
            if not u.empty and u.iloc[0]["senha_hash"] == hash_pw(senha):
                st.session_state.user = dict(u.iloc[0])
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")
        st.caption("Demo: admin / admin123")
        st.markdown('</div>', unsafe_allow_html=True)


def sidebar():
    user = st.session_state.user
    st.sidebar.title("🏛️ Bahia")
    st.sidebar.caption(f"{user['nome']} | {user['perfil']}")
    menu = ["Dashboard", "Entidades", "Nova Qualificação", "Cursos e Demandas", "Fluxo Administrativo", "Relatórios"]
    if user["perfil"] == "Administrador":
        menu += ["Cadastros Base", "Usuários"]
    page = st.sidebar.radio("Menu", menu)
    if st.sidebar.button("Sair"):
        st.session_state.clear(); st.rerun()
    return page


def dashboard():
    st.title(APP_TITLE)
    entidades = q("SELECT * FROM entidades")
    prot = q("SELECT * FROM protocolos")
    cursos = q("SELECT * FROM cursos WHERE ativo=1")
    k1,k2,k3,k4 = st.columns(4)
    vals = [(len(entidades), "Entidades"), (len(cursos), "Cursos ativos"), (len(prot[prot.status!='Finalizado']) if not prot.empty else 0, "Em andamento"), (len(prot[prot.status=='Finalizado']) if not prot.empty else 0, "Finalizados")]
    for col,(v,l) in zip([k1,k2,k3,k4], vals):
        with col: st.markdown(f'<div class="bahia-card"><div class="kpi">{v}</div><div class="kpi-label">{l}</div></div>', unsafe_allow_html=True)
    st.divider()
    if not prot.empty:
        col1,col2 = st.columns(2)
        with col1:
            fig = px.pie(prot, names="status", title="Protocolos por status")
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.histogram(entidades, x="nivel", title="Entidades por nível") if not entidades.empty else None
            if fig: st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Ainda não existem protocolos. Cadastre uma entidade e envie uma demanda.")


def entidades_page():
    st.title("🏢 Entidades")
    df = q("SELECT * FROM entidades ORDER BY id DESC")
    busca = st.text_input("Buscar entidade")
    if busca and not df.empty:
        df = df[df["entidade"].str.contains(busca, case=False, na=False)]
    st.dataframe(df, use_container_width=True, hide_index=True)


def nova_qualificacao():
    st.title("📝 Nova Qualificação")
    perguntas = q("SELECT * FROM perguntas_qualificacao WHERE ativo=1 ORDER BY ordem")
    with st.form("nova_entidade"):
        c1,c2 = st.columns(2)
        with c1:
            entidade = st.text_input("Entidade")
            area = st.selectbox("Área responsável", ["SEBRAE", "SEMATEC"])
            caa = st.text_input("CAA")
            can = st.text_input("CAN")
        with c2:
            atep = st.text_input("ATEP")
            agente = st.text_input("Agente de negócio")
            convenio = st.text_input("Número de convênio")
        st.subheader("Questionário de qualificação")
        respostas = {}
        for _, r in perguntas.iterrows():
            respostas[int(r.id)] = st.radio(r.pergunta, ["Não", "Sim"], horizontal=True, key=f"q_{r.id}")
        salvar = st.form_submit_button("Salvar qualificação", use_container_width=True)
    if salvar:
        if not entidade.strip():
            st.error("Informe o nome da entidade.")
            return
        pontos = sum(int(r.pontos_sim) for _, r in perguntas.iterrows() if respostas.get(int(r.id)) == "Sim")
        nivel = nivel_por_pontos(pontos)
        exec_sql("""INSERT INTO entidades(entidade,area,caa,can,atep,agente_negocio,numero_convenio,nivel,pontuacao,data_cadastro)
                  VALUES(?,?,?,?,?,?,?,?,?,?)""", (entidade, area, caa, can, atep, agente, convenio, nivel, pontos, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        st.success(f"Entidade cadastrada. Nível: {nivel} | Pontuação: {pontos}")


def cursos_demandas():
    st.title("📚 Cursos e Demandas")
    ents = q("SELECT * FROM entidades ORDER BY entidade")
    if ents.empty:
        st.warning("Cadastre uma entidade primeiro."); return
    entidade_nome = st.selectbox("Entidade", ents["entidade"].tolist())
    ent = ents[ents.entidade == entidade_nome].iloc[-1]
    st.markdown(f"Área: **{ent.area}** &nbsp;&nbsp; Nível: **{ent.nivel}**", unsafe_allow_html=True)
    niveis = niveis_permitidos(ent.nivel)
    cursos = q("SELECT * FROM cursos WHERE area=? AND ativo=1", (ent.area,))
    cursos = cursos[cursos["nivel"].isin(niveis)]
    if cursos.empty:
        st.warning("Não existem cursos para este perfil."); return
    curso_nome = st.selectbox("Curso disponível", cursos["curso"].tolist())
    curso = cursos[cursos.curso == curso_nome].iloc[0]
    perguntas = q("SELECT * FROM perguntas_curso WHERE curso_id=? AND ativo=1 ORDER BY ordem", (int(curso.id),))
    with st.form("demanda"):
        st.subheader("Questionário da demanda")
        respostas = {}
        for _, r in perguntas.iterrows():
            respostas[int(r.id)] = st.radio(r.pergunta, ["Não", "Sim"], horizontal=True, key=f"pc_{r.id}")
        obs = st.text_area("Observação inicial")
        enviar = st.form_submit_button("Gerar protocolo e enviar para validação", use_container_width=True)
    if enviar:
        pontos = sum(int(r.pontos_sim) for _, r in perguntas.iterrows() if respostas.get(int(r.id)) == "Sim")
        protocolo = f"BA-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        exec_sql("""INSERT INTO protocolos(protocolo,entidade_id,curso_id,pontuacao_curso,status,responsavel_atual,data_abertura,data_atualizacao,observacao)
                  VALUES(?,?,?,?,?,?,?,?,?)""", (protocolo, int(ent.id), int(curso.id), pontos, "Validação Administrativa", "Administrativo", now, now, obs))
        exec_sql("INSERT INTO historico_fluxo(protocolo,status_anterior,status_novo,usuario,data_movimento,observacao) VALUES(?,?,?,?,?,?)", (protocolo, "", "Validação Administrativa", st.session_state.user["usuario"], now, obs))
        st.success(f"Protocolo criado: {protocolo}")


def fluxo_page():
    st.title("🔄 Fluxo Administrativo")
    df = q("""SELECT p.*, e.entidade, c.curso, c.area, c.nivel FROM protocolos p
              LEFT JOIN entidades e ON e.id=p.entidade_id LEFT JOIN cursos c ON c.id=p.curso_id ORDER BY p.id DESC""")
    if df.empty:
        st.warning("Nenhum protocolo criado."); return
    status_filtro = st.multiselect("Filtrar status", sorted(df.status.unique().tolist()))
    view = df[df.status.isin(status_filtro)] if status_filtro else df
    st.dataframe(view[["protocolo","entidade","curso","pontuacao_curso","status","responsavel_atual","data_abertura"]], use_container_width=True, hide_index=True)
    prot = st.selectbox("Selecionar protocolo", df.protocolo.tolist())
    row = df[df.protocolo == prot].iloc[0]
    st.markdown(f"### {prot} {badge(row.status)}", unsafe_allow_html=True)
    st.write(f"**Entidade:** {row.entidade} | **Curso:** {row.curso} | **Pontuação:** {row.pontuacao_curso}")
    obs = st.text_area("Observação da decisão")
    c1,c2 = st.columns(2)
    fluxo = {"Validação Administrativa":"Análise Técnica", "Análise Técnica":"Agendamento", "Agendamento":"Execução", "Execução":"Finalizado"}
    with c1:
        if st.button("Aprovar / Avançar", use_container_width=True):
            novo = fluxo.get(row.status, row.status)
            resp = {"Análise Técnica":"Técnico", "Agendamento":"Agendamento", "Execução":"Executor", "Finalizado":"Finalizado"}.get(novo, "Administrativo")
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            exec_sql("UPDATE protocolos SET status=?, responsavel_atual=?, data_atualizacao=? WHERE protocolo=?", (novo, resp, now, prot))
            exec_sql("INSERT INTO historico_fluxo(protocolo,status_anterior,status_novo,usuario,data_movimento,observacao) VALUES(?,?,?,?,?,?)", (prot, row.status, novo, st.session_state.user["usuario"], now, obs))
            st.success("Fluxo atualizado."); st.rerun()
    with c2:
        if st.button("Recusar / Cancelar", use_container_width=True):
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            exec_sql("UPDATE protocolos SET status='Cancelado', responsavel_atual='Cancelado', data_atualizacao=? WHERE protocolo=?", (now, prot))
            exec_sql("INSERT INTO historico_fluxo(protocolo,status_anterior,status_novo,usuario,data_movimento,observacao) VALUES(?,?,?,?,?,?)", (prot, row.status, "Cancelado", st.session_state.user["usuario"], now, obs))
            st.error("Protocolo cancelado."); st.rerun()
    st.subheader("Histórico")
    hist = q("SELECT status_anterior,status_novo,usuario,data_movimento,observacao FROM historico_fluxo WHERE protocolo=? ORDER BY id", (prot,))
    st.dataframe(hist, use_container_width=True, hide_index=True)


def relatorios():
    st.title("📊 Relatórios")
    df = q("""SELECT p.*, e.entidade, e.nivel AS nivel_entidade, c.curso, c.area FROM protocolos p
              LEFT JOIN entidades e ON e.id=p.entidade_id LEFT JOIN cursos c ON c.id=p.curso_id""")
    if df.empty:
        st.info("Sem dados para relatório."); return
    st.download_button("Baixar protocolos CSV", df.to_csv(index=False, sep=";").encode("utf-8"), "protocolos_bahia.csv", "text/csv")
    st.plotly_chart(px.bar(df, x="status", title="Quantidade por status"), use_container_width=True)
    st.plotly_chart(px.bar(df, x="area", color="status", title="Protocolos por área"), use_container_width=True)


def cadastros_base():
    st.title("⚙️ Cadastros Base")
    t1,t2,t3 = st.tabs(["Cursos", "Perguntas Qualificação", "Perguntas Curso"])
    with t1:
        with st.form("add_curso"):
            nome=st.text_input("Curso"); area=st.selectbox("Área",["SEBRAE","SEMATEC"]); nivel=st.selectbox("Nível",["Básico","Intermediário","Avançado"])
            if st.form_submit_button("Cadastrar curso") and nome:
                exec_sql("INSERT INTO cursos(curso,area,nivel) VALUES(?,?,?)", (nome,area,nivel)); st.success("Curso cadastrado."); st.rerun()
        st.dataframe(q("SELECT * FROM cursos ORDER BY id DESC"), use_container_width=True, hide_index=True)
    with t2:
        with st.form("add_pq"):
            ordem=st.number_input("Ordem",1,999,1); pergunta=st.text_area("Pergunta"); pontos=st.number_input("Pontos SIM",0,100,5)
            if st.form_submit_button("Cadastrar pergunta") and pergunta:
                exec_sql("INSERT INTO perguntas_qualificacao(ordem,pergunta,pontos_sim) VALUES(?,?,?)", (ordem,pergunta,pontos)); st.success("Pergunta cadastrada."); st.rerun()
        st.dataframe(q("SELECT * FROM perguntas_qualificacao ORDER BY ordem"), use_container_width=True, hide_index=True)
    with t3:
        cursos = q("SELECT * FROM cursos WHERE ativo=1 ORDER BY curso")
        if not cursos.empty:
            with st.form("add_pc"):
                curso_nome=st.selectbox("Curso", cursos.curso.tolist()); ordem=st.number_input("Ordem ",1,999,1); pergunta=st.text_area("Pergunta "); pontos=st.number_input("Pontos SIM ",0,100,5)
                if st.form_submit_button("Cadastrar pergunta do curso") and pergunta:
                    cid = int(cursos[cursos.curso==curso_nome].iloc[0].id)
                    exec_sql("INSERT INTO perguntas_curso(curso_id,ordem,pergunta,pontos_sim) VALUES(?,?,?,?)", (cid,ordem,pergunta,pontos)); st.success("Pergunta cadastrada."); st.rerun()
        st.dataframe(q("SELECT pc.id,c.curso,pc.ordem,pc.pergunta,pc.pontos_sim FROM perguntas_curso pc LEFT JOIN cursos c ON c.id=pc.curso_id ORDER BY c.curso,pc.ordem"), use_container_width=True, hide_index=True)


def usuarios_page():
    st.title("👥 Usuários")
    with st.form("user"):
        nome=st.text_input("Nome"); usuario=st.text_input("Usuário"); senha=st.text_input("Senha", type="password"); perfil=st.selectbox("Perfil", ["Administrador","Administrativo","Técnico","Agendamento","Executor","Consulta"])
        if st.form_submit_button("Criar usuário") and nome and usuario and senha:
            try:
                exec_sql("INSERT INTO usuarios(nome,usuario,senha_hash,perfil) VALUES(?,?,?,?)", (nome,usuario,hash_pw(senha),perfil)); st.success("Usuário criado."); st.rerun()
            except sqlite3.IntegrityError:
                st.error("Usuário já existe.")
    st.dataframe(q("SELECT id,nome,usuario,perfil,ativo FROM usuarios ORDER BY id"), use_container_width=True, hide_index=True)


init_db()
if "user" not in st.session_state:
    login()
else:
    page = sidebar()
    pages = {"Dashboard": dashboard, "Entidades": entidades_page, "Nova Qualificação": nova_qualificacao, "Cursos e Demandas": cursos_demandas, "Fluxo Administrativo": fluxo_page, "Relatórios": relatorios, "Cadastros Base": cadastros_base, "Usuários": usuarios_page}
    pages[page]()
