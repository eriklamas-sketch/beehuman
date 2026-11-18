"""Datos FICTICIOS de créditos para las pruebas de pantalla de «Prestaciones y créditos» (base local bhui).
Crea los créditos con las funciones reales (cred_guardar, cred_cambiar_estado); solo las líneas de descuento
y los periodos procesados se escriben directo, porque la pantalla únicamente los LEE.
  ADELA  1 crédito  · FONACOT convertido, completo, pendiente de activar.
  BENITO 3 créditos · INFONAVIT, FONACOT con propuesto y procesado, préstamo con saldo.
  CESAR  5 créditos · INFONAVIT %, FONACOT con dos periodos abiertos, préstamo suspendido,
                      FONACOT incompleto con faltantes, anticipo terminado.
  DIANA  16 créditos (con montar_diana=True) · 14 vivos en todas las categorías + 2 terminados."""
import json
import rest_local as RL

T = '0a000000-0000-4000-8000-000000000001'; E1 = '0c000000-0000-4000-8000-000000000001'
SEM = '0e000000-0000-4000-8000-000000000007'; MEN = '0e000000-0000-4000-8000-000000000030'
U = {'admin': '0b000000-0000-4000-8000-000000000001', 'nomina': '0b000000-0000-4000-8000-000000000002'}
RL.U.update(U)
P = {'ADELA': '0a100000-0000-4000-8000-000000000011', 'BENITO': '0a100000-0000-4000-8000-000000000012',
     'CESAR': '0a100000-0000-4000-8000-000000000013', 'DIANA': '0a100000-0000-4000-8000-000000000014'}
NOMBRE = {'ADELA': 'ADELA PALACIOS GALVAN', 'BENITO': 'BENITO ZAVALA GALINDO', 'CESAR': 'CESAR DELGADILLO HINOJOSA', 'DIANA': 'DIANA FUENTES ORTIZ'}

def sql(q, quien=None, replica=False):
    c = RL.conectar(); cur = c.cursor()
    try:
        if replica: cur.execute('set local session_replication_role = replica')
        if quien:
            cur.execute("select set_config('request.jwt.claims', %s, true)", (json.dumps({'sub': U[quien], 'role': 'authenticated'}),))
            cur.execute('set local role authenticated')
        cur.execute(q); r = cur.fetchone() if cur.description else None; c.commit(); return r[0] if r else None
    finally: c.close()
lit = lambda d: "'" + json.dumps(d).replace("'", "''") + "'::jsonb"
rel = {k: sql(f"select id from public.relaciones_laborales where personal_id = '{v}' and estado = 'vigente'") for k, v in P.items()}
FON = lambda ref, imp: {'tipo': 'fonacot', 'referencia': ref, 'periodicidad_id': SEM, 'importe_periodo': imp}

def credito(quien_p, d):
    d = dict(d, personal_id=P[quien_p], relacion_laboral_id=rel[quien_p], fecha_inicio=d.get('fecha_inicio', '2026-11-01'))
    return sql(f"select public.cred_guardar(null, {lit(d)})", 'nomina')
def estado(cid, e, motivo, fecha='2026-11-12'): sql(f"select public.cred_cambiar_estado('{cid}', '{e}', '{fecha}', '{motivo}')", 'nomina')
def incompleto(cid, sin_importe=False):
    sql(f"update public.cred_creditos set estado = 'incompleto', origen = 'conversion_no_fonacot'{', importe_periodo = null' if sin_importe else ''} where id = '{cid}'", replica=True)
def linea(cred, per, quien_p, sug, fin, origen):
    return sql(f"""insert into public.cred_descuentos (tenant_id, periodo_id, credito_id, personal_id, relacion_laboral_id, sugerido, final, origen)
                   values ('{T}', '{per}', '{cred}', '{P[quien_p]}', '{rel[quien_p]}', {sug}, {fin if fin is not None else 'null'}, '{origen}') returning id""")

def montar(montar_diana=False):
    S = {}
    sql(f"update public.inc_parametros set responsable_nomina_user = '{U['nomina']}' where empresa_id = '{E1}'", replica=True)
    S['PER_PROC'] = sql(f"select public.inc_crear_periodo('{E1}','{SEM}','2026-11-02','2026-11-08')", 'nomina')
    S['PER_AB1'] = sql(f"select public.inc_crear_periodo('{E1}','{SEM}','2026-11-09','2026-11-15')", 'nomina')
    S['PER_AB2'] = sql(f"select public.inc_crear_periodo('{E1}','{SEM}','2026-11-16','2026-11-22')", 'nomina')
    PP, A1, A2 = S['PER_PROC'], S['PER_AB1'], S['PER_AB2']
    # ADELA
    S['A1'] = credito('ADELA', FON('FON-UNO-01', 250)); incompleto(S['A1'])
    # BENITO
    S['B_INF'] = credito('BENITO', {'tipo': 'infonavit', 'referencia': 'INF-9921', 'infonavit_tipo': 'cuota_fija', 'infonavit_valor': 1200, 'infonavit_fecha_aviso': '2026-10-15'})
    S['B_FON'] = credito('BENITO', FON('FON-B-02', 250))
    S['B_PRE'] = credito('BENITO', {'tipo': 'prestamo', 'referencia': 'PRE-04', 'periodicidad_id': SEM, 'importe_periodo': 500, 'monto_total': 10000})
    # CESAR
    S['C_INF'] = credito('CESAR', {'tipo': 'infonavit', 'referencia': 'INF-5550', 'infonavit_tipo': 'porcentaje', 'infonavit_valor': 20})
    S['C_FON'] = credito('CESAR', FON('FON-C-01', 300))
    S['C_SUS'] = credito('CESAR', {'tipo': 'prestamo', 'referencia': 'PRE-SUS', 'periodicidad_id': SEM, 'importe_periodo': 400, 'monto_total': 4000})
    S['C_INC'] = credito('CESAR', FON('FON-C-INC', 180))
    S['C_TER'] = credito('CESAR', {'tipo': 'anticipo', 'referencia': 'ANT-OLD', 'periodicidad_id': SEM, 'importe_periodo': 1000, 'monto_total': 1000})
    estado(S['C_SUS'], 'suspendido', 'Acuerdo con el trabajador'); estado(S['C_TER'], 'terminado', 'Liquidado en efectivo', '2026-11-05')
    incompleto(S['C_INC'], sin_importe=True)
    linea(S['B_FON'], PP, 'BENITO', 250, 250, 'aceptado'); linea(S['B_FON'], A1, 'BENITO', 250, None, 'pendiente')
    lp = linea(S['B_PRE'], PP, 'BENITO', 500, 500, 'aceptado'); linea(S['B_PRE'], A1, 'BENITO', 500, 450, 'modificado')
    sql(f"""insert into public.cred_movimientos (tenant_id, credito_id, periodo_id, descuento_id, importe, saldo_anterior, saldo_nuevo)
            values ('{T}', '{S['B_PRE']}', '{PP}', '{lp}', 500, 10000, 9500) returning id""")
    linea(S['C_FON'], A1, 'CESAR', 300, None, 'pendiente'); linea(S['C_FON'], A2, 'CESAR', 300, 300, 'aceptado')
    linea(S['C_FON'], PP, 'CESAR', 300, None, 'descartado')
    if montar_diana:
        D = S['D'] = {}
        for ref, imp, tot in [('PRE-10', 500, 8000), ('PRE-11', 300, 3000), ('PRE-12', 250, 2500), ('PRE-13', 400, 4000), ('PRE-14', 350, 3500), ('PRE-15', 200, 2000)]:
            D[ref] = credito('DIANA', {'tipo': 'prestamo', 'referencia': ref, 'periodicidad_id': SEM, 'importe_periodo': imp, 'monto_total': tot})
        D['ANT-20'] = credito('DIANA', {'tipo': 'anticipo', 'referencia': 'ANT-20', 'periodicidad_id': SEM, 'importe_periodo': 600, 'monto_total': 1800})
        for ref, imp in [('FON-30', 280), ('FON-31', 150), ('FON-32', 200)]: D[ref] = credito('DIANA', FON(ref, imp))
        D['INF-40'] = credito('DIANA', {'tipo': 'infonavit', 'referencia': 'INF-40', 'infonavit_tipo': 'cuota_fija', 'infonavit_valor': 1650})
        D['PEN-50'] = credito('DIANA', {'tipo': 'pension', 'referencia': 'EXP-50', 'pension_forma': 'porcentaje', 'pension_valor': 25, 'pension_beneficiario': 'BENEFICIARIA SINTETICA'})
        D['OTR-60'] = credito('DIANA', {'tipo': 'otro', 'concepto': 'Caja de ahorro', 'referencia': 'CA-60', 'periodicidad_id': SEM, 'importe_periodo': 200})
        D['OTR-61'] = credito('DIANA', {'tipo': 'otro', 'concepto': 'Fondo de ahorro', 'referencia': 'FA-61', 'periodicidad_id': MEN, 'importe_periodo': 900})
        D['PRE-T1'] = credito('DIANA', {'tipo': 'prestamo', 'referencia': 'PRE-T1', 'periodicidad_id': SEM, 'importe_periodo': 500, 'monto_total': 1000})
        D['FON-T2'] = credito('DIANA', FON('FON-T2', 120))
        for k in ('PRE-T1', 'FON-T2'): estado(D[k], 'terminado', 'Liquidado', '2026-11-05')
        estado(D['PRE-13'], 'suspendido', 'Incapacidad')
        incompleto(D['FON-31']); incompleto(D['FON-32'], sin_importe=True)
        for ref, per, sug, fin, o in [('PRE-10', A1, 500, None, 'pendiente'), ('PRE-11', A1, 300, 300, 'aceptado'), ('PRE-12', A2, 250, None, 'pendiente'),
                                      ('PRE-14', A1, 350, None, 'pendiente'), ('ANT-20', A1, 600, None, 'pendiente'), ('FON-30', A1, 280, None, 'pendiente'),
                                      ('OTR-60', A1, 200, None, 'pendiente'),
                                      # Dato forzado para probar la regla: crédito MENSUAL con línea en un periodo semanal.
                                      ('OTR-61', A1, 900, None, 'pendiente')]:
            linea(D[ref], per, 'DIANA', sug, fin, o)
    # El periodo se marca procesado después de registrar sus líneas (como ocurre al procesar).
    sql(f"update public.inc_periodos set procesado_en = '2026-11-10 12:00-06', procesado_por = '{U['nomina']}' where id = '{PP}'", replica=True)
    return S
