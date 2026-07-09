import { createClient } from "@supabase/supabase-js";

export type User = {
  id: number;
  nome: string;
  usuario: string;
  email?: string;
  perfil: string;
  ativo?: boolean | number;
  senha_temporaria?: boolean | number;
  trocar_senha_obrigatorio?: boolean | number;
  acesso_pendente?: boolean | number;
};

export type Row = Record<string, any>;

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || import.meta.env.SUPABASE_URL;
const supabaseAnonKey =
  import.meta.env.VITE_SUPABASE_ANON_KEY ||
  import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY ||
  import.meta.env.SUPABASE_ANON_KEY ||
  import.meta.env.SUPABASE_PUBLISHABLE_KEY;
const useSupabase = Boolean(supabaseUrl && supabaseAnonKey);
const supabase = useSupabase ? createClient(supabaseUrl, supabaseAnonKey) : null;

const STATUS_FLUXO = [
  "Validação Administrativa",
  "Análise Técnica",
  "Agendamento",
  "Execução",
  "Finalizado",
  "Cancelado",
  "Reprovado"
];

const FORM_GERAL_PENDENTE = "Formulario geral pendente";
const CADASTRO_INICIAL = "Cadastro inicial";

async function sha256(value: string) {
  const buffer = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(buffer)).map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

function nowStr() {
  return new Date().toISOString().slice(0, 19).replace("T", " ");
}

function tempPassword() {
  const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789";
  return Array.from({ length: 10 }, () => alphabet[Math.floor(Math.random() * alphabet.length)]).join("");
}

function nextStep(status: string) {
  const steps: Record<string, [string, string]> = {
    "Validação Administrativa": ["Análise Técnica", "Técnico"],
    "Análise Técnica": ["Agendamento", "Agendamento"],
    Agendamento: ["Execução", "Executor"],
    Execução: ["Finalizado", "Finalizado"]
  };
  return steps[status] || [status, ""];
}

function levelByPoints(points: number) {
  if (points <= 20) return "Básico";
  if (points <= 35) return "Intermediário";
  return "Avançado";
}

function dbTrue(value: unknown) {
  return value === true || value === 1 || value === "1" || String(value).toLowerCase() === "true";
}

function dbFalse(value: unknown) {
  return value === false || value === 0 || value === "0" || String(value).toLowerCase() === "false";
}

function isActive(row: Row) {
  return row.ativo == null || dbTrue(row.ativo);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    }
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || "Erro na requisição.");
  }
  return data as T;
}

function ensureSupabase() {
  if (!supabase) throw new Error("Supabase não está configurado no ambiente.");
  return supabase;
}

function throwDb(error: any) {
  if (error) throw new Error(error.message || "Erro no Supabase.");
}

const flaskApi = {
  login: (usuario: string, senha: string) =>
    request<{ user: User }>("/api/login", { method: "POST", body: JSON.stringify({ usuario, senha }) }),
  register: (email: string) =>
    request<{ message: string }>("/api/register", { method: "POST", body: JSON.stringify({ email }) }),
  changePassword: (userId: number, senha: string) =>
    request<{ user: User; message: string }>("/api/change-password", { method: "POST", body: JSON.stringify({ user_id: userId, senha }) }),
  dashboard: () => request<any>("/api/dashboard"),
  entities: () => request<{ items: Row[] }>("/api/entities"),
  createEntity: (entidade: string, user: User) =>
    request<{ id: number; message: string }>("/api/entities", { method: "POST", body: JSON.stringify({ entidade, usuario: user.usuario, email: user.email || "" }) }),
  qualificationOptions: () => request<{ items: Row[] }>("/api/qualification/start-options"),
  pendingQualification: (kind: "geral" | "bpf") => request<{ items: Row[] }>(`/api/qualification/pending/${kind}`),
  questions: (kind: "geral" | "bpf") => request<{ items: Row[] }>(`/api/questions/${kind}`),
  saveCadastro: (id: number, fields: Row) =>
    request<{ message: string }>("/api/qualification/cadastro", { method: "POST", body: JSON.stringify({ id, fields }) }),
  saveGeneral: (entidade_id: number, respostas: Row[]) =>
    request<any>("/api/qualification/general", { method: "POST", body: JSON.stringify({ entidade_id, respostas }) }),
  saveBpf: (entidade_id: number, respostas: Row[]) =>
    request<any>("/api/qualification/bpf", { method: "POST", body: JSON.stringify({ entidade_id, respostas }) }),
  courses: () => request<{ items: Row[] }>("/api/courses"),
  courseQuestions: (courseId: number) => request<{ items: Row[] }>(`/api/courses/${courseId}/questions`),
  protocols: () => request<{ items: Row[]; status: string[] }>("/api/protocols"),
  createProtocol: (payload: Row) => request<any>("/api/protocols", { method: "POST", body: JSON.stringify(payload) }),
  advanceProtocol: (protocolo: string, usuario: string, observacao = "", data_agendada = "") =>
    request<any>(`/api/protocols/${protocolo}/advance`, { method: "POST", body: JSON.stringify({ usuario, observacao, data_agendada }) }),
  cancelProtocol: (protocolo: string, usuario: string, observacao = "") =>
    request<any>(`/api/protocols/${protocolo}/cancel`, { method: "POST", body: JSON.stringify({ usuario, observacao }) }),
  forms: (protocolo: string) => request<any>(`/api/forms/${protocolo}`),
  table: (table: string) => request<{ items: Row[] }>(`/api/admin/table/${table}`),
  saveTable: (table: string, rows: Row[]) =>
    request<any>(`/api/admin/table/${table}`, { method: "POST", body: JSON.stringify({ rows }) })
};

const supabaseApi = {
  async login(usuario: string, senha: string) {
    const db = ensureSupabase();
    const senha_hash = await sha256(senha);
    const login = usuario.trim().toLowerCase();
    const { data, error } = await db
      .from("usuarios")
      .select("*")
      .or(`usuario.eq.${login},email.eq.${login}`)
      .limit(1)
      .maybeSingle();
    throwDb(error);
    if (data && dbFalse(data.ativo)) throw new Error("Este usuário está inativo. Procure um administrador.");
    if (!data || data.senha_hash !== senha_hash) throw new Error("Usuário ou senha inválidos.");
    return { user: data as User };
  },

  async register(email: string) {
    const db = ensureSupabase();
    const cleanEmail = email.trim().toLowerCase();
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(cleanEmail)) throw new Error("Informe um e-mail válido.");
    const senha = tempPassword();
    const senha_hash = await sha256(senha);
    const data_solicitacao = nowStr();
    const { data: existing, error: lookupError } = await db
      .from("usuarios")
      .select("*")
      .or(`usuario.eq.${cleanEmail},email.eq.${cleanEmail}`)
      .limit(1)
      .maybeSingle();
    throwDb(lookupError);
    if (existing) {
      const { error } = await db
        .from("usuarios")
        .update({ senha_hash, senha_temporaria: true, trocar_senha_obrigatorio: true, acesso_pendente: true, perfil: "Pendente", data_solicitacao })
        .eq("id", existing.id);
      throwDb(error);
    } else {
      const { error } = await db.from("usuarios").insert({
        nome: cleanEmail,
        usuario: cleanEmail,
        email: cleanEmail,
        senha_hash,
        perfil: "Pendente",
        senha_temporaria: true,
        trocar_senha_obrigatorio: true,
        acesso_pendente: true,
        data_solicitacao,
        ativo: true
      });
      throwDb(error);
    }
    await db.from("notificacoes").insert({
      protocolo: `ACESSO-${cleanEmail}`,
      destinatario: cleanEmail,
      assunto: "Senha temporária - Sistema Bahia",
      corpo: `Olá.\n\nCriamos um acesso temporário para o Sistema Bahia.\n\nE-mail: ${cleanEmail}\nSenha temporária: ${senha}\n\nAo entrar, defina uma nova senha.`,
      enviado: false,
      data_criacao: data_solicitacao,
      erro: "E-mail real precisa de Edge Function/SMTP. Senha temporária registrada no sistema."
    });
    return { message: "Usuário criado. A senha temporária foi registrada nas notificações do sistema." };
  },

  async changePassword(userId: number, senha: string) {
    const db = ensureSupabase();
    if (senha.length < 6) throw new Error("A nova senha deve ter pelo menos 6 caracteres.");
    const senha_hash = await sha256(senha);
    const { error } = await db
      .from("usuarios")
      .update({ senha_hash, senha_temporaria: false, trocar_senha_obrigatorio: false })
      .eq("id", userId);
    throwDb(error);
    const { data, error: lookupError } = await db.from("usuarios").select("*").eq("id", userId).single();
    throwDb(lookupError);
    return { message: "Senha definida com sucesso.", user: data as User };
  },

  async dashboard() {
    const db = ensureSupabase();
    const [entidadesRes, cursosRes, protocolosRes] = await Promise.all([
      db.from("entidades").select("*"),
      db.from("cursos").select("*"),
      db.from("protocolos").select("*")
    ]);
    throwDb(entidadesRes.error || cursosRes.error || protocolosRes.error);
    const entidades = (entidadesRes.data || []).filter(isActive);
    const cursos = (cursosRes.data || []).filter(isActive);
    const protocolos = protocolosRes.data || [];
    return {
      cards: {
        entidades: entidades.length,
        qualificadas: entidades.filter((e) => e.status_qualificacao === "Concluída" || e.status_qualificacao === "Concluida").length,
        formGeralPendentes: entidades.filter((e) => e.status_qualificacao === FORM_GERAL_PENDENTE).length,
        bpfPendentes: entidades.filter((e) => e.status_qualificacao === "BPF pendente").length,
        cursos: cursos.length,
        fluxos: protocolos.filter((p) => !["Finalizado", "Cancelado", "Reprovado"].includes(p.status)).length
      },
      protocolos: protocolos.slice(-20),
      entidadesPorNivel: entidades,
      cursosPorArea: cursos
    };
  },

  async entities() {
    const db = ensureSupabase();
    const { data, error } = await db.from("entidades").select("*").order("id", { ascending: false });
    throwDb(error);
    return { items: (data || []).filter(isActive) };
  },

  async createEntity(entidade: string, user: User) {
    const db = ensureSupabase();
    const { data, error } = await db.from("entidades").insert({
      entidade,
      status_qualificacao: CADASTRO_INICIAL,
      data_cadastro: nowStr(),
      cadastrado_por: user.usuario,
      cadastrado_por_email: user.email || "",
      ativo: true
    }).select("id").single();
    throwDb(error);
    return { id: data?.id, message: "Entidade cadastrada." };
  },

  async qualificationOptions() {
    const db = ensureSupabase();
    const { data, error } = await db
      .from("entidades")
      .select("*")
      .order("entidade");
    throwDb(error);
    return { items: (data || []).filter((row) => isActive(row) && ![FORM_GERAL_PENDENTE, "BPF pendente"].includes(row.status_qualificacao || "")) };
  },

  async pendingQualification(kind: "geral" | "bpf") {
    const db = ensureSupabase();
    const status = kind === "geral" ? FORM_GERAL_PENDENTE : "BPF pendente";
    const { data, error } = await db.from("entidades").select("*").eq("status_qualificacao", status).order("id", { ascending: false });
    throwDb(error);
    return { items: (data || []).filter(isActive) };
  },

  async questions(kind: "geral" | "bpf") {
    const db = ensureSupabase();
    const table = kind === "geral" ? "perguntas_qualificacao" : "perguntas_bpf";
    const query =
      kind === "geral"
        ? db.from(table).select("*").order("questionario").order("ordem")
        : db.from(table).select("*").order("secao").order("subsecao").order("ordem");
    const { data, error } = await query;
    throwDb(error);
    return { items: (data || []).filter(isActive) };
  },

  async saveCadastro(id: number, fields: Row) {
    const db = ensureSupabase();
    const { error } = await db.from("entidades").update({ ...fields, status_qualificacao: FORM_GERAL_PENDENTE }).eq("id", id);
    throwDb(error);
    return { message: "Dados cadastrais salvos." };
  },

  async saveGeneral(entidade_id: number, respostas: Row[]) {
    const db = ensureSupabase();
    const pontos = respostas.reduce((sum, row) => sum + Number(row.pontuacao || 0), 0);
    const nivel = levelByPoints(pontos);
    const { error: deleteError } = await db.from("respostas_entidade").delete().eq("entidade_id", entidade_id);
    if (deleteError) throw new Error(`Erro ao limpar respostas do Formulario Geral: ${deleteError.message}`);
    const { error: insertError } = await db.from("respostas_entidade").insert(respostas.map((r) => ({ ...r, entidade_id, data_resposta: nowStr() })));
    if (insertError) throw new Error(`Erro ao salvar respostas do Formulario Geral: ${insertError.message}`);
    const { error } = await db.from("entidades").update({ status_qualificacao: "BPF pendente", nivel, pontuacao: pontos, pontuacao_q1: pontos }).eq("id", entidade_id);
    if (error) throw new Error(`Erro ao atualizar status da entidade apos o Formulario Geral: ${error.message}`);
    return { message: "Formulário Geral salvo.", nivel, pontuacao: pontos };
  },

  async saveBpf(entidade_id: number, respostas: Row[]) {
    const db = ensureSupabase();
    const pontos = respostas.reduce((sum, row) => sum + Number(row.pontuacao || 0), 0);
    const { error: deleteError } = await db.from("respostas_bpf").delete().eq("entidade_id", entidade_id);
    if (deleteError) throw new Error(`Erro ao limpar respostas do BPF: ${deleteError.message}`);
    const { error: insertError } = await db.from("respostas_bpf").insert(respostas.map((r) => ({ ...r, entidade_id, data_resposta: nowStr() })));
    if (insertError) throw new Error(`Erro ao salvar respostas do BPF: ${insertError.message}`);
    const { error } = await db.from("entidades").update({ status_qualificacao: "Concluída", pontuacao_q2: pontos }).eq("id", entidade_id);
    if (error) throw new Error(`Erro ao concluir a qualificação da entidade apos o BPF: ${error.message}`);
    return { message: "BPF salvo. Entidade liberada para cursos.", pontuacao: pontos };
  },

  async courses() {
    const db = ensureSupabase();
    const { data, error } = await db.from("cursos").select("*").order("area").order("nivel").order("curso");
    throwDb(error);
    return { items: (data || []).filter(isActive) };
  },

  async courseQuestions(courseId: number) {
    const db = ensureSupabase();
    const { data: rawQuestions, error } = await db.from("perguntas_curso").select("*").eq("curso_id", courseId).order("ordem");
    throwDb(error);
    const questions = (rawQuestions || []).filter(isActive);
    const ids = (questions || []).map((q) => q.id);
    const { data: rawAlternatives, error: alternativesError } = ids.length
      ? await db.from("alternativas_curso").select("*").in("pergunta_id", ids).order("pergunta_id").order("ordem")
      : { data: [], error: null };
    throwDb(alternativesError);
    const alternatives = (rawAlternatives || []).filter(isActive);
    return { items: (questions || []).map((q) => ({ ...q, alternativas: (alternatives || []).filter((a) => a.pergunta_id === q.id) })) };
  },

  async protocols() {
    const db = ensureSupabase();
    const { data, error } = await db.from("protocolos").select("*, entidades(entidade,nivel), cursos(curso)").order("id", { ascending: false });
    throwDb(error);
    return {
      items: (data || []).map((row: any) => ({ ...row, entidade: row.entidades?.entidade, nivel_entidade: row.entidades?.nivel, curso: row.cursos?.curso })),
      status: STATUS_FLUXO
    };
  },

  async createProtocol(payload: Row) {
    const db = ensureSupabase();
    const protocolo = `BA-${new Date().toISOString().replace(/\D/g, "").slice(0, 14)}`;
    const data_mov = nowStr();
    const respostas = payload.respostas || [];
    const { error } = await db.from("protocolos").insert({
      protocolo,
      entidade_id: payload.entidade_id,
      curso_id: payload.curso_id,
      area: payload.area,
      pontuacao_curso: payload.pontuacao_curso || 0,
      status: "Validação Administrativa",
      etapa_atual: "Administrativo",
      responsavel_atual: "Administrativo",
      solicitante_nome: payload.solicitante_nome || "",
      solicitante_email: payload.solicitante_email || "",
      data_abertura: data_mov,
      data_atualizacao: data_mov,
      observacao: payload.observacao || ""
    });
    throwDb(error);
    await db.from("historico_fluxo").insert({ protocolo, status_anterior: "", status_novo: "Validação Administrativa", usuario: payload.usuario || "admin", data_movimento: data_mov, observacao: payload.observacao || "" });
    if (respostas.length) await db.from("respostas_curso").insert(respostas.map((r: Row) => ({ ...r, protocolo, data_resposta: data_mov })));
    return { message: "Protocolo criado.", protocolo };
  },

  async advanceProtocol(protocolo: string, usuario: string, observacao = "", data_agendada = "") {
    const db = ensureSupabase();
    const { data: row, error: lookupError } = await db.from("protocolos").select("*").eq("protocolo", protocolo).single();
    throwDb(lookupError);
    const [status, etapa] = nextStep(row.status);
    const update: Row = { status, etapa_atual: etapa, responsavel_atual: etapa, data_atualizacao: nowStr() };
    if (row.status === "Agendamento") update.data_agendada = data_agendada;
    const { error } = await db.from("protocolos").update(update).eq("protocolo", protocolo);
    throwDb(error);
    await db.from("historico_fluxo").insert({ protocolo, status_anterior: row.status, status_novo: status, usuario, data_movimento: nowStr(), observacao });
    return { message: "Fluxo atualizado.", status };
  },

  async cancelProtocol(protocolo: string, usuario: string, observacao = "") {
    const db = ensureSupabase();
    const { data: row, error: lookupError } = await db.from("protocolos").select("*").eq("protocolo", protocolo).single();
    throwDb(lookupError);
    const { error } = await db.from("protocolos").update({ status: "Cancelado", etapa_atual: "Cancelado", responsavel_atual: "Cancelado", data_atualizacao: nowStr() }).eq("protocolo", protocolo);
    throwDb(error);
    await db.from("historico_fluxo").insert({ protocolo, status_anterior: row.status, status_novo: "Cancelado", usuario, data_movimento: nowStr(), observacao });
    return { message: "Protocolo cancelado.", status: "Cancelado" };
  },

  async forms(protocolo: string) {
    const db = ensureSupabase();
    const { data: prot, error } = await db.from("protocolos").select("*").eq("protocolo", protocolo).single();
    throwDb(error);
    const [geral, bpf, curso, historico] = await Promise.all([
      db.from("respostas_entidade").select("*").eq("entidade_id", prot.entidade_id).order("id"),
      db.from("respostas_bpf").select("*").eq("entidade_id", prot.entidade_id).order("id"),
      db.from("respostas_curso").select("*").eq("protocolo", protocolo).order("id"),
      db.from("historico_fluxo").select("*").eq("protocolo", protocolo).order("id")
    ]);
    throwDb(geral.error || bpf.error || curso.error || historico.error);
    return { geral: geral.data || [], bpf: bpf.data || [], curso: curso.data || [], historico: historico.data || [] };
  },

  async table(table: string) {
    const db = ensureSupabase();
    const { data, error } = await db.from(table).select("*").order("id", { ascending: false });
    throwDb(error);
    return { items: data || [] };
  },

  async saveTable(table: string, rows: Row[]) {
    const db = ensureSupabase();
    for (const row of rows) {
      const clean = { ...row };
      delete clean._deleted;
      if (clean.id) {
        const id = clean.id;
        delete clean.id;
        const { error } = await db.from(table).update(clean).eq("id", id);
        throwDb(error);
      } else if (Object.values(clean).some((value) => value !== "" && value != null)) {
        const { error } = await db.from(table).insert(clean);
        throwDb(error);
      }
    }
    return { message: "Tabela salva." };
  }
};

export const api = useSupabase ? supabaseApi : flaskApi;
