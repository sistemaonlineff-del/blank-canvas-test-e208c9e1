import React, { FormEvent, useEffect, useState } from "react";
import { CheckCircle2, Database, FileText, Home, LogOut, RefreshCw, Search, Settings, UserPlus } from "lucide-react";
import { api, CADASTRO_OPTIONS, Row, User, USER_ROLE_OPTIONS } from "./api";
import logo1 from "../assets/logo_1.jpeg";
import logo2 from "../assets/logo_2.jpeg";
import "./styles.css";

type Page = "home" | "qualificacao" | "cursos" | "status" | "aprovacoes" | "entidades" | "config";
type AnswerValue = string | string[];

const pageLabels: Record<Page, string> = {
  home: "Tela principal",
  qualificacao: "Qualificar Nova Entidade",
  cursos: "Cursos",
  status: "Consultar Status",
  aprovacoes: "Minhas Aprovações",
  entidades: "Entidades",
  config: "Configurações"
};

const tableLabels: Record<string, string> = {
  cursos: "Cursos",
  perguntas_qualificacao: "Perguntas Entidade",
  perguntas_bpf: "Perguntas BPF",
  perguntas_curso: "Perguntas Curso",
  alternativas_curso: "Alternativas Curso",
  owners_area: "Owners por Área",
  entidades: "Entidades",
  usuarios: "Usuários",
  notificacoes: "Notificações"
};

function normalizeRoleKey(value: unknown) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

function isModerator(user: User) {
  return ["administrador", "moderador"].includes(normalizeRoleKey(user.perfil));
}

function canHandleStatus(user: User, status: unknown) {
  const role = normalizeRoleKey(user.perfil);
  const statusKey = String(status || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
  if (["administrador", "moderador"].includes(role)) return true;
  if (role === "analista administrativo") return statusKey === "validacao administrativa";
  if (role === "analista tecnico") return statusKey === "analise tecnica";
  if (role === "agendamento") return statusKey === "agendamento";
  if (role === "execucao") return statusKey === "execucao";
  return false;
}

function useAsync<T>(factory: () => Promise<T>, deps: React.DependencyList) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    factory()
      .then((value) => active && setData(value))
      .catch((err) => active && setError(err.message || String(err)))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, deps);

  return { data, loading, error, reload: () => factory().then(setData) };
}

function Login({ onLogin }: { onLogin: (user: User) => void }) {
  const [mode, setMode] = useState<"login" | "register" | "password">("login");
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");
  const [novaSenha, setNovaSenha] = useState("");
  const [confirmarSenha, setConfirmarSenha] = useState("");
  const [pendingUser, setPendingUser] = useState<User | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");
    try {
      const result = await api.login(usuario, senha);
      if (result.user.trocar_senha_obrigatorio || result.user.senha_temporaria) {
        setPendingUser(result.user);
        setMode("password");
        return;
      }
      saveStoredUser(result.user);
      onLogin(result.user);
    } catch (err: any) {
      setError(err.message);
    }
  }

  async function register(event: FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");
    try {
      const result = await api.register(usuario);
      setMessage(result.tempPassword ? `${result.message} Senha temporária: ${result.tempPassword}` : result.message);
      setMode("login");
    } catch (err: any) {
      setError(err.message);
    }
  }

  async function changePassword(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (!pendingUser) return;
    if (novaSenha !== confirmarSenha) {
      setError("As senhas nao conferem.");
      return;
    }
    try {
      const result = await api.changePassword(pendingUser.id, novaSenha);
      saveStoredUser(result.user);
      onLogin(result.user);
    } catch (err: any) {
      setError(err.message);
    }
  }

  return (
    <main className="login-page">
      <section className="login-hero">
        <h1>Governanca e Qualificacao de Demandas - Bahia</h1>
        <span>Sistema Bahia</span>
      </section>
      <form className="login-card" onSubmit={mode === "register" ? register : mode === "password" ? changePassword : submit}>
        <h2>{mode === "register" ? "Criar novo usuario" : mode === "password" ? "Definir nova senha" : "Acesso ao sistema"}</h2>
        <p>{mode === "register" ? "Informe seu e-mail para receber uma senha temporaria." : mode === "password" ? "Cadastre uma nova senha para continuar." : "Entre para acompanhar qualificacoes, cursos e fluxos."}</p>
        {mode !== "password" && (
          <>
            <label>E-mail ou usuario</label>
            <input value={usuario} onChange={(e) => setUsuario(e.target.value)} autoFocus />
          </>
        )}
        {mode === "login" && (
          <>
            <label>Senha</label>
            <input value={senha} onChange={(e) => setSenha(e.target.value)} type="password" />
          </>
        )}
        {mode === "password" && (
          <>
            <label>Nova senha</label>
            <input value={novaSenha} onChange={(e) => setNovaSenha(e.target.value)} type="password" autoFocus />
            <label>Confirmar nova senha</label>
            <input value={confirmarSenha} onChange={(e) => setConfirmarSenha(e.target.value)} type="password" />
          </>
        )}
        {message && <div className="alert success">{message}</div>}
        {error && <div className="alert error">{error}</div>}
        <button type="submit">{mode === "register" ? "Enviar senha temporaria" : mode === "password" ? "Salvar nova senha" : "Entrar"}</button>
        {mode === "login" && <button className="plain-button" type="button" onClick={() => { setMode("register"); setError(""); setMessage(""); }}>Criar novo usuario</button>}
        {mode !== "login" && <button className="plain-button" type="button" onClick={() => { setMode("login"); setError(""); }}>Voltar para login</button>}
      </form>
    </main>
  );
}
function Layout({ user, page, setPage, logout, children }: any) {
  const admin = isModerator(user);
  const pages: { id: Page; icon: React.ReactNode }[] = [
    { id: "home", icon: <Home size={18} /> },
    { id: "qualificacao", icon: <UserPlus size={18} /> },
    { id: "cursos", icon: <FileText size={18} /> },
    { id: "status", icon: <Search size={18} /> },
    { id: "aprovacoes", icon: <CheckCircle2 size={18} /> },
    ...(admin ? [{ id: "entidades" as Page, icon: <Database size={18} /> }, { id: "config" as Page, icon: <Settings size={18} /> }] : [])
  ];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <img src={logo1} alt="Logo CAR" />
          <img src={logo2} alt="Logo Governo da Bahia" />
          <strong>Sistema Bahia</strong>
          <span>Governança & Qualificação</span>
        </div>
        <div className="user-chip">
          <div className="avatar">{(user.nome || user.usuario || "U").slice(0, 1).toUpperCase()}</div>
          <div>
            <strong>{user.nome || user.usuario}</strong>
            <span>{user.perfil} · {user.usuario}</span>
          </div>
        </div>
        <nav>
          {pages.map((item) => (
            <button key={item.id} className={page === item.id ? "active" : ""} onClick={() => setPage(item.id)}>
              {item.icon}
              {pageLabels[item.id]}
            </button>
          ))}
        </nav>
        <button className="logout" onClick={logout}>
          <LogOut size={18} />
          Sair
        </button>
      </aside>
      <section className="content">
        <header className="topbar">
          <h1>Governança e Qualificação de Demandas - Bahia</h1>
          <p>Sistema Bahia · {user.perfil}</p>
        </header>
        {children}
      </section>
    </div>
  );
}

function HomePage({ user }: { user: User }) {
  const { data, loading, error } = useAsync(api.dashboard, []);
  const moderator = isModerator(user);
  if (loading) return <Loading />;
  if (error) return <ErrorMessage text={error} />;
  const cards = data?.cards || {};
  return (
    <PageBlock title="Tela principal">
      {(user.acesso_pendente || user.perfil === "Pendente") && (
        <div className="alert warning">Seu usuário está aguardando qualificação de atividade por um moderador.</div>
      )}
      {moderator && Number(cards.usuariosPendentes || 0) > 0 && (
        <div className="alert warning">Há {cards.usuariosPendentes} usuário(s) pendente(s) aguardando definição de cargo em Configurações → Usuários.</div>
      )}
      <div className="cards-grid">
        <Metric title="Entidades cadastradas" value={cards.entidades} />
        <Metric title="Entidades qualificadas" value={cards.qualificadas} />
        <Metric title="Form. geral pendentes" value={cards.formGeralPendentes} />
        <Metric title="BPF pendentes" value={cards.bpfPendentes} />
        <Metric title="Cursos disponíveis" value={cards.cursos} />
        <Metric title="Fluxos em andamento" value={cards.fluxos} />
        {moderator && <Metric title="Usuários pendentes" value={cards.usuariosPendentes} />}
      </div>
      <DataTable rows={data?.protocolos || []} empty="Nenhum protocolo criado." />
    </PageBlock>
  );
}

function EntidadesPage({ user }: { user: User }) {
  const [nome, setNome] = useState("");
  const [cnpj, setCnpj] = useState("");
  const [message, setMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { data, loading, error, reload } = useAsync(api.entities, [message]);

  async function create(event: FormEvent) {
    event.preventDefault();
    setErrorMessage("");
    setSubmitting(true);
    try {
      const result = await api.createEntity(nome, cnpj, user);
      setNome("");
      setCnpj("");
      setMessage(result.message);
      await reload();
    } catch (err: any) {
      setErrorMessage(err.message || "Erro ao cadastrar entidade.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <PageBlock title="Entidades">
      <form className="inline-form" onSubmit={create}>
        <label>Cadastrar Nova entidade</label>
        <input value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Nome da Entidade" />
        <input value={cnpj} onChange={(e) => setCnpj(e.target.value)} placeholder="CNPJ da Entidade" />
        <button disabled={!nome.trim() || !cnpj.trim() || submitting}>{submitting ? "Salvando..." : "Salvar"}</button>
      </form>
      {message && <div className="alert success">{message}</div>}
      {errorMessage && <div className="alert error">{errorMessage}</div>}
      {loading ? <Loading /> : error ? <ErrorMessage text={error} /> : <DataTable rows={data?.items || []} />}
    </PageBlock>
  );
}

function isConcludedStatus(status: any) {
  return ["Concluída", "Concluida", "ConcluÃ­da"].includes(String(status || ""));
}

function allowedLevels(nivel: any) {
  const value = String(nivel || "");
  if (["Avançado", "Avancado", "AvanÃ§ado"].includes(value)) return ["Básico", "Basico", "BÃ¡sico", "Intermediário", "Intermediario", "IntermediÃ¡rio", "Avançado", "Avancado", "AvanÃ§ado"];
  if (["Intermediário", "Intermediario", "IntermediÃ¡rio"].includes(value)) return ["Básico", "Basico", "BÃ¡sico", "Intermediário", "Intermediario", "IntermediÃ¡rio"];
  return ["Básico", "Basico", "BÃ¡sico"];
}

type QuestionOption = { label: string; points: number };

function normalizeText(value: unknown) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

function isSealCertificationQuestion(question: Row) {
  const secao = normalizeText(question.secao);
  const subsecao = normalizeText(question.subsecao);
  const codigo = normalizeText(question.codigo_pergunta);
  const pergunta = normalizeText(question.pergunta);
  return (
    secao.includes("selos e certificacoes") ||
    codigo.includes("selo de inspecao") ||
    pergunta.includes("selo de inspecao") ||
    (subsecao === "5.1" && (pergunta === "multipla" || !pergunta))
  );
}

function questionPrompt(question: Row, kind: "geral" | "bpf" | "curso") {
  if (kind === "bpf" && isSealCertificationQuestion(question)) {
    return "A agroindústria está regularizada com qual selo de inspeção?";
  }
  if (kind === "bpf" && normalizeText(question.pergunta) === "multipla" && question.codigo_pergunta) {
    return String(question.codigo_pergunta);
  }
  return String(question.pergunta || question.codigo_pergunta || "");
}

function questionOptions(question: Row, kind: "geral" | "bpf" | "curso"): QuestionOption[] {
  if (kind === "geral") {
    const options = [1, 2, 3]
      .map((idx) => ({ label: String(question[`opcao_${idx}`] || "").trim(), points: Number(question[`pontos_${idx}`] || 0) }))
      .filter((option) => option.label);
    return options.length ? options : [{ label: "Não", points: 0 }, { label: "Sim", points: Number(question.pontos_sim || 1) }];
  }
  if (kind === "bpf") {
    if (isSealCertificationQuestion(question)) {
      return ["SIM", "SIE", "ANVISA", "MAPA"].map((label) => ({ label, points: Number(question.pontos_sim || 1) }));
    }
    const labels = String(question.opcoes || "S;N;P;NA").split(";").map((item) => item.trim()).filter(Boolean);
    return labels.map((label) => ({ label, points: label === "S" ? Number(question.pontos_sim || 1) : 0 }));
  }
  const alternatives = question.alternativas || [];
  if (alternatives.length) {
    return alternatives.map((item: Row) => ({ label: String(item.alternativa || ""), points: Number(item.pontos || 0) }));
  }
  return [{ label: "Não", points: 0 }, { label: "Sim", points: Number(question.pontos_sim || 1) }];
}

function defaultAnswerValue(question: Row, kind: "geral" | "bpf" | "curso"): AnswerValue {
  if (kind === "bpf" && isSealCertificationQuestion(question)) return [];
  return questionOptions(question, kind)[0]?.label || "";
}

function answerPoints(question: Row, kind: "geral" | "bpf" | "curso", answer: AnswerValue) {
  if (Array.isArray(answer)) {
    return answer.length ? Number(question.pontos_sim || 1) : 0;
  }
  return questionOptions(question, kind).find((option) => option.label === answer)?.points || 0;
}

function groupedRows(rows: Row[], key: string) {
  return rows.reduce<Record<string, Row[]>>((groups, row) => {
    const group = String(row[key] || "Perguntas");
    groups[group] = groups[group] || [];
    groups[group].push(row);
    return groups;
  }, {});
}

function QuestionRow({ question, kind, value, onChange }: { question: Row; kind: "geral" | "bpf" | "curso"; value: AnswerValue; onChange: (value: AnswerValue) => void }) {
  const options = questionOptions(question, kind);
  const multipleChoice = kind === "bpf" && isSealCertificationQuestion(question);
  const currentValues = Array.isArray(value) ? value : [];
  const title = kind === "bpf" && question.codigo_pergunta && normalizeText(question.pergunta) !== "multipla"
    ? `${question.codigo_pergunta} - ${question.pergunta}`
    : questionPrompt(question, kind);
  return (
    <fieldset className="question-row">
      <legend>{title}</legend>
      <div className="choice-row">
        {options.map((option) => (
          <label key={option.label} className="choice-pill">
            <input
              type={multipleChoice ? "checkbox" : "radio"}
              checked={multipleChoice ? currentValues.includes(option.label) : value === option.label}
              onChange={() => {
                if (multipleChoice) {
                  onChange(
                    currentValues.includes(option.label)
                      ? currentValues.filter((item) => item !== option.label)
                      : [...currentValues, option.label]
                  );
                  return;
                }
                onChange(option.label);
              }}
            />
            <span>{option.label}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

function QualificationQuestionForm({ kind, pending, onSaved }: { kind: "geral" | "bpf"; pending: Row[]; onSaved: (message: string) => void }) {
  const questions = useAsync(() => api.questions(kind), [kind]);
  const [entidadeId, setEntidadeId] = useState<number | "">("");
  const [entitySearch, setEntitySearch] = useState("");
  const [answers, setAnswers] = useState<Record<string, AnswerValue>>({});
  const [submitError, setSubmitError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const next: Record<string, AnswerValue> = {};
    (questions.data?.items || []).forEach((question) => {
      next[question.id] = defaultAnswerValue(question, kind);
    });
    setAnswers(next);
    setSubmitError("");
  }, [questions.data, kind]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitError("");
    if (!entidadeId) return;
    setSubmitting(true);
    try {
      const respostas = (questions.data?.items || []).map((question) => {
        const answer = answers[question.id] ?? defaultAnswerValue(question, kind);
        const resposta = Array.isArray(answer) ? answer.join("; ") : answer;
        const pontuacao = answerPoints(question, kind, answer);
        return { questionario: question.questionario, pergunta_id: question.id, pergunta: questionPrompt(question, kind), resposta, pontuacao };
      });
      const result = kind === "geral" ? await api.saveGeneral(Number(entidadeId), respostas) : await api.saveBpf(Number(entidadeId), respostas);
      onSaved(`${result.message}${result.nivel ? ` Nível: ${result.nivel}. Pontuação: ${result.pontuacao}.` : ""}`);
      setEntidadeId("");
    } catch (err: any) {
      setSubmitError(err.message || "Erro ao salvar formulário.");
    } finally {
      setSubmitting(false);
    }
  }

  if (!pending.length) return <div className="empty">{kind === "geral" ? "Nenhuma entidade aguardando Formulario Geral." : "Nenhuma entidade aguardando BPF."}</div>;
  if (questions.loading) return <Loading />;
  if (questions.error) return <ErrorMessage text={questions.error} />;
  if (!questions.data?.items.length) return <div className="empty">Nenhuma pergunta cadastrada para este formulário.</div>;

  const groups = groupedRows(questions.data.items, kind === "geral" ? "questionario" : "secao");
  const filteredPending = pending.filter((item) => {
    const search = entitySearch.trim().toLowerCase();
    if (!search) return true;
    return [item.entidade, item.cnpj, item.id]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(search));
  });
  return (
    <form className="panel" onSubmit={submit}>
      <label>{kind === "geral" ? "Entidade aguardando Formulario Geral" : "Entidade aguardando BPF"}
        <input
          placeholder="Buscar entidade por nome, CNPJ ou codigo"
          value={entitySearch}
          onChange={(e) => setEntitySearch(e.target.value)}
        />
        <select value={entidadeId} onChange={(e) => setEntidadeId(Number(e.target.value) || "")}>
          <option value="">Selecionar</option>
          {filteredPending.map((item) => <option key={item.id} value={item.id}>{item.id} | {item.entidade} | {item.cnpj || "Sem CNPJ"}</option>)}
        </select>
      </label>
      {submitError && <div className="alert error">{submitError}</div>}
      {kind === "bpf" && (
        <div className="legend-card">
          <strong>Legenda das respostas do BPF</strong>
          <div className="legend-grid">
            <span><b>S</b> = Sim</span>
            <span><b>N</b> = Nao</span>
            <span><b>P</b> = Parcial</span>
            <span><b>NA</b> = Nao se aplica</span>
          </div>
        </div>
      )}
      <div className="question-list">
        {Object.entries(groups).map(([group, rows]) => (
          <section className="question-section" key={group}>
            <h3>{group}</h3>
            {kind === "bpf" && Object.keys(groupedRows(rows, "subsecao")).length > 1
              ? Object.entries(groupedRows(rows, "subsecao")).map(([subgroup, subgroupRows]) => (
                <div key={subgroup}>
                  <h4>{subgroup}</h4>
                  {subgroupRows.map((question) => <QuestionRow key={question.id} question={question} kind={kind} value={answers[question.id]} onChange={(value) => setAnswers({ ...answers, [question.id]: value })} />)}
                </div>
              ))
              : rows.map((question) => <QuestionRow key={question.id} question={question} kind={kind} value={answers[question.id]} onChange={(value) => setAnswers({ ...answers, [question.id]: value })} />)}
          </section>
        ))}
      </div>
      <button disabled={!entidadeId || submitting}>
        {submitting ? "Salvando..." : kind === "geral" ? "Salvar Formulario Geral e abrir BPF" : "Salvar BPF e concluir qualificação"}
      </button>
    </form>
  );
}

function QualificacaoPage() {
  const [tab, setTab] = useState<"cadastro" | "geral" | "bpf">("cadastro");
  const [selected, setSelected] = useState<Row | null>(null);
  const [fields, setFields] = useState<Row>({});
  const [entitySearch, setEntitySearch] = useState("");
  const [message, setMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [savingCadastro, setSavingCadastro] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const options = useAsync(api.qualificationOptions, [refreshKey]);
  const pendingGeral = useAsync(() => api.pendingQualification("geral"), [refreshKey]);
  const pendingBpf = useAsync(() => api.pendingQualification("bpf"), [refreshKey]);

  useEffect(() => {
    if (!selected) {
      setFields({});
      return;
    }
    setFields({
      cnpj: selected.cnpj || "",
      numero_convenio: selected.numero_convenio || "",
      an_atep_ateg: selected.an_atep_ateg || "",
      agente_negocio: selected.agente_negocio || "",
      atep: selected.atep || "",
      nome_ateg: selected.nome_ateg || "",
      coordenador_tipo: selected.coordenador_tipo || "",
      nome_coordenador: selected.nome_coordenador || "",
      natureza_juridica: selected.natureza_juridica || "",
      dap_caf: selected.dap_caf || "",
      territorio_identidade: selected.territorio_identidade || "",
      email_responsavel: selected.email_responsavel || "",
      tipologia_beneficiarios: selected.tipologia_beneficiarios || "",
      comunidade_tradicional: selected.comunidade_tradicional || "",
      ativa_dinamica: selected.ativa_dinamica || "",
      municipio_entidade: selected.municipio_entidade || "",
      certificacao: selected.certificacao || "",
      licenca_ambiental: selected.licenca_ambiental || "",
      telefone: selected.telefone || "",
      endereco: selected.endereco || ""
    });
  }, [selected]);

  async function saveCadastro(event: FormEvent) {
    event.preventDefault();
    setErrorMessage("");
    if (!selected) return;
    setSavingCadastro(true);
    try {
      const result = await api.saveCadastro(selected.id, fields);
      setMessage(result.message);
      setRefreshKey((value) => value + 1);
      setSelected(null);
      setFields({});
      setTab("geral");
    } catch (err: any) {
      setErrorMessage(err.message || "Erro ao salvar dados cadastrais.");
    } finally {
      setSavingCadastro(false);
    }
  }

  const showAgenteNegocio = fields.an_atep_ateg === "AN";
  const showAtepAteg = fields.an_atep_ateg === "ATEP/ATEG";
  const showComunidadeTradicional = fields.tipologia_beneficiarios === "Comunidades Tradicionais";
  const filteredEntities = (options.data?.items || []).filter((item) => {
    const search = entitySearch.trim().toLowerCase();
    if (!search) return true;
    return [item.entidade, item.cnpj, item.id]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(search));
  });

  return (
    <PageBlock title="Qualificar Nova Entidade">
      <Tabs value={tab} onChange={setTab} items={[
        ["cadastro", "Selecionar entidade da base"],
        ["geral", "Aguardando Finalizar Formulario Geral"],
        ["bpf", "Aguardando Finalizar Formulario BPF"]
      ]} />
      {message && <div className="alert success">{message}</div>}
      {errorMessage && <div className="alert error">{errorMessage}</div>}
      {tab === "cadastro" && (
        <form className="panel" onSubmit={saveCadastro}>
          <label>Entidade cadastrada na base</label>
          <input
            placeholder="Buscar entidade por nome, CNPJ ou codigo"
            value={entitySearch}
            onChange={(e) => setEntitySearch(e.target.value)}
          />
          <select onChange={(e) => setSelected(options.data?.items.find((item) => String(item.id) === e.target.value) || null)} value={selected?.id || ""}>
            <option value="">Selecionar</option>
            {filteredEntities.map((item) => <option key={item.id} value={item.id}>{item.id} | {item.entidade} | {item.cnpj || "Sem CNPJ"}</option>)}
          </select>
          <div className="form-grid">
            <label>Número do Convênio
              <input value={fields.numero_convenio || ""} onChange={(e) => setFields({ ...fields, numero_convenio: e.target.value })} />
            </label>
            <label>AN ou ATEP / ATEG
              <select value={fields.an_atep_ateg || ""} onChange={(e) => setFields({ ...fields, an_atep_ateg: e.target.value, agente_negocio: "", atep: "", nome_ateg: "" })}>
                <option value="">Selecionar</option>
                {CADASTRO_OPTIONS.anAtepAteg.map((option) => <option key={option} value={option}>{option}</option>)}
              </select>
            </label>
            <label>Coordenador de Negócio / Coordenação de Mercado
              <select value={fields.coordenador_tipo || ""} onChange={(e) => setFields({ ...fields, coordenador_tipo: e.target.value })}>
                <option value="">Selecionar</option>
                {CADASTRO_OPTIONS.coordenadorTipo.map((option) => <option key={option} value={option}>{option}</option>)}
              </select>
            </label>
            {showAgenteNegocio && (
              <label>Nome do Agente de Negócio
                <input value={fields.agente_negocio || ""} onChange={(e) => setFields({ ...fields, agente_negocio: e.target.value })} />
              </label>
            )}
            {showAtepAteg && (
              <label>Nome ATEP
                <input value={fields.atep || ""} onChange={(e) => setFields({ ...fields, atep: e.target.value })} />
              </label>
            )}
            {showAtepAteg && (
              <label>Nome ATEG
                <input value={fields.nome_ateg || ""} onChange={(e) => setFields({ ...fields, nome_ateg: e.target.value })} />
              </label>
            )}
            <label>Nome do Coordenador
              <input value={fields.nome_coordenador || ""} onChange={(e) => setFields({ ...fields, nome_coordenador: e.target.value })} />
            </label>
            <label>Nº CNPJ
              <input value={fields.cnpj || ""} onChange={(e) => setFields({ ...fields, cnpj: e.target.value })} />
            </label>
            <label>Natureza Jurídica da Entidade
              <select value={fields.natureza_juridica || ""} onChange={(e) => setFields({ ...fields, natureza_juridica: e.target.value })}>
                <option value="">Selecionar</option>
                {CADASTRO_OPTIONS.naturezaJuridica.map((option) => <option key={option} value={option}>{option}</option>)}
              </select>
            </label>
            <label>Nº DAP ou CAF
              <input value={fields.dap_caf || ""} onChange={(e) => setFields({ ...fields, dap_caf: e.target.value })} />
            </label>
            <label>Território de Identidade
              <input value={fields.territorio_identidade || ""} onChange={(e) => setFields({ ...fields, territorio_identidade: e.target.value })} />
            </label>
            <label>Email
              <input value={fields.email_responsavel || ""} onChange={(e) => setFields({ ...fields, email_responsavel: e.target.value })} />
            </label>
            <label>Municipio da Entidade
              <input value={fields.municipio_entidade || ""} onChange={(e) => setFields({ ...fields, municipio_entidade: e.target.value })} />
            </label>
            <label>Certificacao
              <select value={fields.certificacao || ""} onChange={(e) => setFields({ ...fields, certificacao: e.target.value })}>
                <option value="">Selecionar</option>
                {CADASTRO_OPTIONS.certificacoesEntidade.map((option) => <option key={option} value={option}>{option}</option>)}
              </select>
            </label>
            <label>Licenca ambiental
              <select value={fields.licenca_ambiental || ""} onChange={(e) => setFields({ ...fields, licenca_ambiental: e.target.value })}>
                <option value="">Selecionar</option>
                {CADASTRO_OPTIONS.licencasAmbientais.map((option) => <option key={option} value={option}>{option}</option>)}
              </select>
            </label>
            <label>Telefone
              <input value={fields.telefone || ""} onChange={(e) => setFields({ ...fields, telefone: e.target.value })} />
            </label>
            <label>Endereco
              <input value={fields.endereco || ""} onChange={(e) => setFields({ ...fields, endereco: e.target.value })} />
            </label>
            <label>Tipologia de Beneficiários
              <select value={fields.tipologia_beneficiarios || ""} onChange={(e) => setFields({ ...fields, tipologia_beneficiarios: e.target.value, comunidade_tradicional: "" })}>
                <option value="">Selecionar</option>
                {CADASTRO_OPTIONS.tipologiaBeneficiarios.map((option) => <option key={option} value={option}>{option}</option>)}
              </select>
            </label>
            {showComunidadeTradicional && (
              <label>Comunidades Tradicionais
                <select value={fields.comunidade_tradicional || ""} onChange={(e) => setFields({ ...fields, comunidade_tradicional: e.target.value })}>
                  <option value="">Selecionar</option>
                  {CADASTRO_OPTIONS.comunidadesTradicionais.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
              </label>
            )}
            <label>Ativa ou Dinâmica
              <select value={fields.ativa_dinamica || ""} onChange={(e) => setFields({ ...fields, ativa_dinamica: e.target.value })}>
                <option value="">Selecionar</option>
                {CADASTRO_OPTIONS.ativaDinamica.map((option) => <option key={option} value={option}>{option}</option>)}
              </select>
            </label>
          </div>
          <button disabled={!selected || savingCadastro}>{savingCadastro ? "Salvando..." : "Salvar dados cadastrais"}</button>
        </form>
      )}
      {tab === "geral" && <QualificationQuestionForm kind="geral" pending={pendingGeral.data?.items || []} onSaved={(text) => { setMessage(text); setRefreshKey((value) => value + 1); setTab("bpf"); }} />}
      {tab === "bpf" && <QualificationQuestionForm kind="bpf" pending={pendingBpf.data?.items || []} onSaved={(text) => { setMessage(text); setRefreshKey((value) => value + 1); }} />}
    </PageBlock>
  );
}

function CursosPage({ user }: { user: User }) {
  const entities = useAsync(api.entities, []);
  const courses = useAsync(api.courses, []);
  const [payload, setPayload] = useState<Row>({});
  const [message, setMessage] = useState("");
  const qualified = (entities.data?.items || []).filter((item) => item.status_qualificacao === "Concluída");

  async function submit(event: FormEvent) {
    event.preventDefault();
    const course = (courses.data?.items || []).find((item) => String(item.id) === String(payload.curso_id));
    const result = await api.createProtocol({
      ...payload,
      area: course?.area,
      solicitante_nome: user.nome,
      solicitante_email: user.email,
      usuario: user.usuario
    });
    setMessage(`${result.message} ${result.protocolo}`);
    setPayload({});
  }

  return (
    <PageBlock title="Cursos">
      <form className="panel" onSubmit={submit}>
        <label>Entidade
          <select value={payload.entidade_id || ""} onChange={(e) => setPayload({ ...payload, entidade_id: Number(e.target.value) })}>
            <option value="">Selecionar</option>
            {qualified.map((item) => <option key={item.id} value={item.id}>{item.entidade} · {item.nivel}</option>)}
          </select>
        </label>
        <label>Curso
          <select value={payload.curso_id || ""} onChange={(e) => setPayload({ ...payload, curso_id: Number(e.target.value) })}>
            <option value="">Selecionar</option>
            {(courses.data?.items || []).map((item) => <option key={item.id} value={item.id}>{item.curso} · {item.area} · {item.nivel}</option>)}
          </select>
        </label>
        <label>Observação
          <textarea value={payload.observacao || ""} onChange={(e) => setPayload({ ...payload, observacao: e.target.value })} />
        </label>
        <button>Salvar e iniciar fluxo</button>
      </form>
      {message && <div className="alert success">{message}</div>}
    </PageBlock>
  );
}

function CursosPageV2({ user }: { user: User }) {
  const entities = useAsync(api.entities, []);
  const courses = useAsync(api.courses, []);
  const [payload, setPayload] = useState<Row>({});
  const [answers, setAnswers] = useState<Row>({});
  const [entitySearch, setEntitySearch] = useState("");
  const [message, setMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const courseQuestions = useAsync(() => payload.curso_id ? api.courseQuestions(Number(payload.curso_id)) : Promise.resolve({ items: [] }), [payload.curso_id]);
  const qualified = (entities.data?.items || []).filter((item) => isConcludedStatus(item.status_qualificacao));
  const selectedEntity = qualified.find((item) => String(item.id) === String(payload.entidade_id));
  const filteredQualified = qualified.filter((item) => {
    const search = entitySearch.trim().toLowerCase();
    if (!search) return true;
    return [item.entidade, item.cnpj, item.id, item.nivel]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(search));
  });
  const areas = Array.from(new Set((courses.data?.items || []).map((item) => item.area).filter(Boolean)));
  const availableCourses = (courses.data?.items || []).filter((course) => {
    if (!selectedEntity) return false;
    return (!payload.area || course.area === payload.area) && allowedLevels(selectedEntity.nivel).includes(String(course.nivel || ""));
  });

  useEffect(() => {
    const next: Row = {};
    (courseQuestions.data?.items || []).forEach((question) => {
      next[question.id] = questionOptions(question, "curso")[0]?.label || "";
    });
    setAnswers(next);
  }, [courseQuestions.data]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setErrorMessage("");
    setSubmitting(true);
    try {
      const course = (courses.data?.items || []).find((item) => String(item.id) === String(payload.curso_id));
      const entity = qualified.find((item) => String(item.id) === String(payload.entidade_id));
      const respostas = (courseQuestions.data?.items || []).map((question) => {
        const resposta = answers[question.id] || questionOptions(question, "curso")[0]?.label || "";
        const pontuacao = questionOptions(question, "curso").find((option) => option.label === resposta)?.points || 0;
        return { pergunta_id: question.id, pergunta: question.pergunta, resposta, pontuacao };
      });
      const result = await api.createProtocol({
        ...payload,
        area: course?.area,
        entidade: entity?.entidade,
        curso: course?.curso,
        respostas,
        pontuacao_curso: respostas.reduce((total, row) => total + Number(row.pontuacao || 0), 0),
        solicitante_nome: user.nome,
        solicitante_email: user.email,
        usuario: user.usuario
      });
      setMessage(`${result.message} ${result.protocolo}`);
      setPayload({});
      setAnswers({});
    } catch (err: any) {
      setErrorMessage(err.message || "Erro ao salvar demanda do curso.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <PageBlock title="Cursos">
      <form className="panel" onSubmit={submit}>
        <label>Entidade
          <input
            placeholder="Buscar entidade por nome, CNPJ, nivel ou codigo"
            value={entitySearch}
            onChange={(e) => setEntitySearch(e.target.value)}
          />
          <select value={payload.entidade_id || ""} onChange={(e) => setPayload({ entidade_id: Number(e.target.value), area: "", curso_id: "" })}>
            <option value="">Selecionar</option>
            {filteredQualified.map((item) => <option key={item.id} value={item.id}>{item.entidade} · {item.nivel}</option>)}
          </select>
        </label>
        {selectedEntity && <div className="course-summary">Nível da entidade: <strong>{selectedEntity.nivel}</strong></div>}
        <label>Área do curso
          <select value={payload.area || ""} onChange={(e) => setPayload({ ...payload, area: e.target.value, curso_id: "" })} disabled={!selectedEntity}>
            <option value="">Selecionar</option>
            {areas.map((area) => <option key={area} value={area}>{area}</option>)}
          </select>
        </label>
        <label>Curso
          <select value={payload.curso_id || ""} onChange={(e) => setPayload({ ...payload, curso_id: Number(e.target.value) })} disabled={!payload.area}>
            <option value="">Selecionar</option>
            {availableCourses.map((item) => <option key={item.id} value={item.id}>{item.curso} · {item.nivel} · estoque {item.estoque_total ?? 0}</option>)}
          </select>
        </label>
        {payload.curso_id && courseQuestions.loading && <Loading />}
        {payload.curso_id && courseQuestions.error && <ErrorMessage text={courseQuestions.error} />}
        {payload.curso_id && Boolean(courseQuestions.data?.items.length) && (
          <div className="question-list">
            <h3>Questionário da demanda</h3>
            {courseQuestions.data?.items.map((question) => (
              <QuestionRow key={question.id} question={question} kind="curso" value={answers[question.id]} onChange={(value) => setAnswers({ ...answers, [question.id]: value })} />
            ))}
          </div>
        )}
        {payload.curso_id && !courseQuestions.loading && !courseQuestions.error && !courseQuestions.data?.items.length && (
          <div className="alert warning">Este curso ainda nao possui questionario cadastrado. Voce pode salvar e seguir o fluxo normalmente.</div>
        )}
        <label>Observação
          <textarea value={payload.observacao || ""} onChange={(e) => setPayload({ ...payload, observacao: e.target.value })} />
        </label>
        {errorMessage && <div className="alert error">{errorMessage}</div>}
        <button disabled={!payload.entidade_id || !payload.curso_id || submitting}>{submitting ? "Salvando..." : "Salvar e iniciar fluxo"}</button>
      </form>
      {message && <div className="alert success">{message}</div>}
      {!qualified.length && <div className="empty">Finalize o Formulário Geral e o BPF de uma entidade para liberar cursos.</div>}
    </PageBlock>
  );
}

function StatusPage() {
  const { data, loading, error } = useAsync(api.protocols, []);
  if (loading) return <Loading />;
  if (error) return <ErrorMessage text={error} />;
  return <PageBlock title="Consultar Status"><DataTable rows={data?.items || []} /></PageBlock>;
}

function AprovacoesPage({ user }: { user: User }) {
  const [selected, setSelected] = useState("");
  const [message, setMessage] = useState("");
  const protocols = useAsync(api.protocols, [message]);
  const forms = useAsync(() => selected ? api.forms(selected) : Promise.resolve(null), [selected, message]);
  const rows = protocols.data?.items || [];

  async function advance() {
    if (!selected) return;
    const result = await api.advanceProtocol(selected, user.usuario);
    setMessage(result.message);
  }

  return (
    <PageBlock title="Minhas Aprovações">
      {message && <div className="alert success">{message}</div>}
      <DataTable rows={rows} />
      <div className="inline-form">
        <select value={selected} onChange={(e) => setSelected(e.target.value)}>
          <option value="">Selecionar protocolo</option>
          {rows.map((row) => <option key={row.protocolo} value={row.protocolo}>{row.protocolo} · {row.entidade} · {row.status}</option>)}
        </select>
        <button onClick={advance} disabled={!selected}>Aprovar / Avançar</button>
      </div>
      {selected && <DataTable rows={forms.data?.historico || []} empty="Sem histórico." />}
    </PageBlock>
  );
}

function StatusPageV2() {
  const { data, loading, error } = useAsync(api.protocols, []);
  const [status, setStatus] = useState("");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState("");
  const forms = useAsync(() => selected ? api.forms(selected) : Promise.resolve(null), [selected]);
  if (loading) return <Loading />;
  if (error) return <ErrorMessage text={error} />;
  const rows = data?.items || [];
  const filtered = filterProtocols(rows, status, query);
  const selectedRow = rows.find((row) => row.protocolo === selected);
  return (
    <PageBlock title="Consultar Status">
      <ProtocolFilters rows={rows} status={status} setStatus={setStatus} query={query} setQuery={setQuery} />
      <DataTable rows={filtered} />
      <div className="inline-form">
        <select value={selected} onChange={(e) => setSelected(e.target.value)}>
          <option value="">Selecionar protocolo</option>
          {filtered.map((row) => <option key={row.protocolo} value={row.protocolo}>{row.protocolo} · {row.entidade} · {row.status}</option>)}
        </select>
      </div>
      {selected && <ProtocolDetails row={selectedRow} forms={forms.data} />}
    </PageBlock>
  );
}

function AprovacoesPageV2({ user, onDone }: { user: User; onDone: () => void }) {
  const [selected, setSelected] = useState("");
  const [status, setStatus] = useState("");
  const [query, setQuery] = useState("");
  const [message, setMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const protocols = useAsync(api.protocols, [message]);
  const forms = useAsync(() => selected ? api.forms(selected) : Promise.resolve(null), [selected, message]);
  const rows = (protocols.data?.items || []).filter((row) => canHandleStatus(user, row.status));
  const filtered = filterProtocols(rows, status, query);
  const selectedRow = rows.find((row) => row.protocolo === selected);

  async function advance(observacao: string, dataAgendada: string) {
    if (!selected) return;
    setSubmitting(true);
    setErrorMessage("");
    setMessage("");
    try {
      const result = await api.advanceProtocol(selected, user.usuario, observacao, dataAgendada);
      setMessage(result.message || "Fluxo atualizado.");
      setSelected("");
    } catch (err: any) {
      setErrorMessage(err.message || "Erro ao avancar o protocolo.");
    } finally {
      setSubmitting(false);
    }
  }

  async function cancel(observacao: string) {
    if (!selected) return;
    setSubmitting(true);
    setErrorMessage("");
    setMessage("");
    try {
      const result = await api.cancelProtocol(selected, user.usuario, observacao);
      setMessage(result.message || "Protocolo cancelado.");
      setSelected("");
    } catch (err: any) {
      setErrorMessage(err.message || "Erro ao cancelar o protocolo.");
    } finally {
      setSubmitting(false);
    }
  }

  async function reject(observacao: string) {
    if (!selected) return;
    setSubmitting(true);
    setErrorMessage("");
    setMessage("");
    try {
      const result = await api.rejectProtocol(selected, user.usuario, observacao);
      setMessage(result.message || "Protocolo reprovado.");
      setSelected("");
    } catch (err: any) {
      setErrorMessage(err.message || "Erro ao reprovar o protocolo.");
    } finally {
      setSubmitting(false);
    }
  }

  async function waitlist(observacao: string) {
    if (!selected) return;
    setSubmitting(true);
    setErrorMessage("");
    setMessage("");
    try {
      const result = await api.waitlistProtocol(selected, user.usuario, observacao);
      setMessage(result.message || "Protocolo enviado para lista de espera.");
      setSelected("");
    } catch (err: any) {
      setErrorMessage(err.message || "Erro ao enviar o protocolo para lista de espera.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <PageBlock title="Minhas Aprovações">
      {message && <div className="alert success">{message}</div>}
      {errorMessage && <div className="alert error">{errorMessage}</div>}
      <ProtocolFilters rows={rows} status={status} setStatus={setStatus} query={query} setQuery={setQuery} />
      <DataTable rows={filtered} />
      <div className="inline-form">
        <select value={selected} onChange={(e) => setSelected(e.target.value)}>
          <option value="">Selecionar protocolo</option>
          {filtered.map((row) => <option key={row.protocolo} value={row.protocolo}>{row.protocolo} · {row.entidade} · {row.status}</option>)}
        </select>
      </div>
      {selected && <ProtocolDetails row={selectedRow} forms={forms.data} approval user={user} onAdvance={advance} onCancel={cancel} onReject={reject} onWaitlist={waitlist} busy={submitting} />}
    </PageBlock>
  );
}

type ConfigFieldType = "text" | "number" | "textarea" | "select" | "toggle";
type ConfigOption = { label: string; value: string };
type ConfigReferenceData = { cursos: Row[]; perguntasCurso: Row[] };
type ConfigFieldDefinition = {
  key: string;
  label: string;
  type?: ConfigFieldType;
  placeholder?: string;
  options?: ConfigOption[] | ((references: ConfigReferenceData) => ConfigOption[]);
};
type ConfigSchema = {
  title: string;
  description: string;
  addLabel: string;
  fields: ConfigFieldDefinition[];
  defaultRow: () => Row;
  itemLabel: (row: Row, references: ConfigReferenceData) => string;
};

const AREA_OPTIONS: ConfigOption[] = [
  { label: "CIMATEC", value: "CIMATEC" },
  { label: "SEBRAE", value: "SEBRAE" }
];

const LEVEL_OPTIONS: ConfigOption[] = [
  { label: "Básico", value: "Básico" },
  { label: "Intermediário", value: "Intermediário" },
  { label: "Avançado", value: "Avançado" }
];

const OWNER_STAGE_OPTIONS: ConfigOption[] = [
  { label: "Administrativo", value: "Administrativo" },
  { label: "Analise Tecnica", value: "Analise Tecnica" },
  { label: "Agendamento", value: "Agendamento" },
  { label: "Execucao", value: "Execucao" }
];

const CONFIG_SCHEMAS: Record<string, ConfigSchema> = {
  cursos: {
    title: "Cursos",
    description: "Cadastre cursos sem depender da tabela inteira. Selecione um item, edite os campos e salve.",
    addLabel: "Adicionar curso",
    defaultRow: () => ({ curso: "", area: "CIMATEC", nivel: "Básico", descricao: "", carga_horaria: "", estoque_total: 0, owner_email: "", ativo: true }),
    itemLabel: (row) => `${row.curso || "Novo curso"} · ${row.area || "-"} · ${row.nivel || "-"}`,
    fields: [
      { key: "curso", label: "Nome do curso", placeholder: "Ex.: Boas práticas de fabricação" },
      { key: "area", label: "Área", type: "select", options: AREA_OPTIONS },
      { key: "nivel", label: "Nível", type: "select", options: LEVEL_OPTIONS },
      { key: "descricao", label: "Descrição", type: "textarea" },
      { key: "carga_horaria", label: "Carga horária" },
      { key: "estoque_total", label: "Estoque total", type: "number" },
      { key: "owner_email", label: "Email do responsável" },
      { key: "ativo", label: "Ativo", type: "toggle" }
    ]
  },
  perguntas_qualificacao: {
    title: "Perguntas Entidade",
    description: "Crie perguntas do Formulário Geral com as opções e pontuações já organizadas.",
    addLabel: "Adicionar pergunta de entidade",
    defaultRow: () => ({ questionario: "", ordem: "", pergunta: "", tipo: "Multipla", opcao_1: "", opcao_2: "", opcao_3: "", pontos_1: 0, pontos_2: 5, pontos_3: 10, pontos_sim: 1, ativo: true }),
    itemLabel: (row) => `${row.questionario || "Questionário"} · ${row.ordem || "?"} · ${row.pergunta || "Nova pergunta"}`,
    fields: [
      { key: "questionario", label: "Questionário" },
      { key: "ordem", label: "Ordem", type: "number" },
      { key: "pergunta", label: "Pergunta", type: "textarea" },
      { key: "tipo", label: "Tipo" },
      { key: "opcao_1", label: "Opção 1" },
      { key: "pontos_1", label: "Pontos opção 1", type: "number" },
      { key: "opcao_2", label: "Opção 2" },
      { key: "pontos_2", label: "Pontos opção 2", type: "number" },
      { key: "opcao_3", label: "Opção 3" },
      { key: "pontos_3", label: "Pontos opção 3", type: "number" },
      { key: "pontos_sim", label: "Pontos padrão SIM", type: "number" },
      { key: "ativo", label: "Ativo", type: "toggle" }
    ]
  },
  perguntas_bpf: {
    title: "Perguntas BPF",
    description: "Edite ou adicione perguntas do BPF em um formulário mais limpo, com seção e opções separadas.",
    addLabel: "Adicionar pergunta BPF",
    defaultRow: () => ({ secao: "", subsecao: "", codigo_pergunta: "", ordem: "", pergunta: "", tipo_resposta: "Multipla", opcoes: "S;N;P;NA", pontos_sim: 1, ativo: true }),
    itemLabel: (row) => `${row.secao || "Seção"} · ${row.codigo_pergunta || row.ordem || "?"} · ${row.pergunta || "Nova pergunta"}`,
    fields: [
      { key: "secao", label: "Seção" },
      { key: "subsecao", label: "Subseção" },
      { key: "codigo_pergunta", label: "Código / título" },
      { key: "ordem", label: "Ordem", type: "number" },
      { key: "pergunta", label: "Pergunta", type: "textarea" },
      { key: "tipo_resposta", label: "Tipo de resposta" },
      { key: "opcoes", label: "Opções (separadas por ;)" },
      { key: "pontos_sim", label: "Pontos do SIM", type: "number" },
      { key: "ativo", label: "Ativo", type: "toggle" }
    ]
  },
  perguntas_curso: {
    title: "Perguntas Curso",
    description: "Escolha o curso, defina a ordem e escreva a pergunta sem precisar navegar por uma planilha gigante.",
    addLabel: "Adicionar pergunta de curso",
    defaultRow: () => ({ curso_id: "", ordem: "", pergunta: "", pontos_sim: 1, ativo: true }),
    itemLabel: (row, references) => {
      const course = references.cursos.find((item) => String(item.id) === String(row.curso_id));
      return `${course?.curso || "Curso"} · ${row.ordem || "?"} · ${row.pergunta || "Nova pergunta"}`;
    },
    fields: [
      { key: "curso_id", label: "Curso", type: "select", options: (references) => references.cursos.map((item) => ({ label: `${item.curso} · ${item.area || "-"}`, value: String(item.id) })) },
      { key: "ordem", label: "Ordem", type: "number" },
      { key: "pergunta", label: "Pergunta", type: "textarea" },
      { key: "pontos_sim", label: "Pontos padrão", type: "number" },
      { key: "ativo", label: "Ativo", type: "toggle" }
    ]
  },
  alternativas_curso: {
    title: "Alternativas Curso",
    description: "Cadastre as alternativas vinculadas à pergunta correta, com ordem e pontuação separadas.",
    addLabel: "Adicionar alternativa",
    defaultRow: () => ({ pergunta_id: "", ordem: "", alternativa: "", pontos: 0, ativo: true }),
    itemLabel: (row, references) => {
      const question = references.perguntasCurso.find((item) => String(item.id) === String(row.pergunta_id));
      return `${question?.pergunta || "Pergunta"} · ${row.ordem || "?"} · ${row.alternativa || "Nova alternativa"}`;
    },
    fields: [
      { key: "pergunta_id", label: "Pergunta do curso", type: "select", options: (references) => references.perguntasCurso.map((item) => ({ label: `${item.id} · ${item.pergunta}`, value: String(item.id) })) },
      { key: "ordem", label: "Ordem", type: "number" },
      { key: "alternativa", label: "Alternativa", type: "textarea" },
      { key: "pontos", label: "Pontos", type: "number" },
      { key: "ativo", label: "Ativo", type: "toggle" }
    ]
  },
  owners_area: {
    title: "Owners por Área",
    description: "Defina responsáveis por área e etapa em uma lista simples, com remoção rápida e visual limpa.",
    addLabel: "Adicionar owner",
    defaultRow: () => ({ area: "CIMATEC", etapa: "Administrativo", nome: "", email: "", usuario: "", ativo: true }),
    itemLabel: (row) => `${row.area || "Área"} · ${row.etapa || "Etapa"} · ${row.nome || "Novo owner"}`,
    fields: [
      { key: "area", label: "Área", type: "select", options: AREA_OPTIONS },
      { key: "etapa", label: "Etapa", type: "select", options: OWNER_STAGE_OPTIONS },
      { key: "nome", label: "Nome" },
      { key: "email", label: "Email" },
      { key: "usuario", label: "Usuário" },
      { key: "ativo", label: "Ativo", type: "toggle" }
    ]
  },
  entidades: {
    title: "Entidades",
    description: "Atualize os dados principais da entidade em um cadastro focado, sem precisar editar coluna por coluna na grade.",
    addLabel: "Adicionar entidade",
    defaultRow: () => ({ entidade: "", cnpj: "", municipio_entidade: "", certificacao: "", email_responsavel: "", telefone: "", endereco: "", ativo: true }),
    itemLabel: (row) => `${row.entidade || "Nova entidade"} · ${row.cnpj || "Sem CNPJ"}`,
    fields: [
      { key: "entidade", label: "Nome da entidade" },
      { key: "cnpj", label: "CNPJ" },
      { key: "municipio_entidade", label: "Município" },
      { key: "territorio_identidade", label: "Território" },
      { key: "certificacao", label: "Certificação" },
      { key: "licenca_ambiental", label: "Licença ambiental" },
      { key: "email_responsavel", label: "Email responsável" },
      { key: "telefone", label: "Telefone" },
      { key: "endereco", label: "Endereço", type: "textarea" },
      { key: "ativo", label: "Ativo", type: "toggle" }
    ]
  }
};

function makeTempKey() {
  return `tmp_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function fieldOptions(field: ConfigFieldDefinition, references: ConfigReferenceData) {
  if (!field.options) return [];
  return typeof field.options === "function" ? field.options(references) : field.options;
}

function ConfigCollectionEditor({ table, rows, onChange, references }: { table: string; rows: Row[]; onChange: (rows: Row[]) => void; references: ConfigReferenceData }) {
  const schema = CONFIG_SCHEMAS[table];
  const [search, setSearch] = useState("");
  const [showInactive, setShowInactive] = useState(false);
  const [selectedKey, setSelectedKey] = useState("");

  const visibleRows = rows.filter((row) => {
    if (!showInactive && row.ativo != null && String(row.ativo) === "false") return false;
    const label = schema.itemLabel(row, references).toLowerCase();
    return !search.trim() || label.includes(search.trim().toLowerCase());
  });

  useEffect(() => {
    if (!visibleRows.length) {
      setSelectedKey("");
      return;
    }
    if (!visibleRows.some((row) => String(row.id ?? row._tempKey ?? "") === selectedKey)) {
      setSelectedKey(String(visibleRows[0].id ?? visibleRows[0]._tempKey ?? ""));
    }
  }, [selectedKey, visibleRows]);

  function addRecord() {
    const nextRow = { ...schema.defaultRow(), _tempKey: makeTempKey() };
    onChange([nextRow, ...rows]);
    setSelectedKey(String(nextRow._tempKey));
  }

  function updateRecord(recordKey: string, field: string, value: unknown) {
    onChange(
      rows.map((row) => {
        const key = String(row.id ?? row._tempKey ?? "");
        return key === recordKey ? { ...row, [field]: value } : row;
      })
    );
  }

  function removeRecord(recordKey: string) {
    const target = rows.find((row) => String(row.id ?? row._tempKey ?? "") === recordKey);
    if (!target) return;
    const label = schema.itemLabel(target, references);
    if (!window.confirm(`Remover "${label}"?`)) return;
    const nextRows = rows.filter((row) => String(row.id ?? row._tempKey ?? "") !== recordKey);
    onChange(nextRows);
    setSelectedKey("");
  }

  const selectedRow = rows.find((row) => String(row.id ?? row._tempKey ?? "") === selectedKey);

  return (
    <div className="config-workspace">
      <aside className="config-list-panel">
        <div className="config-list-header">
          <div>
            <h3>{schema.title}</h3>
            <p>{schema.description}</p>
          </div>
          <button type="button" onClick={addRecord}>{schema.addLabel}</button>
        </div>
        <div className="config-list-tools">
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder={`Buscar em ${schema.title.toLowerCase()}`} />
          <label className="toggle-row">
            <input type="checkbox" checked={showInactive} onChange={(e) => setShowInactive(e.target.checked)} />
            <span>Mostrar inativos</span>
          </label>
        </div>
        <div className="config-record-list">
          {visibleRows.length ? visibleRows.map((row) => {
            const recordKey = String(row.id ?? row._tempKey ?? "");
            const active = selectedKey === recordKey;
            return (
              <button key={recordKey} type="button" className={active ? "config-record-item active" : "config-record-item"} onClick={() => setSelectedKey(recordKey)}>
                <strong>{schema.itemLabel(row, references)}</strong>
                <span>{row.id ? `ID ${row.id}` : "Novo registro"}</span>
              </button>
            );
          }) : <div className="empty">Nenhum registro encontrado.</div>}
        </div>
      </aside>
      <section className="config-form-panel">
        {selectedRow ? (
          <>
            <div className="config-form-header">
              <div>
                <h3>{schema.itemLabel(selectedRow, references)}</h3>
                <p>Edite os campos abaixo e use remover apenas para o item selecionado.</p>
              </div>
              <button type="button" className="danger" onClick={() => removeRecord(String(selectedRow.id ?? selectedRow._tempKey ?? ""))}>Remover item</button>
            </div>
            <div className="form-grid">
              {schema.fields.map((field) => {
                const value = selectedRow[field.key];
                const options = fieldOptions(field, references);
                if (field.type === "textarea") {
                  return (
                    <label key={field.key}>
                      {field.label}
                      <textarea value={String(value ?? "")} onChange={(e) => updateRecord(String(selectedRow.id ?? selectedRow._tempKey ?? ""), field.key, e.target.value)} />
                    </label>
                  );
                }
                if (field.type === "select") {
                  return (
                    <label key={field.key}>
                      {field.label}
                      <select value={String(value ?? "")} onChange={(e) => updateRecord(String(selectedRow.id ?? selectedRow._tempKey ?? ""), field.key, e.target.value)}>
                        <option value="">Selecionar</option>
                        {options.map((option) => <option key={`${field.key}_${option.value}`} value={option.value}>{option.label}</option>)}
                      </select>
                    </label>
                  );
                }
                if (field.type === "toggle") {
                  return (
                    <label key={field.key} className="toggle-card">
                      <span>{field.label}</span>
                      <input type="checkbox" checked={Boolean(value)} onChange={(e) => updateRecord(String(selectedRow.id ?? selectedRow._tempKey ?? ""), field.key, e.target.checked)} />
                    </label>
                  );
                }
                return (
                  <label key={field.key}>
                    {field.label}
                    <input
                      type={field.type === "number" ? "number" : "text"}
                      value={String(value ?? "")}
                      placeholder={field.placeholder || ""}
                      onChange={(e) => updateRecord(String(selectedRow.id ?? selectedRow._tempKey ?? ""), field.key, field.type === "number" ? e.target.value : e.target.value)}
                    />
                  </label>
                );
              })}
            </div>
          </>
        ) : (
          <div className="empty">Escolha um item da lista ou clique em adicionar para começar.</div>
        )}
      </section>
    </div>
  );
}

function ConfigPage() {
  const [table, setTable] = useState("cursos");
  const [rows, setRows] = useState<Row[]>([]);
  const [message, setMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const pendingPasswordUsers =
    table === "usuarios"
      ? rows.filter((row) => !row.id && String(row.email || row.usuario || row.nome || "").trim() && !row.senha_hash)
      : [];
  const courseReferences = useAsync(() => api.table("cursos"), [message]);
  const questionReferences = useAsync(() => api.table("perguntas_curso"), [message]);

  useEffect(() => {
    setErrorMessage("");
    api.table(table)
      .then((data) => setRows(data.items))
      .catch((err: any) => setErrorMessage(err.message || "Erro ao carregar tabela."));
  }, [table, message]);

  async function save() {
    setErrorMessage("");
    if (table === "usuarios" && pendingPasswordUsers.length) {
      setErrorMessage("Gere a senha temporaria dos novos usuarios antes de salvar a tabela.");
      return;
    }
    try {
      await api.saveTable(table, rows);
      setMessage("Tabela salva.");
    } catch (err: any) {
      setErrorMessage(err.message || "Erro ao salvar tabela.");
    }
  }

  async function processNotificationQueue() {
    setErrorMessage("");
    setMessage("");
    try {
      const result = await api.processNotifications(100);
      setMessage(result.message);
    } catch (err: any) {
      setErrorMessage(err.message || "Erro ao processar fila de notificacoes.");
    }
  }

  const references: ConfigReferenceData = {
    cursos: courseReferences.data?.items || [],
    perguntasCurso: questionReferences.data?.items || []
  };

  return (
    <PageBlock title="Configurações">
      <Tabs value={table} onChange={setTable as any} items={Object.entries(tableLabels)} />
      {message && <div className="alert success">{message}</div>}
      {errorMessage && <div className="alert error">{errorMessage}</div>}
      {table === "usuarios" && !!pendingPasswordUsers.length && (
        <div className="alert warning">Antes de salvar, clique em `Gerar senha` para cada novo usuario adicionado.</div>
      )}
      {table === "notificacoes" ? (
        <>
          <div className="config-notice">
            <p>As notificações ficam em uma fila simples. Você pode revisar os registros abaixo ou processar a fila manualmente.</p>
            <button type="button" onClick={processNotificationQueue}>Processar fila de notificacoes</button>
          </div>
          <DataTable rows={rows} />
        </>
      ) : table === "usuarios" ? (
        <UsersManagementTable rows={rows} onChange={setRows} />
      ) : (
        <ConfigCollectionEditor table={table} rows={rows} onChange={setRows} references={references} />
      )}
      {table !== "notificacoes" && <button onClick={save}>Salvar alterações</button>}
    </PageBlock>
  );
}

function UsersManagementTable({ rows, onChange }: { rows: Row[]; onChange: (rows: Row[]) => void }) {
  const [search, setSearch] = useState("");
  const [selectedKey, setSelectedKey] = useState("");

  function addUser() {
    const newUser = {
      email: "",
      usuario: "",
      nome: "",
      perfil: null,
      ativo: true,
      acesso_pendente: false,
      senha_temporaria: false,
      trocar_senha_obrigatorio: false,
      _tempKey: makeTempKey()
    };
    onChange([newUser, ...rows]);
    setSelectedKey(String(newUser._tempKey));
  }

  function update(recordKey: string, patch: Row) {
    onChange(
      rows.map((row) => {
        const key = String(row.id ?? row._tempKey ?? "");
        return key === recordKey ? { ...row, ...patch } : row;
      })
    );
  }

  function remove(recordKey: string) {
    const target = rows.find((row) => String(row.id ?? row._tempKey ?? "") === recordKey);
    if (!target) return;
    const label = target.nome || target.email || target.usuario || "este usuário";
    if (!window.confirm(`Remover "${label}"?`)) return;
    onChange(rows.filter((row) => String(row.id ?? row._tempKey ?? "") !== recordKey));
    setSelectedKey("");
  }

  async function hashValue(value: string) {
    const buffer = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
    return Array.from(new Uint8Array(buffer)).map((byte) => byte.toString(16).padStart(2, "0")).join("");
  }

  function tempPassword() {
    const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789";
    return Array.from({ length: 10 }, () => alphabet[Math.floor(Math.random() * alphabet.length)]).join("");
  }

  function statusValue(row: Row) {
    if (String(row.ativo) === "false" || row.ativo === false || row.ativo === 0) return "Inativo";
    if (row.acesso_pendente || !row.perfil) return "Pendente";
    return "Ativo";
  }

  async function resetPassword(recordKey: string) {
    const senha = tempPassword();
    const senha_hash = await hashValue(senha);
    update(recordKey, {
      senha_hash,
      senha_temporaria: true,
      trocar_senha_obrigatorio: true,
      generated_temp_password: senha
    });
  }

  const visibleRows = rows.filter((row) => {
    const term = search.trim().toLowerCase();
    if (!term) return true;
    return [row.nome, row.email, row.usuario, row.perfil].some((value) => String(value || "").toLowerCase().includes(term));
  });

  useEffect(() => {
    if (!visibleRows.length) {
      setSelectedKey("");
      return;
    }
    if (!visibleRows.some((row) => String(row.id ?? row._tempKey ?? "") === selectedKey)) {
      setSelectedKey(String(visibleRows[0].id ?? visibleRows[0]._tempKey ?? ""));
    }
  }, [selectedKey, visibleRows]);

  const selectedRow = rows.find((row) => String(row.id ?? row._tempKey ?? "") === selectedKey);
  const selectedRecordKey = String(selectedRow?.id ?? selectedRow?._tempKey ?? "");

  return (
    <div className="config-workspace">
      <aside className="config-list-panel">
        <div className="config-list-header">
          <div>
            <h3>Usuários</h3>
            <p>Crie acessos, ajuste cargo e status e gere senha temporária sem depender de uma grade gigante.</p>
          </div>
          <button type="button" onClick={addUser}>Adicionar usuário</button>
        </div>
        <div className="config-list-tools">
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar por nome, email ou cargo" />
        </div>
        <div className="config-record-list">
          {visibleRows.length ? visibleRows.map((row) => {
            const recordKey = String(row.id ?? row._tempKey ?? "");
            const active = selectedKey === recordKey;
            return (
              <button key={recordKey} type="button" className={active ? "config-record-item active" : "config-record-item"} onClick={() => setSelectedKey(recordKey)}>
                <strong>{row.nome || row.email || row.usuario || "Novo usuário"}</strong>
                <span>{row.email || row.usuario || "Sem login"} · {row.perfil || statusValue(row)}</span>
              </button>
            );
          }) : <div className="empty">Nenhum usuário encontrado.</div>}
        </div>
      </aside>
      <section className="config-form-panel">
        {selectedRow ? (
          <>
            <div className="config-form-header">
              <div>
                <h3>{selectedRow.nome || selectedRow.email || selectedRow.usuario || "Novo usuário"}</h3>
                <p>Defina o acesso, gere a senha temporária e remova apenas quando tiver certeza.</p>
              </div>
              <button type="button" className="danger" onClick={() => remove(selectedRecordKey)}>Remover usuário</button>
            </div>
            <div className="form-grid">
              <label>E-mail / login
                <input value={selectedRow.email ?? selectedRow.usuario ?? ""} onChange={(e) => update(selectedRecordKey, { email: e.target.value, usuario: e.target.value })} />
              </label>
              <label>Nome
                <input value={selectedRow.nome ?? ""} onChange={(e) => update(selectedRecordKey, { nome: e.target.value })} />
              </label>
              <label>Cargo
                <select
                  value={selectedRow.perfil ?? ""}
                  onChange={(e) => update(selectedRecordKey, { perfil: e.target.value || null, acesso_pendente: !e.target.value })}
                >
                  <option value="">Selecionar cargo</option>
                  {USER_ROLE_OPTIONS.map((role) => <option key={role} value={role}>{role}</option>)}
                </select>
              </label>
              <label>Status
                <select
                  value={statusValue(selectedRow)}
                  onChange={(e) => update(selectedRecordKey, {
                    ativo: e.target.value !== "Inativo",
                    acesso_pendente: e.target.value === "Pendente"
                  })}
                >
                  <option value="Ativo">Ativo</option>
                  <option value="Inativo">Inativo</option>
                  <option value="Pendente">Pendente</option>
                </select>
              </label>
              <div className="password-reset-card">
                <strong>Senha temporária</strong>
                <span>{selectedRow.generated_temp_password || "Nenhuma senha gerada nesta edição."}</span>
                <button className="icon" type="button" onClick={() => resetPassword(selectedRecordKey)}>Gerar senha</button>
              </div>
              <label className="toggle-card">
                <span>Trocar senha no próximo acesso</span>
                <input type="checkbox" checked={Boolean(selectedRow.trocar_senha_obrigatorio)} onChange={(e) => update(selectedRecordKey, { trocar_senha_obrigatorio: e.target.checked })} />
              </label>
            </div>
          </>
        ) : (
          <div className="empty">Escolha um usuário da lista ou clique em adicionar para começar.</div>
        )}
      </section>
    </div>
  );
}

function DataTable({ rows, empty = "Nenhum registro encontrado." }: { rows: Row[]; empty?: string }) {
  if (!rows.length) return <div className="empty">{empty}</div>;
  const cols = Array.from(new Set(rows.flatMap((row) => Object.keys(row)))).slice(0, 12);
  return (
    <div className="table-scroll">
      <table>
        <thead><tr>{cols.map((col) => <th key={col}>{col}</th>)}</tr></thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>{cols.map((col) => <td key={col}>{String(row[col] ?? "")}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function filterProtocols(rows: Row[], status: string, query: string) {
  const term = query.trim().toLowerCase();
  return rows.filter((row) => {
    const statusOk = !status || row.status === status;
    const protocolOk = !term || String(row.protocolo || "").toLowerCase().includes(term);
    return statusOk && protocolOk;
  });
}

function statusOptions(rows: Row[]) {
  return Array.from(new Set(rows.map((row) => row.status).filter(Boolean))).sort();
}

function actionLabel(status: string) {
  const key = String(status || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  if (key.includes("agendamento")) return "Enviar agendamento";
  if (key.includes("execucao")) return "Finalizar";
  if (key.includes("analise")) return "Enviar para Agendamento";
  if (key.includes("validacao")) return "Aprovar e enviar para Analise Tecnica";
  return "Enviar";
}

function ProtocolFilters({ rows, status, setStatus, query, setQuery }: { rows: Row[]; status: string; setStatus: (value: string) => void; query: string; setQuery: (value: string) => void }) {
  return (
    <div className="filters-bar">
      <label>Status
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">Todos</option>
          {statusOptions(rows).map((item) => <option key={item} value={item}>{item}</option>)}
        </select>
      </label>
      <label>Protocolo
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Buscar protocolo" />
      </label>
    </div>
  );
}

function ResponseSection({ title, rows, empty }: { title: string; rows: Row[]; empty: string }) {
  return (
    <details className="response-section">
      <summary>{title} <span>{rows.length}</span></summary>
      <DataTable rows={rows} empty={empty} />
    </details>
  );
}

function ProtocolDetails({ row, forms, approval = false, user, onAdvance, onCancel, onReject, onWaitlist, busy = false }: { row: Row | undefined; forms: any; approval?: boolean; user?: User; onAdvance?: (observacao: string, dataAgendada: string) => Promise<void>; onCancel?: (observacao: string) => Promise<void>; onReject?: (observacao: string) => Promise<void>; onWaitlist?: (observacao: string) => Promise<void>; busy?: boolean }) {
  const [observacao, setObservacao] = useState("");
  const [dataAgendada, setDataAgendada] = useState("");
  const [osError, setOsError] = useState("");
  const [downloadingOs, setDownloadingOs] = useState(false);
  if (!row) return <div className="empty">Selecione um protocolo para ver os detalhes.</div>;
  const currentRow = row;
  const finalizado = ["Finalizado", "Cancelado", "Reprovado"].includes(String(currentRow.status || ""));
  const statusKey = String(currentRow.status || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  const canDownloadOs = ["agendamento", "execucao", "finalizado"].includes(statusKey);
  const needsDecisionButtons = ["validacao administrativa", "analise tecnica"].includes(statusKey);

  async function downloadOs() {
    setOsError("");
    setDownloadingOs(true);
    try {
      await api.downloadOs(String(currentRow.protocolo));
    } catch (err: any) {
      setOsError(err.message || "Erro ao gerar a OS.");
    } finally {
      setDownloadingOs(false);
    }
  }

  return (
    <section className="detail-panel">
      <div className="detail-header">
        <div>
          <h3>{currentRow.protocolo}</h3>
          <p>{currentRow.entidade || "-"} · {currentRow.curso || "-"} · {currentRow.status || "-"}</p>
        </div>
        {canDownloadOs ? (
          <button className="download-button" onClick={downloadOs} type="button" disabled={downloadingOs}>
            {downloadingOs ? "Gerando OS..." : "Baixar OS preenchida"}
          </button>
        ) : (
          <span className="muted">OS será gerada ao enviar para Agendamento.</span>
        )}
      </div>
      {osError && <div className="alert error">{osError}</div>}
      <div className="detail-grid">
        <Metric title="Área" value={currentRow.area || "-"} />
        <Metric title="Responsável" value={currentRow.responsavel_atual || currentRow.etapa_atual || "-"} />
        <Metric title="Agendamento" value={currentRow.data_agendada || "-"} />
        <Metric title="Pontuação curso" value={currentRow.pontuacao_curso ?? 0} />
      </div>
      <h3>Histórico de movimentação</h3>
      <DataTable rows={forms?.historico || []} empty="Sem histórico." />
      <ResponseSection title="Formulario Geral" rows={forms?.geral || []} empty="Sem respostas do Formulario Geral." />
      <ResponseSection title="BPF" rows={forms?.bpf || []} empty="Sem respostas do BPF." />
      <ResponseSection title="Formulario do Curso" rows={forms?.curso || []} empty="Sem respostas do curso." />
      {approval && finalizado && <div className="alert error">Este protocolo esta encerrado e nao permite novas acoes.</div>}      {approval && !finalizado && (
        <div className="approval-actions">
          {String(currentRow.status || "") === "Agendamento" && (
            <label>Data para iniciar execução
              <input type="datetime-local" value={dataAgendada} onChange={(e) => setDataAgendada(e.target.value)} />
            </label>
          )}
          <label>Observação da decisão
            <textarea value={observacao} onChange={(e) => setObservacao(e.target.value)} />
          </label>
          <div className="action-row">
            <button onClick={() => onAdvance?.(observacao, dataAgendada)} disabled={busy || !user || (String(currentRow.status || "") === "Agendamento" && !dataAgendada)}>
              {busy ? "Enviando..." : actionLabel(String(currentRow.status || ""))}
            </button>
            {needsDecisionButtons ? (
              <>
                <button className="warning-button" onClick={() => onWaitlist?.(observacao)} disabled={busy || !user}>Lista de espera</button>
                <button className="danger" onClick={() => onReject?.(observacao)} disabled={busy || !user}>Reprovar</button>
              </>
            ) : (
              <button className="danger" onClick={() => onCancel?.(observacao)} disabled={busy || !user}>Cancelar</button>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

function Tabs({ value, onChange, items }: { value: any; onChange: (value: any) => void; items: [any, string][] }) {
  return <div className="tabs">{items.map(([id, label]) => <button key={id} className={value === id ? "active" : ""} onClick={() => onChange(id)}>{label}</button>)}</div>;
}

function PageBlock({ title, children }: { title: string; children: React.ReactNode }) {
  return <main><h2 className="page-title">{title}</h2>{children}</main>;
}

function Metric({ title, value }: { title: string; value: any }) {
  return <div className="metric"><strong>{value ?? 0}</strong><span>{title}</span></div>;
}

function Loading() { return <div className="empty">Carregando...</div>; }
function ErrorMessage({ text }: { text: string }) { return <div className="alert error">{text}</div>; }

function hasBrowserStorage() {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

function saveStoredUser(user: User) {
  if (!hasBrowserStorage()) return;
  window.localStorage.setItem("bahia_user", JSON.stringify(user));
}

function clearStoredUser() {
  if (!hasBrowserStorage()) return;
  window.localStorage.removeItem("bahia_user");
}

function getStoredUser() {
  if (!hasBrowserStorage()) return null;
  const raw = window.localStorage.getItem("bahia_user");
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    window.localStorage.removeItem("bahia_user");
    return null;
  }
}

export default function App() {
  const [user, setUser] = useState<User | null>(getStoredUser);
  const [page, setPage] = useState<Page>("home");

  if (!user) return <Login onLogin={setUser} />;

  function logout() {
    clearStoredUser();
    setUser(null);
  }

  return (
    <Layout user={user} page={page} setPage={setPage} logout={logout}>
      {page === "home" && <HomePage user={user} />}
      {page === "entidades" && <EntidadesPage user={user} />}
      {page === "qualificacao" && <QualificacaoPage />}
      {page === "cursos" && <CursosPageV2 user={user} />}
      {page === "status" && <StatusPageV2 />}
      {page === "aprovacoes" && <AprovacoesPageV2 user={user} onDone={() => setPage("home")} />}
      {page === "config" && <ConfigPage />}
    </Layout>
  );
}
