# Governanca e Qualificacao de Demandas - Bahia

Aplicacao migrada para uma arquitetura compativel com Vercel:

- Frontend: React + TypeScript + Vite
- API: Flask em funcao serverless dentro de `api/index.py`
- Banco: Supabase/Postgres em producao via `SUPABASE_DB_URL` ou `DATABASE_URL`
- Fallback local: SQLite `bahia.db`

O Streamlit original permanece em `app.py` como referencia e backup.

## Rodar localmente

```bash
pip install -r requirements.txt
npm install
npm run dev
```

Para testar a API Flask localmente separada do Vite:

```bash
flask --app api.index run --port 5000
```

## Deploy Vercel

Variaveis de ambiente recomendadas:

```text
SUPABASE_DB_URL=postgresql://...
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.seuprovedor.com
SMTP_PORT=587
SMTP_USER=usuario@seudominio.com
SMTP_PASSWORD=sua-senha-ou-app-password
SMTP_FROM=Sistema Bahia <usuario@seudominio.com>
SMTP_TLS=1
SMTP_SSL=0
SMTP_TIMEOUT=20
```

Observacoes sobre SMTP:

- `EMAIL_PROVIDER=smtp` deixa o Flask usar SMTP como caminho principal.
- Para porta `587`, o mais comum e `SMTP_TLS=1` com `SMTP_SSL=0`.
- Para porta `465`, normalmente use `SMTP_SSL=1` com `SMTP_TLS=0`.
- Se usar Gmail, prefira `App Password` em vez da senha normal da conta.
- Se quiser manter Resend como contingencia, tambem pode configurar `RESEND_API_KEY` e `MAIL_FROM`.

Comandos:

```bash
vercel deploy
vercel env add SUPABASE_DB_URL production
vercel env add EMAIL_PROVIDER production
vercel env add SMTP_HOST production
vercel env add SMTP_PORT production
vercel env add SMTP_USER production
vercel env add SMTP_PASSWORD production
vercel env add SMTP_FROM production
vercel env add SMTP_TLS production
vercel env add SMTP_SSL production
vercel env add SMTP_TIMEOUT production
```

## Login inicial local

- usuario: `admin`
- senha: `admin123`
