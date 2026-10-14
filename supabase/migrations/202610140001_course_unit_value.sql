alter table public.cursos
  add column if not exists valor_unitario numeric
  check (valor_unitario >= 0 and valor_unitario < 'Infinity'::numeric
    and valor_unitario = round(valor_unitario, 2));

notify pgrst, 'reload schema';