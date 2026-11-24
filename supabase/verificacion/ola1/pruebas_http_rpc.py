"""B-c · Llamadas HTTP reales a las funciones RPC de B-a, contra PostgREST LOCAL (127.0.0.1:3010 → base local bhui).
Requiere: bhui con la semilla de ui_concentrado_volumen.py (tenant «TENANT UI VOLUMEN») y PostgREST local en marcha.
  H1  Sin sesión (anon): el concentrado se rechaza.
  H2  Token firmado con otro secreto: 401.
  H3  Nómina: 200, concentrado de 500 personas, huella SHA-256.
  H4  Coordinador: rechazado («sin permiso»).
  H5  Función interna inc__concentrado_base: no expuesta a authenticated.
  H6  Firma con huella desactualizada: rechazada; no se registra.
  H7  Firma con la huella revisada: 200; un evento con la huella.
  H8  Repetir la firma: no duplica («ya tiene la firma vigente»).
  H9  inc_firmar_hoja con área Nómina: rechazada.
  H10 Estado de la firma por HTTP = vigente, misma huella.
Uso: python3 pruebas_http_rpc.py"""
import json, time, hmac, hashlib, base64, subprocess, urllib.request, urllib.error

BASE = 'http://127.0.0.1:3010'
SECRETO = b"beehuman-local-solo-pruebas-secreto-de-32-caracteres-o-mas"
U = {'nomina': '1bd10000-0000-4000-8000-000000000002', 'coordA': '1bd10000-0000-4000-8000-000000000003'}
def sql(q):
    r = subprocess.run(['psql', '-X', '-q', '-At', '-h', '/tmp', '-p', '55432', '-U', 'postgres', '-d', 'bhui', '-c', q], capture_output=True, text=True)
    return r.stdout.strip()
b64 = lambda d: base64.urlsafe_b64encode(d).rstrip(b'=')
def jwt(sub, secreto=SECRETO):
    h = b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    p = b64(json.dumps({"sub": sub, "role": "authenticated", "aud": "authenticated", "exp": int(time.time()) + 3600}).encode())
    return (h + b'.' + p + b'.' + b64(hmac.new(secreto, h + b'.' + p, hashlib.sha256).digest())).decode()
def http(metodo, ruta, cuerpo=None, token=None):
    req = urllib.request.Request(BASE + ruta, method=metodo, data=json.dumps(cuerpo).encode() if cuerpo is not None else None,
                                 headers={'Content-Type': 'application/json', **({'Authorization': 'Bearer ' + token} if token else {})})
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=60) as r: return r.status, r.read().decode()
    except urllib.error.HTTPError as e: return e.code, e.read().decode()
res = []
def ok(c, n, d=''):
    res.append((n, bool(c))); print(('OK    ' if c else 'FALLA ') + n + (f'  [{d}]' if d else ''))

P1 = sql("select id from public.inc_periodos where empresa_id = '1bd20000-0000-4000-8000-000000000001' order by inicio limit 1")
H1 = sql(f"select id from public.inc_hojas where periodo_id = '{P1}' limit 1")
TN, TC = jwt(U['nomina']), jwt(U['coordA'])
rpc = lambda f, args, tok=None: http('POST', f'/rpc/{f}', args, tok)

st, b = rpc('inc_concentrado_periodo', {'p_periodo': P1})
ok(st in (401, 403) and 'permission denied' in b, 'H1 Sin sesión (anon): el concentrado se rechaza', f'{st} {b[:90]}')
st, b = rpc('inc_concentrado_periodo', {'p_periodo': P1}, jwt(U['nomina'], b'otro-secreto-que-no-es-el-del-servidor-1234567890'))
ok(st == 401, 'H2 Token firmado con otro secreto: 401', f'{st} {b[:90]}')
t0 = time.time(); st, b = rpc('inc_concentrado_periodo', {'p_periodo': P1}, TN); dt = time.time() - t0
c = json.loads(b) if st == 200 else {}
ok(st == 200 and c.get('totales', {}).get('personas') == 500 and len(c.get('huella', {}).get('total', '')) == 64,
   'H3 Nómina: 200, concentrado de 500 personas con huella SHA-256', f'{st} · {dt:.2f} s · {len(b) / 1e6:.2f} MB · estado={c.get("estado")}')
st, b = rpc('inc_concentrado_periodo', {'p_periodo': P1}, TC)
ok(st >= 400 and 'sin permiso' in b, 'H4 Coordinador: rechazado', f'{st} {b[:90]}')
st, b = rpc('inc__concentrado_base', {'p_periodo': P1}, TN)
ok(st in (401, 403, 404) and ('permission denied' in b or 'Could not find' in b), 'H5 Función interna no expuesta a usuarios', f'{st} {b[:90]}')
st, b = rpc('inc_firmar_periodo', {'p_periodo': P1, 'p_huella_revisada': '0' * 64}, TN)
n0 = sql(f"select count(*) from public.inc_eventos where periodo_id = '{P1}' and tipo = 'firma_nomina'")
ok(st >= 400 and 'cambió mientras lo revisabas' in b and n0 == '0', 'H6 Firma con huella desactualizada: rechazada y no registrada', f'{st} {b[:90]}')
st, b = rpc('inc_firmar_periodo', {'p_periodo': P1, 'p_huella_revisada': c['huella']['total']}, TN)
n1 = sql(f"select count(*) from public.inc_eventos where periodo_id = '{P1}' and tipo = 'firma_nomina' and hoja_id is null and huella->>'total' = '{c['huella']['total']}'")
ok(st == 200 and 'registrada' in b and n1 == '1', 'H7 Firma con la huella revisada: 200 y un evento con esa huella', f'{st} {b[:90]}')
st, b = rpc('inc_firmar_periodo', {'p_periodo': P1, 'p_huella_revisada': c['huella']['total']}, TN)
n2 = sql(f"select count(*) from public.inc_eventos where periodo_id = '{P1}' and tipo = 'firma_nomina'")
ok(st == 200 and 'ya tiene la firma de Nómina vigente' in b and n2 == '1', 'H8 Repetir la firma no la duplica', f'{st} {b[:90]}')
st, b = rpc('inc_firmar_hoja', {'p_hoja': H1, 'p_area': 'nomina'}, TN)
ok(st >= 400 and 'Nómina firma el periodo completo' in b, 'H9 inc_firmar_hoja con área Nómina: rechazada', f'{st} {b[:90]}')
st, b = rpc('inc_firma_periodo_estado', {'p_periodo': P1}, TN)
e = json.loads(b) if st == 200 else {}
ok(st == 200 and e.get('estado') == 'vigente' and e.get('huella_actual', {}).get('total') == c['huella']['total'], 'H10 Estado de la firma por HTTP: vigente con la misma huella', f'{st} {e.get("estado")}')

malas = [r for r in res if not r[1]]
print(f'\nRESULTADO: {len(res) - len(malas)} de {len(res)} verificaciones OK')
raise SystemExit(1 if malas else 0)
