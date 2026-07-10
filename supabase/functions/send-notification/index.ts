import { createClient } from "npm:@supabase/supabase-js@2";
import nodemailer from "npm:nodemailer@6.9.15";

type NotificationRow = {
  id: number;
  protocolo: string | null;
  destinatario: string | null;
  assunto: string | null;
  corpo: string | null;
  enviado: boolean | number | null;
  erro: string | null;
};

type WebhookPayload = {
  type?: "INSERT" | "UPDATE" | "DELETE";
  table?: string;
  schema?: string;
  record?: NotificationRow | null;
  old_record?: NotificationRow | null;
};

const supabaseUrl = Deno.env.get("SUPABASE_URL") ?? "";
const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";

const smtpHost = Deno.env.get("SMTP_HOST") ?? "";
const smtpUser = Deno.env.get("SMTP_USER") ?? "";
const smtpPassword = Deno.env.get("SMTP_PASSWORD") ?? "";
const smtpFrom = (Deno.env.get("SMTP_FROM") || smtpUser).trim();
const smtpPort = Number(Deno.env.get("SMTP_PORT") || "587");
const smtpTls = (Deno.env.get("SMTP_TLS") || "1") !== "0";
const smtpSsl = (Deno.env.get("SMTP_SSL") || "0") === "1";

const admin = createClient(supabaseUrl, serviceRoleKey, {
  auth: { persistSession: false, autoRefreshToken: false },
});

function json(body: Record<string, unknown>, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function isSent(value: NotificationRow["enviado"]) {
  return value === true || value === 1 || value === "1";
}

async function updateNotification(id: number, patch: Partial<NotificationRow>) {
  const { error } = await admin.from("notificacoes").update(patch).eq("id", id);
  if (error) {
    console.error("Erro ao atualizar notificacao", id, error.message);
  }
}

async function sendViaSmtp(row: NotificationRow) {
  if (!smtpHost || !smtpFrom) {
    throw new Error("SMTP nao configurado. Defina SMTP_HOST e SMTP_FROM/SMTP_USER.");
  }

  const transporter = nodemailer.createTransport({
    host: smtpHost,
    port: smtpPort,
    secure: smtpSsl,
    requireTLS: !smtpSsl && smtpTls,
    auth: smtpUser && smtpPassword ? { user: smtpUser, pass: smtpPassword } : undefined,
  });

  await transporter.sendMail({
    from: smtpFrom,
    to: String(row.destinatario || "").trim(),
    subject: String(row.assunto || "Notificacao do Sistema Bahia").trim(),
    text: String(row.corpo || "").trim(),
  });
}

Deno.serve(async (req) => {
  if (req.method !== "POST") {
    return json({ error: "Metodo nao permitido." }, 405);
  }

  if (!supabaseUrl || !serviceRoleKey) {
    return json({ error: "SUPABASE_URL ou SUPABASE_SERVICE_ROLE_KEY ausentes." }, 500);
  }

  const payload = (await req.json().catch(() => null)) as WebhookPayload | null;
  const row = payload?.record;

  if (!row || payload?.table !== "notificacoes") {
    return json({ message: "Webhook ignorado sem registro valido." });
  }

  if (isSent(row.enviado)) {
    return json({ message: "Notificacao ja enviada." });
  }

  if (!String(row.destinatario || "").trim()) {
    await updateNotification(row.id, {
      erro: "Destinatario vazio.",
    });
    return json({ message: "Destinatario vazio." }, 400);
  }

  try {
    await sendViaSmtp(row);
    await updateNotification(row.id, {
      enviado: 1,
      data_envio: new Date().toISOString(),
      erro: "",
    } as Partial<NotificationRow>);
    return json({ message: "Email enviado.", id: row.id });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    await updateNotification(row.id, {
      erro: `SMTP: ${message}`,
    });
    return json({ error: message, id: row.id }, 500);
  }
});
