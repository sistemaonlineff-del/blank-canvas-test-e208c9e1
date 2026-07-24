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

export const USER_ROLE_OPTIONS = [
  "Administrador",
  "Moderador",
  "Analista Administrativo",
  "Analista Tecnico",
  "Agendamento",
  "Execucao"
] as const;

export const CADASTRO_OPTIONS = {
  anAtepAteg: ["AN", "ATEP/ATEG"],
  coordenadorTipo: ["Coordenador de Negocio", "Coordenacao de Mercado"],
  naturezaJuridica: ["Associacao", "Cooperativa", "Cooperativa Central"],
  certificacoesEntidade: ["ADAB", "SIM", "SIM CONSORCIO", "SUSAF", "MAPA", "ANVISA", "DIVISA", "VIGILANCIA MUNICIPAL"],
  licencasAmbientais: ["Sim", "Nao", "Nao se aplica"],
  ativaDinamica: ["Ativa", "Dinamica"],
  tipologiaBeneficiarios: [
    "Agricultores Familiares",
    "Comunidades Tradicionais",
    "Assentados da Reforma Agraria",
    "Extrativistas"
  ],
  comunidadesTradicionais: ["Quilombolas", "Indigenas", "Fundos e Fechos de Pastos", "Povos de Terreiro", "Outro"]
} as const;

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || import.meta.env.SUPABASE_URL;
const supabaseAnonKey =
  import.meta.env.VITE_SUPABASE_ANON_KEY ||
  import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY ||
  import.meta.env.SUPABASE_ANON_KEY ||
  import.meta.env.SUPABASE_PUBLISHABLE_KEY;
const apiBaseUrl = String(import.meta.env.VITE_API_BASE_URL || "")
  .trim()
  .replace(/\/+$/, "");
const useSupabase = Boolean(supabaseUrl && supabaseAnonKey);
const supabase = useSupabase ? createClient(supabaseUrl, supabaseAnonKey) : null;

const STATUS_VALIDACAO = "Validacao Administrativa";
const STATUS_ANALISE = "Analise Tecnica";
const STATUS_AGENDAMENTO = "Agendamento";
const STATUS_EXECUCAO = "Execucao";
const STATUS_FINALIZADO = "Finalizado";
const STATUS_CANCELADO = "Cancelado";
const STATUS_REPROVADO = "Reprovado";
const STATUS_LISTA_ESPERA = "Lista de Espera";

const STATUS_FLUXO = [
  STATUS_VALIDACAO,
  STATUS_ANALISE,
  STATUS_LISTA_ESPERA,
  STATUS_AGENDAMENTO,
  STATUS_EXECUCAO,
  STATUS_FINALIZADO,
  STATUS_CANCELADO,
  STATUS_REPROVADO
];

const FORM_GERAL_PENDENTE = "Formulario geral pendente";
const CADASTRO_INICIAL = "Cadastro inicial";
const ROLE_ADMIN = "Administrador";
const ROLE_MODERATOR = "Moderador";
const ROLE_ANALISTA_ADM = "Analista Administrativo";
const ROLE_ANALISTA_TECNICO = "Analista Tecnico";
const ROLE_AGENDAMENTO = "Agendamento";
const ROLE_EXECUCAO = "Execucao";

const FLOW_NOTIFICATION_ORDER = [ROLE_ANALISTA_ADM, ROLE_ANALISTA_TECNICO, ROLE_AGENDAMENTO, ROLE_EXECUCAO];

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

function normalizeStatusKey(value: unknown) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

function normalizeRoleKey(value: unknown) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

function nextStep(status: string) {
  const steps: Record<string, [string, string]> = {
    "validacao administrativa": [STATUS_ANALISE, ROLE_ANALISTA_TECNICO],
    "analise tecnica": [STATUS_AGENDAMENTO, ROLE_AGENDAMENTO],
    agendamento: [STATUS_EXECUCAO, ROLE_EXECUCAO],
    execucao: [STATUS_FINALIZADO, STATUS_FINALIZADO]
  };
  return steps[normalizeStatusKey(status)] || [status, ""];
}

function rolesForStatus(status: unknown) {
  const key = normalizeStatusKey(status);
  if (key === "validacao administrativa") return [ROLE_ADMIN, ROLE_MODERATOR, ROLE_ANALISTA_ADM];
  if (key === "analise tecnica") return [ROLE_ADMIN, ROLE_MODERATOR, ROLE_ANALISTA_TECNICO];
  if (key === "agendamento") return [ROLE_ADMIN, ROLE_MODERATOR, ROLE_AGENDAMENTO];
  if (key === "execucao") return [ROLE_ADMIN, ROLE_MODERATOR, ROLE_EXECUCAO];
  return [ROLE_ADMIN, ROLE_MODERATOR];
}

function flowRolesUpToStatus(status: unknown) {
  const key = normalizeStatusKey(status);
  const index =
    key === "validacao administrativa" ? 0 :
      key === "analise tecnica" ? 1 :
        key === "agendamento" ? 2 :
          key === "execucao" ? 3 : FLOW_NOTIFICATION_ORDER.length - 1;
  return [ROLE_ADMIN, ROLE_MODERATOR, ...FLOW_NOTIFICATION_ORDER.slice(0, index + 1)];
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

function unique<T>(items: T[]) {
  return Array.from(new Set(items));
}

function isActive(row: Row) {
  return row.ativo == null || dbTrue(row.ativo);
}

function safeText(value: unknown) {
  return String(value ?? "-").trim() || "-";
}

function escapeHtml(value: unknown) {
  return safeText(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

async function buildProtocolOsDocument(protocol: Row) {
  const rows: Array<[string, unknown, string, unknown]> = [
    ["Protocolo", protocol.protocolo, "Status", protocol.status],
    ["Entidade", protocol.entidade, "Curso", protocol.curso],
    ["Area", protocol.area, "Nivel da entidade", protocol.nivel_entidade],
    ["Solicitante", protocol.solicitante_nome, "E-mail", protocol.solicitante_email],
    ["Data de abertura", protocol.data_abertura, "Data agendada", protocol.data_agendada],
    ["Responsavel atual", protocol.responsavel_atual, "Etapa atual", protocol.etapa_atual]
  ];
  const entidadeRows: Array<[string, unknown, string, unknown]> = [
    ["Entidade", protocol.entidade, "CNPJ", protocol.cnpj],
    ["Municipio", protocol.municipio_entidade, "Territorio", protocol.territorio_identidade],
    ["Endereco", protocol.endereco, "Telefone", protocol.telefone],
    ["Email responsavel", protocol.email_responsavel, "Certificacao", protocol.certificacao]
  ];
  const renderTable = (tableRows: Array<[string, unknown, string, unknown]>) =>
    tableRows
      .map(
        ([labelA, valueA, labelB, valueB]) => `
          <tr>
            <td><strong>${escapeHtml(labelA)}:</strong> ${escapeHtml(valueA)}</td>
            <td><strong>${escapeHtml(labelB)}:</strong> ${escapeHtml(valueB)}</td>
          </tr>
        `
      )
      .join("");

  const html = `
    <html>
      <head>
        <meta charset="utf-8" />
        <title>OS ${escapeHtml(protocol.protocolo)}</title>
        <style>
          body { font-family: Arial, sans-serif; color: #111827; margin: 32px; }
          h1 { font-size: 24px; margin: 0 0 8px; }
          h2 { font-size: 16px; margin: 24px 0 12px; }
          p { margin: 0 0 12px; }
          table { width: 100%; border-collapse: collapse; margin-bottom: 16px; }
          td { border: 1px solid #cbd5e1; padding: 10px; vertical-align: top; width: 50%; }
        </style>
      </head>
      <body>
        <h1>ORDEM DE SERVICO</h1>
        <p><strong>Governanca e Qualificacao de Demandas - Bahia</strong></p>
        <table>${renderTable(rows)}</table>
        <h2>DADOS DA ENTIDADE</h2>
        <table>${renderTable(entidadeRows)}</table>
        <h2>OBSERVACOES</h2>
        <p>${escapeHtml(protocol.observacao)}</p>
      </body>
    </html>
  `;

  return new Blob(["\ufeff", html], { type: "application/msword" });
}

async function fetchActiveUsersByRoles(db: ReturnType<typeof ensureSupabase>, roles: string[]) {
  const allowedRoles = unique(roles).filter(Boolean);
  if (!allowedRoles.length) return [];
  const { data, error } = await db
    .from("usuarios")
    .select("*")
    .in("perfil", allowedRoles)
    .eq("ativo", true)
    .eq("acesso_pendente", false);
  throwDb(error);
  return (data || []).filter((row) => isActive(row) && !dbTrue(row.acesso_pendente));
}

async function queueNotifications(
  db: ReturnType<typeof ensureSupabase>,
  protocolo: string,
  recipients: string[],
  assunto: string,
  corpo: string
) {
  const destinatarios = unique(
    recipients
      .map((item) => String(item || "").trim().toLowerCase())
      .filter(Boolean)
  );
  if (!destinatarios.length) return;
  const payload = destinatarios.map((destinatario) => ({
    protocolo,
    destinatario,
    assunto,
    corpo,
    enviado: false,
    data_criacao: nowStr(),
    erro: "Fila registrada. Configure SMTP/Edge Function para envio automatico real."
  }));
  const { error } = await db.from("notificacoes").insert(payload);
  throwDb(error);
}

function buildApprovalNotification(row: Row, nextStatus: string, nextStage: string, observacao = "", cancelled = false) {
  const assunto = cancelled
    ? `Atencao: protocolo ${safeText(row.protocolo)} foi cancelado`
    : "Atencao: chegou uma nova demanda para sua area";
  const corpo = cancelled
    ? [
        "Atencao,",
        "",
        "O fluxo abaixo foi cancelado no Sistema Bahia.",
        "",
        `Numero do protocolo: ${safeText(row.protocolo)}`,
        `Entidade: ${safeText(row.entidade)}`,
        `CNPJ: ${safeText(row.cnpj)}`,
        `Area: ${safeText(row.area)}`,
        `Pessoa que iniciou o fluxo: ${safeText(row.solicitante_nome)}`,
        `E-mail do solicitante: ${safeText(row.solicitante_email)}`,
        `Observacao: ${safeText(observacao || "-")}`
      ].join("\n")
    : [
        "Atencao,",
        "",
        "Chegou uma nova demanda aguardando sua atuacao no Sistema Bahia.",
        "",
        `Numero do protocolo: ${safeText(row.protocolo)}`,
        `Entidade: ${safeText(row.entidade)}`,
        `CNPJ: ${safeText(row.cnpj)}`,
        `Curso: ${safeText(row.curso)}`,
        `Area responsavel: ${safeText(row.area)}`,
        `Etapa atual: ${safeText(nextStage)}`,
        `Status do fluxo: ${safeText(nextStatus)}`,
        `Pessoa que iniciou o fluxo: ${safeText(row.solicitante_nome)}`,
        `E-mail do solicitante: ${safeText(row.solicitante_email)}`,
        `Observacao: ${safeText(observacao || "-")}`
      ].join("\n");
  return { assunto, corpo };
}

async function fetchNotificationRecipients(db: ReturnType<typeof ensureSupabase>, row: Row, cancelled = false) {
  const area = String(row.area || "").trim();
  const recipients = new Set<string>();
  if (row.solicitante_email) recipients.add(String(row.solicitante_email).trim().toLowerCase());

  if (cancelled) {
    if (area) {
      const { data: owners, error: ownersError } = await db
        .from("owners_area")
        .select("email")
        .eq("area", area)
        .eq("ativo", true);
      throwDb(ownersError);
      (owners || []).forEach((owner: Row) => {
        const email = String(owner.email || "").trim().toLowerCase();
        if (email) recipients.add(email);
      });
    }
    return Array.from(recipients);
  }

  return Array.from(recipients);
}

async function fetchStageRecipients(
  db: ReturnType<typeof ensureSupabase>,
  row: Row,
  nextStatus: string,
  nextStage: string
) {
  const recipients = new Set<string>();
  if (row.solicitante_email) recipients.add(String(row.solicitante_email).trim().toLowerCase());

  const stageRoles = rolesForStatus(nextStatus).filter(
    (role) => ![ROLE_ADMIN, ROLE_MODERATOR].includes(role)
  );

  if (stageRoles.length) {
    const users = await fetchActiveUsersByRoles(db, stageRoles);
    users.forEach((user: Row) => {
      const email = String(user.email || user.usuario || "").trim().toLowerCase();
      if (email) recipients.add(email);
    });
  }

  if (!stageRoles.length && String(nextStage || "").trim()) {
    const fallbackRole = String(nextStage || "").trim().toLowerCase();
    const { data: users, error } = await db
      .from("usuarios")
      .select("email,usuario,perfil")
      .eq("ativo", true);
    throwDb(error);
    (users || [])
      .filter((user: Row) => normalizeRoleKey(user.perfil) === fallbackRole)
      .forEach((user: Row) => {
        const email = String(user.email || user.usuario || "").trim().toLowerCase();
        if (email) recipients.add(email);
      });
  }

  return Array.from(recipients);
}

function protocolSummary(row: Row) {
  return [
    `Protocolo: ${safeText(row.protocolo)}`,
    `Entidade: ${safeText(row.entidade)}`,
    `Curso: ${safeText(row.curso)}`,
    `Status: ${safeText(row.status)}`,
    `Responsavel atual: ${safeText(row.responsavel_atual || row.etapa_atual)}`,
    `Solicitante: ${safeText(row.solicitante_nome)} <${safeText(row.solicitante_email)}>`
  ].join("\n");
}

async function notifyRoleGroup(
  db: ReturnType<typeof ensureSupabase>,
  protocolo: string,
  roles: string[],
  assunto: string,
  corpo: string,
  extraRecipients: string[] = []
) {
  const users = await fetchActiveUsersByRoles(db, roles);
  await queueNotifications(
    db,
    protocolo,
    [...users.map((user) => user.email || user.usuario), ...extraRecipients],
    assunto,
    corpo
  );
}

function normalizeTableRow(table: string, row: Row) {
  if (table !== "usuarios") return row;
  const normalized: Row = {
    ...row,
    perfil: row.perfil || null,
    ativo: dbTrue(row.ativo),
    acesso_pendente: dbTrue(row.acesso_pendente),
    senha_temporaria: dbTrue(row.senha_temporaria),
    trocar_senha_obrigatorio: dbTrue(row.trocar_senha_obrigatorio)
  };
  delete normalized.generated_temp_password;
  return normalized;
}

function hasMeaningfulRowData(table: string, row: Row) {
  if (table === "usuarios") {
    return Boolean(String(row.email || row.usuario || row.nome || "").trim());
  }
  return Object.values(row).some((value) => value !== "" && value != null);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = /^https?:\/\//i.test(path) ? path : `${apiBaseUrl}${path}`;
  const res = await fetch(url, {
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

async function adjustCourseStock(db: ReturnType<typeof ensureSupabase>, courseId: number, delta: number) {
  const { data: course, error } = await db.from("cursos").select("id,estoque_total").eq("id", courseId).single();
  throwDb(error);
  const currentStock = Number(course?.estoque_total ?? 0);
  const nextStock = currentStock + delta;
  if (nextStock < 0) {
    throw new Error("Este curso nao possui vagas disponiveis no estoque.");
  }
  const { error: updateError } = await db.from("cursos").update({ estoque_total: nextStock }).eq("id", courseId);
  throwDb(updateError);
  return nextStock;
}

const flaskApi = {
  login: (usuario: string, senha: string) =>
    request<{ user: User }>("/api/login", { method: "POST", body: JSON.stringify({ usuario, senha }) }),
  register: (email: string) =>
    request<{ message: string; tempPassword?: string }>("/api/register", { method: "POST", body: JSON.stringify({ email }) }),
  changePassword: (userId: number, senha: string) =>
    request<{ user: User; message: string }>("/api/change-password", { method: "POST", body: JSON.stringify({ user_id: userId, senha }) }),
  dashboard: () => request<any>("/api/dashboard"),
  entities: () => request<{ items: Row[] }>("/api/entities"),
  createEntity: (entidade: string, cnpj: string, user: User) =>
    request<{ id: number; message: string }>("/api/entities", { method: "POST", body: JSON.stringify({ entidade, cnpj, usuario: user.usuario, email: user.email || "" }) }),
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
  rejectProtocol: (protocolo: string, usuario: string, observacao = "") =>
    request<any>(`/api/protocols/${protocolo}/cancel`, { method: "POST", body: JSON.stringify({ usuario, observacao: `[REPROVADO] ${observacao}`.trim() }) }),
  waitlistProtocol: (protocolo: string, usuario: string, observacao = "") =>
    request<any>(`/api/protocols/${protocolo}/cancel`, { method: "POST", body: JSON.stringify({ usuario, observacao: `[LISTA DE ESPERA] ${observacao}`.trim() }) }),
  forms: (protocolo: string) => request<any>(`/api/forms/${protocolo}`),
  downloadOs: async (protocolo: string) => {
    const url = `${apiBaseUrl}/api/protocols/${protocolo}/os`;
    window.open(url, "_blank");
  },
  processNotifications: (limit = 50) =>
    request<{ message: string; total: number; sent: number; failed: number; items: Row[] }>(
      "/api/notificacoes/processar",
      { method: "POST", body: JSON.stringify({ limit }) }
    ),
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
    const login = String(email || "").trim().toLowerCase();
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(login)) {
      throw new Error("Informe um e-mail válido.");
    }
    const temp = tempPassword();
    const senha_hash = await sha256(temp);
    const dataSolicitacao = nowStr();
    const { data: existing, error: existingError } = await db
      .from("usuarios")
      .select("*")
      .or(`usuario.eq.${login},email.eq.${login}`)
      .limit(1)
      .maybeSingle();
    throwDb(existingError);

    if (existing && dbFalse(existing.ativo)) {
      throw new Error("Este usuário está inativo. Procure um administrador.");
    }

    if (existing) {
      const { error } = await db
        .from("usuarios")
        .update({
          nome: login,
          usuario: login,
          email: login,
          senha_hash,
          perfil: null,
          senha_temporaria: true,
          trocar_senha_obrigatorio: true,
          acesso_pendente: true,
          data_solicitacao: dataSolicitacao,
          ativo: true
        })
        .eq("id", existing.id);
      throwDb(error);
    } else {
      const { error } = await db.from("usuarios").insert({
        nome: login,
        usuario: login,
        email: login,
        senha_hash,
        perfil: null,
        senha_temporaria: true,
        trocar_senha_obrigatorio: true,
        acesso_pendente: true,
        data_solicitacao: dataSolicitacao,
        ativo: true
      });
      throwDb(error);
    }

    const adminRecipients = await fetchActiveUsersByRoles(db, [ROLE_ADMIN, ROLE_MODERATOR]);
    await queueNotifications(
      db,
      `ACESSO-${login}`,
      adminRecipients.map((user) => String(user.email || user.usuario || "").trim().toLowerCase()),
      "Novo usuário aguardando qualificação - Sistema Bahia",
      `Um novo usuário criou acesso e aguarda qualificação de atividade.\n\nE-mail: ${login}\nData: ${dataSolicitacao}`
    );

    await queueNotifications(
      db,
      `ACESSO-${login}`,
      [login],
      "Senha temporária - Sistema Bahia",
      `Olá.\n\nCriamos um acesso temporário para o Sistema Bahia.\n\nE-mail: ${login}\nSenha temporária: ${temp}\n\nAo entrar, defina uma nova senha.`
    );

    return {
      message: "Usuário criado. Se o envio automático não estiver configurado, use a senha temporária exibida abaixo.",
      tempPassword: temp
    };
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
    const [entidadesRes, cursosRes, protocolosRes, usuariosRes] = await Promise.all([
      db.from("entidades").select("*"),
      db.from("cursos").select("*"),
      db.from("protocolos").select("*"),
      db.from("usuarios").select("*")
    ]);
    throwDb(entidadesRes.error || cursosRes.error || protocolosRes.error || usuariosRes.error);
    const entidades = (entidadesRes.data || []).filter(isActive);
    const cursos = (cursosRes.data || []).filter(isActive);
    const protocolos = protocolosRes.data || [];
    const usuarios = (usuariosRes.data || []).filter(isActive);
    return {
      cards: {
        entidades: entidades.length,
        qualificadas: entidades.filter((e) => e.status_qualificacao === "Concluída" || e.status_qualificacao === "Concluida").length,
        formGeralPendentes: entidades.filter((e) => e.status_qualificacao === FORM_GERAL_PENDENTE).length,
        bpfPendentes: entidades.filter((e) => e.status_qualificacao === "BPF pendente").length,
        cursos: cursos.length,
        fluxos: protocolos.filter((p) => ![STATUS_FINALIZADO, STATUS_CANCELADO, STATUS_REPROVADO].includes(p.status)).length,
        usuariosPendentes: usuarios.filter((u) => dbTrue(u.acesso_pendente) || !u.perfil).length
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

  async createEntity(entidade: string, cnpj: string, user: User) {
    const db = ensureSupabase();
    const { data, error } = await db.from("entidades").insert({
      entidade,
      cnpj,
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
    const { error: insertError } = await db.from("respostas_bpf").insert(
      respostas.map((r) => ({
        entidade_id,
        pergunta_id: r.pergunta_id,
        pergunta: r.pergunta,
        resposta: r.resposta,
        pontuacao: r.pontuacao,
        data_resposta: nowStr()
      }))
    );
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
    const protocolo = `BA-${new Date().toISOString().replace(/\D/g, "").slice(0, 17)}`;
    const dataMov = nowStr();
    const respostas = Array.isArray(payload.respostas) ? payload.respostas : [];
    const pontuacaoCurso = Number(
      payload.pontuacao_curso ??
      respostas.reduce((total: number, row: Row) => total + Number(row.pontuacao || 0), 0)
    );
    const statusInicial = STATUS_VALIDACAO;
    const etapaInicial = "Administrativo";
    let stockReserved = false;

    const insertPayload = {
      protocolo,
      entidade_id: payload.entidade_id,
      curso_id: payload.curso_id,
      area: payload.area || "",
      pontuacao_curso: pontuacaoCurso,
      status: statusInicial,
      etapa_atual: etapaInicial,
      responsavel_atual: etapaInicial,
      solicitante_nome: payload.solicitante_nome || "",
      solicitante_email: payload.solicitante_email || "",
      data_abertura: dataMov,
      data_atualizacao: dataMov,
      observacao: payload.observacao || ""
    };

    try {
      if (payload.curso_id) {
        await adjustCourseStock(db, Number(payload.curso_id), -1);
        stockReserved = true;
      }

      const { error: protocolError } = await db.from("protocolos").insert(insertPayload);
      throwDb(protocolError);

      const { error: historyError } = await db.from("historico_fluxo").insert({
        protocolo,
        status_anterior: "",
        status_novo: statusInicial,
        usuario: payload.usuario || "admin",
        data_movimento: dataMov,
        observacao: payload.observacao || ""
      });
      throwDb(historyError);

      if (respostas.length) {
        const { error: answersError } = await db.from("respostas_curso").insert(
          respostas.map((row: Row) => ({
            protocolo,
            pergunta_id: row.pergunta_id,
            pergunta: row.pergunta,
            resposta: row.resposta,
            pontuacao: row.pontuacao || 0,
            data_resposta: dataMov
          }))
        );
        throwDb(answersError);
      }

      const rowForNotification: Row = {
        ...insertPayload,
        entidade: payload.entidade || "",
        curso: payload.curso || "",
        cnpj: payload.cnpj || ""
      };
      const recipients = await fetchStageRecipients(db, rowForNotification, statusInicial, etapaInicial);
      const { assunto, corpo } = buildApprovalNotification(
        rowForNotification,
        statusInicial,
        etapaInicial,
        String(payload.observacao || ""),
        false
      );
      await queueNotifications(db, protocolo, recipients, assunto, corpo);

      return { message: "Protocolo criado.", protocolo };
    } catch (error) {
      if (stockReserved && payload.curso_id) {
        try {
          await adjustCourseStock(db, Number(payload.curso_id), 1);
        } catch {
          // Keep the original error when stock rollback also fails.
        }
      }
      throw error;
    }
  },

  async advanceProtocol(protocolo: string, usuario: string, observacao = "", data_agendada = "") {
    const db = ensureSupabase();
    const { data: protocol, error } = await db
      .from("protocolos")
      .select("*, entidades(entidade,cnpj,nivel), cursos(curso)")
      .eq("protocolo", protocolo)
      .single();
    throwDb(error);
    const row = {
      ...protocol,
      entidade: (protocol as any).entidades?.entidade,
      cnpj: (protocol as any).entidades?.cnpj,
      nivel_entidade: (protocol as any).entidades?.nivel,
      curso: (protocol as any).cursos?.curso
    } as Row;
    const [novoStatus, novaEtapa] = nextStep(String(row.status || ""));
    const dataMov = nowStr();
    const updatePayload: Row = {
      status: novoStatus,
      etapa_atual: novaEtapa,
      responsavel_atual: novaEtapa,
      data_atualizacao: dataMov
    };
    if (normalizeStatusKey(row.status) === "agendamento") {
      updatePayload.data_agendada = data_agendada || row.data_agendada || "";
    }
    const { error: updateError } = await db.from("protocolos").update(updatePayload).eq("protocolo", protocolo);
    throwDb(updateError);
    const { error: historyError } = await db.from("historico_fluxo").insert({
      protocolo,
      status_anterior: row.status,
      status_novo: novoStatus,
      usuario,
      data_movimento: dataMov,
      observacao
    });
    throwDb(historyError);
    const recipients = await fetchStageRecipients(db, row, novoStatus, novaEtapa);
    const { assunto, corpo } = buildApprovalNotification(row, novoStatus, novaEtapa, observacao, false);
    await queueNotifications(db, protocolo, recipients, assunto, corpo);
    return { message: "Fluxo atualizado.", status: novoStatus };
  },

  async cancelProtocol(protocolo: string, usuario: string, observacao = "") {
    const db = ensureSupabase();
    const { data: protocol, error } = await db
      .from("protocolos")
      .select("*, entidades(entidade,cnpj,nivel), cursos(curso)")
      .eq("protocolo", protocolo)
      .single();
    throwDb(error);
    const row = {
      ...protocol,
      entidade: (protocol as any).entidades?.entidade,
      cnpj: (protocol as any).entidades?.cnpj,
      nivel_entidade: (protocol as any).entidades?.nivel,
      curso: (protocol as any).cursos?.curso
    } as Row;
    const statusKey = normalizeStatusKey(row.status);
    if ([normalizeStatusKey(STATUS_CANCELADO), normalizeStatusKey(STATUS_REPROVADO), normalizeStatusKey(STATUS_FINALIZADO)].includes(statusKey)) {
      throw new Error("Este protocolo ja esta encerrado.");
    }
    const dataMov = nowStr();
    if (row.curso_id) {
      await adjustCourseStock(db, Number(row.curso_id), 1);
    }
    const { error: updateError } = await db
      .from("protocolos")
      .update({
        status: STATUS_CANCELADO,
        etapa_atual: STATUS_CANCELADO,
        responsavel_atual: STATUS_CANCELADO,
        data_atualizacao: dataMov
      })
      .eq("protocolo", protocolo);
    throwDb(updateError);
    const { error: historyError } = await db.from("historico_fluxo").insert({
      protocolo,
      status_anterior: row.status,
      status_novo: STATUS_CANCELADO,
      usuario,
      data_movimento: dataMov,
      observacao
    });
    throwDb(historyError);
    const recipients = await fetchNotificationRecipients(db, row, true);
    const { assunto, corpo } = buildApprovalNotification(row, STATUS_CANCELADO, STATUS_CANCELADO, observacao, true);
    await queueNotifications(db, protocolo, recipients, assunto, corpo);
    return { message: "Protocolo cancelado.", status: STATUS_CANCELADO };
  },

  async rejectProtocol(protocolo: string, usuario: string, observacao = "") {
    const db = ensureSupabase();
    const { data: protocol, error } = await db
      .from("protocolos")
      .select("*, entidades(entidade,cnpj,nivel), cursos(curso)")
      .eq("protocolo", protocolo)
      .single();
    throwDb(error);
    const row = {
      ...protocol,
      entidade: (protocol as any).entidades?.entidade,
      cnpj: (protocol as any).entidades?.cnpj,
      nivel_entidade: (protocol as any).entidades?.nivel,
      curso: (protocol as any).cursos?.curso
    } as Row;
    const dataMov = nowStr();
    const { error: updateError } = await db
      .from("protocolos")
      .update({
        status: STATUS_REPROVADO,
        etapa_atual: STATUS_REPROVADO,
        responsavel_atual: STATUS_REPROVADO,
        data_atualizacao: dataMov
      })
      .eq("protocolo", protocolo);
    throwDb(updateError);
    const { error: historyError } = await db.from("historico_fluxo").insert({
      protocolo,
      status_anterior: row.status,
      status_novo: STATUS_REPROVADO,
      usuario,
      data_movimento: dataMov,
      observacao
    });
    throwDb(historyError);
    const recipients = await fetchNotificationRecipients(db, row, true);
    const { assunto, corpo } = buildApprovalNotification(row, STATUS_REPROVADO, STATUS_REPROVADO, observacao, true);
    await queueNotifications(db, protocolo, recipients, assunto, corpo);
    return { message: "Protocolo reprovado.", status: STATUS_REPROVADO };
  },

  async waitlistProtocol(protocolo: string, usuario: string, observacao = "") {
    const db = ensureSupabase();
    const { data: protocol, error } = await db
      .from("protocolos")
      .select("*, entidades(entidade,cnpj,nivel), cursos(curso)")
      .eq("protocolo", protocolo)
      .single();
    throwDb(error);
    const row = {
      ...protocol,
      entidade: (protocol as any).entidades?.entidade,
      cnpj: (protocol as any).entidades?.cnpj,
      nivel_entidade: (protocol as any).entidades?.nivel,
      curso: (protocol as any).cursos?.curso
    } as Row;
    const dataMov = nowStr();
    const { error: updateError } = await db
      .from("protocolos")
      .update({
        status: STATUS_LISTA_ESPERA,
        etapa_atual: STATUS_LISTA_ESPERA,
        responsavel_atual: STATUS_LISTA_ESPERA,
        data_atualizacao: dataMov,
        observacao
      })
      .eq("protocolo", protocolo);
    throwDb(updateError);
    const { error: historyError } = await db.from("historico_fluxo").insert({
      protocolo,
      status_anterior: row.status,
      status_novo: STATUS_LISTA_ESPERA,
      usuario,
      data_movimento: dataMov,
      observacao
    });
    throwDb(historyError);
    const recipients = await fetchNotificationRecipients(db, row, true);
    const { assunto, corpo } = buildApprovalNotification(row, STATUS_LISTA_ESPERA, STATUS_LISTA_ESPERA, observacao, true);
    await queueNotifications(db, protocolo, recipients, assunto, corpo);
    return { message: "Protocolo enviado para lista de espera.", status: STATUS_LISTA_ESPERA };
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

  async downloadOs(protocolo: string) {
    const db = ensureSupabase();
    const { data, error } = await db
      .from("protocolos")
      .select("*, entidades(*), cursos(curso)")
      .eq("protocolo", protocolo)
      .single();
    throwDb(error);
    const row = {
      ...data,
      entidade: (data as any).entidades?.entidade,
      cnpj: (data as any).entidades?.cnpj,
      nivel_entidade: (data as any).entidades?.nivel,
      municipio_entidade: (data as any).entidades?.municipio_entidade,
      territorio_identidade: (data as any).entidades?.territorio_identidade,
      endereco: (data as any).entidades?.endereco,
      telefone: (data as any).entidades?.telefone,
      email_responsavel: (data as any).entidades?.email_responsavel,
      curso: (data as any).cursos?.curso
    } as Row;
    const blob = await buildProtocolOsDocument(row);
    downloadBlob(blob, `${protocolo}.doc`);
  },

  async processNotifications(limit = 50) {
    const db = ensureSupabase();
    const { data, error } = await db
      .from("notificacoes")
      .select("*")
      .eq("enviado", false)
      .order("id", { ascending: true })
      .limit(limit);
    throwDb(error);
    const items = data || [];
    return {
      message: items.length
        ? "Fila localizada no Supabase. Para envio real automático, use a Edge Function/webhook já prevista no projeto."
        : "Não há notificações pendentes na fila.",
      total: items.length,
      sent: 0,
      failed: 0,
      items
    };
  },

  async table(table: string) {
    const db = ensureSupabase();
    const { data, error } = await db.from(table).select("*").order("id", { ascending: false });
    throwDb(error);
    return { items: data || [] };
  },

  async saveTable(table: string, rows: Row[]) {
    const db = ensureSupabase();
    const normalizedRows = rows.map((row) => normalizeTableRow(table, { ...row }));
    const { data: existingRows, error: existingError } = await db.from(table).select("*");
    throwDb(existingError);
    const incomingIds = new Set(normalizedRows.filter((row) => row.id).map((row) => row.id));
    const removedRows = (existingRows || []).filter((row: Row) => row.id && !incomingIds.has(row.id));
    const removedIds = removedRows.map((row: Row) => row.id);
    if (removedIds.length) {
      const supportsActiveFlag = removedRows.some((row: Row) => Object.prototype.hasOwnProperty.call(row, "ativo"));
      if (table === "usuarios" || !supportsActiveFlag) {
        const { error: deleteError } = await db.from(table).delete().in("id", removedIds);
        throwDb(deleteError);
      } else {
        const { error: deactivateError } = await db.from(table).update({ ativo: false }).in("id", removedIds);
        throwDb(deactivateError);
      }
    }
    for (const clean of normalizedRows) {
      delete clean._deleted;
      delete clean._tempKey;
      if (clean.id) {
        const id = clean.id;
        const previous =
          table === "usuarios"
            ? await db.from(table).select("*").eq("id", id).maybeSingle()
            : { data: null, error: null };
        throwDb(previous.error);
        delete clean.id;
        const { error } = await db.from(table).update(clean).eq("id", id);
        throwDb(error);
        if (
          table === "usuarios" &&
          previous.data &&
          (dbTrue(previous.data.acesso_pendente) || !previous.data.perfil) &&
          !dbTrue(clean.acesso_pendente) &&
          clean.perfil &&
          (clean.email || clean.usuario)
        ) {
          await queueNotifications(
            db,
            `ACESSO-${clean.email || clean.usuario}`,
            [clean.email || clean.usuario],
            "Acesso liberado - Sistema Bahia",
            `Seu acesso ao Sistema Bahia foi liberado.\n\nCargo: ${clean.perfil}\nUsuario: ${clean.email || clean.usuario}\n\nEntre com a senha definida para continuar.`
          );
        }
      } else if (hasMeaningfulRowData(table, clean)) {
        const { error } = await db.from(table).insert(clean);
        throwDb(error);
      }
    }
    return { message: "Tabela salva." };
  }
};

export const api = useSupabase ? supabaseApi : flaskApi;

