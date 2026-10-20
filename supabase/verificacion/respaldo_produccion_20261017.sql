-- =====================================================================
-- BeeHuman · Respaldo de producción previo a V2.0 (tomado 17-oct-2026)
-- Proyecto: vovyvvpwtjdlswerfjqb. Solo referencia y restauración.
-- =====================================================================

-- 1. Asignaciones de usuarios (usuarios_tenant, 2 filas) --------------
-- Estado exacto antes de V2.0. V2.0 no borra ni cambia estas filas: solo
-- agrega las columnas rol y personal_id. Si alguna se perdiera, esto la
-- restaura (idempotente):
insert into public.usuarios_tenant (user_id, tenant_id, created_at) values
  ('28b037db-6fde-4175-8408-a644c6aeee50', '99f1a014-0cd4-44c3-8d2f-cfa15dc5a1ed', '2026-09-28 22:26:44.933441+00'), -- erik.lamas@gmail.com · BeeHuman — Entorno inicial
  ('c42d6b9a-b543-4b52-a621-b19d26d5041b', '00000000-0000-4000-8000-de0000000001', '2026-10-04 04:59:15.441529+00')  -- demo@beehuman.invalid · BeeHuman — Demo
on conflict (user_id) do nothing;

-- 2. Esquema, políticas y permisos -------------------------------------
-- Respaldo = supabase/reversion/20261018000000_reversion_v2_0.sql
-- (texto literal de producción). Huella del esquema antes de V2.0:
--   total 03e98353d5e19d32ad52fd84b464f608
--   funciones 912ffc829bbbcfbbf4a2614fb35c9f53 · políticas 18095eff6a047432a2195498f22a2839
--   triggers b093e2b01f0e3c5684541697a7d698af · columnas 6280fa89bad5a9cc6ca34c6b209c837d
--   restricciones a267cab6d4c3aa807f6f67864340b459 · índices 3c48c9568a488945689eaf3253a461b8
--   tablas/permisos bfdd523090acfed6c38ed3e440578b77 · vistas db616d8a7664ce06bb1348e4dc6b31a6
-- Comprobar con supabase/verificacion/huella_esquema.sql.

-- 3. Datos (línea base, supabase/verificacion/huella_datos.sql) ---------
-- tabla                          filas  huella
-- areas                              5  162bb4e5ee53ee5ed882223908e8df2e
-- centros_costo                      4  54e6c0f1ef0091b0cf8bbb3c9247323c
-- clasificaciones_personal           6  8df686624fb200c21a18367fb5325350
-- combo_conceptos                    7  8c9d3a607cab65e9374b5990e9ea1735
-- combos                             2  58ae48284f404d6be9b1132d9d693546
-- conceptos_percepcion               7  a847c9c82bb74a06bcfa5e9f80559528
-- departamentos                      6  a1005227d0c4c70d6febf6d238db4184
-- empresas                           6  5dfe193a18c37d5e01a749425f6fb4f6
-- empresas_registros_patronales      7  067aac01bcf9f91a485899ffa9a22f97
-- localidades                        4  a69708261a8f7ba66182b32a5b227e5b
-- movimientos                       20  b97afb9a53b6064fccdf4a293696d942
-- periodicidades                     7  798cf54d6ccd9a04a3b4ab444c9bd8a2
-- personal                          54  21ea334c179cd4a10e8b1776dcc541b4
-- personal_percepciones              4  1052572b96bc87cce6234cbb0d27ed5d
-- personal_registros_pago           69  c3409511234ac2d5ba34c3b3124b5615
-- proyectos                          7  86ec08c7d870ff6254e3663208c44dea
-- puestos                           10  5c1cb4b077f5bf9021be6ede3b5123c8
-- tenants                            2  b052c558d92dc6f6426d0b27ec903fd7
-- usuarios_tenant                    2  a0814777124271de44bf2d6a35408491
-- Si alguien usa producción antes de migrar, la línea base cambia: se
-- vuelve a tomar justo antes de aplicar (paso 2 de la secuencia).
