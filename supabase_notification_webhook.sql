-- Configure o webhook automatico para enviar emails sempre que uma linha nova
-- for inserida em public.notificacoes com enviado = 0.
--
-- Antes de rodar:
-- 1. Crie/deploy a Edge Function "send-notification".
-- 2. Desative a validacao JWT da funcao.
-- 3. Substitua YOUR_PROJECT_REF abaixo pelo Project Ref do Supabase.

drop trigger if exists notificacoes_email_webhook on public.notificacoes;

create trigger notificacoes_email_webhook
after insert on public.notificacoes
for each row
execute function supabase_functions.http_request(
  'https://YOUR_PROJECT_REF.supabase.co/functions/v1/send-notification',
  'POST',
  '{"Content-Type":"application/json"}',
  '{}',
  '5000'
);
