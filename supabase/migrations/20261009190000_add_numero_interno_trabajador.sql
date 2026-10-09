-- BeeHuman: optional tenant-scoped internal employee number for payroll-system synchronization.
-- Apply this migration in Supabase SQL Editor before using the new field in the app.
ALTER TABLE public.personal
  ADD COLUMN IF NOT EXISTS numero_interno_trabajador text;

COMMENT ON COLUMN public.personal.numero_interno_trabajador IS
  'Optional client-defined internal employee number, e.g. for NOI or CONTPAQi synchronization.';
