#!/usr/bin/env python3
"""Genera los CSV ficticios para probar la importación masiva ampliada (layout v2).
Salida: imp_v2_validos_450.csv (450 filas correctas) e imp_v2_errores.csv
(1 fila por tipo de error esperado + 10 válidas de control). Datos 100 % ficticios.
Uso: python3 -I generar_csv_prueba.py <carpeta_salida>"""
import csv, random, sys, os, string
random.seed(20261126)
OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
COLS = ['Nombres','Primer apellido','Segundo apellido','Empresa','Proyecto','RFC','CURP','NSS','CP fiscal',
  'Registro patronal','Puesto','Área','Departamento','Localidad','Centro de costo','Coordinador','Coordinador externo',
  'Tipo de empleado','Turno','Fecha de inicio de contrato','Fecha de vencimiento de contrato',
  'Fecha de ingreso','Fecha de antigüedad','Número interno','SDI','Tipo de trabajador','Tipo de salario','Jornada IMSS','UMF',
  'Forma de pago 1','Periodicidad 1','Modalidad 1','Importe 1','Forma de pago 2','Periodicidad 2','Modalidad 2','Importe 2']
NOM = ['ANA','LUIS','MARTA','JOSE','ROSA','CARLOS','ELENA','PEDRO','LAURA','JUAN','SOFIA','DIEGO','IRMA','RAUL','NORA','OSCAR']
APE = ['PRUEBA','FICTICIO','DEMO','EJEMPLO','MUESTRA','ENSAYO','SINTETICO','MODELO','PATRON','PILOTO']
EMP = [('IMPORTA NORTE DEMO','A0000000001'),('IMPORTA SUR DEMO','B0000000002'),('IMPORTA CENTRO DEMO',None)]
EST = 'DF'
def curp(i, n, a1, a2):
    yy, mm, dd = 80 + i % 20, 1 + i % 12, 1 + i % 28
    base = f"{a1[0]}{'AEIOU'[i%5]}{a2[0]}{n[0]}{yy:02d}{mm:02d}{dd:02d}{'HM'[i%2]}{EST}"
    cons = ''.join(random.choice('BCDFGHJKLMNPQRSTVWXYZ') for _ in range(3))
    return base + cons + string.ascii_uppercase[i % 26] + str(i % 10)
def rfc(c): return c[:10] + ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(3))
def nss(i): return f"{10000000000 + i * 7919 % 89999999999:011d}"
def fila(i, coord=''):
    n, a1, a2 = NOM[i % len(NOM)], APE[i % len(APE)], APE[(i * 3 + 1) % len(APE)] + str(i)
    c = curp(i, n, a1, a2); e, rp = EMP[i % 3]
    imss = rp is not None
    sdi = f"{random.choice([300, 350, 420, 512.5, 680]):.2f}" if imss else ''
    r = dict.fromkeys(COLS, '')
    r.update({'Nombres': n, 'Primer apellido': a1, 'Segundo apellido': a2, 'Empresa': e, 'Proyecto': 'PROYECTO IMPORTACION',
      'RFC': rfc(c), 'CURP': c, 'NSS': nss(i), 'CP fiscal': f"{10000 + i:05d}", 'Registro patronal': rp or '',
      'Coordinador': coord, 'Tipo de empleado': 'Base', 'Turno': 'Matutino', 'Fecha de ingreso': f"2025-{1 + i % 12:02d}-{1 + i % 28:02d}",
      'Número interno': str(1000 + i), 'SDI': sdi, 'Tipo de trabajador': '1' if imss else '', 'Tipo de salario': '0' if imss else '',
      'Jornada IMSS': '0' if imss else '',
      'Forma de pago 1': 'Base / IMSS' if imss else 'Efectivo', 'Periodicidad 1': random.choice(['SEMANAL', 'QUINCENAL']),
      'Modalidad 1': 'Bruto' if imss else 'Neto', 'Importe 1': f"{random.choice([2500, 3200, 4100, 5600]):.2f}"})
    if imss and i % 4 == 0:
        r.update({'Forma de pago 2': 'Efectivo', 'Periodicidad 2': r['Periodicidad 1'], 'Modalidad 2': 'Neto', 'Importe 2': '800.00'})
    return r
filas = [fila(i) for i in range(20)]                      # 20 coordinadores, en el mismo archivo
filas += [fila(i, coord=filas[i % 20]['CURP']) for i in range(20, 450)]
def escribir(nombre, rows):
    with open(os.path.join(OUT, nombre), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=COLS); w.writeheader(); w.writerows(rows)
escribir('imp_v2_validos_450.csv', filas)
# Errores: (descripción esperada, modificación) sobre filas nuevas 500+
casos = [
 ('RP de otra empresa', {'Empresa': 'IMPORTA SUR DEMO', 'Registro patronal': 'A0000000001'}),
 ('RP inexistente', {'Registro patronal': 'Z9999999999'}),
 ('SBC menor al salario mínimo', {'SDI': '100.00'}),
 ('IMSS sin SDI', {'SDI': ''}),
 ('Clasificación IMSS sin NSS', {'NSS': ''}),
 ('CURP con formato inválido', {'CURP': 'XXXX'}),
 ('CURP duplicada en el archivo (2 filas)', 'DUP'),
 ('CURP ya registrada en BeeHuman', 'EXISTE'),
 ('Coordinador inexistente', {'Coordinador': 'BEH-999999'}),
 ('Coordinador y coordinador externo a la vez', {'Coordinador': 'BEH-000001', 'Coordinador externo': 'FULANO'}),
 ('Periodicidad inexistente', {'Periodicidad 1': 'DECENAL'}),
 ('Forma de pago inexistente', {'Forma de pago 1': 'HONORARIOS X'}),
 ('Modalidad inválida', {'Modalidad 1': 'Mixto'}),
 ('Importe cero', {'Importe 1': '0'}),
 ('Esquema incompleto (falta periodicidad 2)', {'Forma de pago 2': 'Efectivo', 'Modalidad 2': 'Neto', 'Importe 2': '500'}),
 ('Fecha de ingreso vacía', {'Fecha de ingreso': ''}),
 ('Fecha de ingreso inválida', {'Fecha de ingreso': '31/02/2025'}),
 ('Tipo de trabajador inválido', {'Tipo de trabajador': '9'}),
 ('UMF inválida', {'UMF': '12'}),
 ('Empresa inexistente', {'Empresa': 'NO EXISTE SA'}),
]
err = []
for k, (desc, mod) in enumerate(casos):
    r = fila(501 + k * 3)            # i % 3 == 0 → IMPORTA NORTE DEMO con RP
    if mod == "DUP": r2 = fila(502 + k * 3); r2['CURP'] = r['CURP']; err.append(r2)
    elif mod == 'EXISTE': r['CURP'] = filas[0]['CURP']
    else: r.update(mod)
    err.append(r)
err += [fila(700 + i) for i in range(10)]
escribir('imp_v2_errores.csv', err)
with open(os.path.join(OUT, 'imp_v2_errores_esperados.txt'), 'w', encoding='utf-8') as f:
    f.write('Archivo imp_v2_errores.csv: filas 2..%d con error (una por caso), %d válidas de control al final.\n' % (len(err) - 9, 10))
    for desc, _ in casos: f.write('- ' + desc + '\n')
print('ok', len(filas), len(err))
# --- Archivos adicionales para I5 (corte), I6 (altas nuevas) e I7 (formato anterior de 21 columnas) ---
escribir('imp_v2_corte_120.csv', [fila(1000 + i) for i in range(120)])
escribir('imp_v2_altas_10.csv', [fila(2001 + 3 * i) for i in range(10)])   # i % 3 == 0 → IMPORTA NORTE DEMO con RP
f3 = []
for i in range(5):
    r = fila(3000 + 3 * i + 2)       # i % 3 == 2 → IMPORTA CENTRO DEMO, sin RP
    r = {k: r[k] for k in COLS[:21]}
    if i == 0: r['Proyecto'] = ''   # proyecto opcional
    f3.append(r)
with open(os.path.join(OUT, 'imp_f3_21col_5.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=COLS[:21]); w.writeheader(); w.writerows(f3)
print('adicionales ok')
