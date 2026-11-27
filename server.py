"""¿Qué dirIA Bogotá? — servidor local sin dependencias externas.
Datos oficiales: IDRD / Datos Abiertos Bogotá (CC BY 4.0).
El motor de consulta es determinista; Gemini, si está configurado,
solo interpreta la intención. Nunca inventa las cifras.
"""
from __future__ import annotations
import csv, io, json, os, re, sys, time, unicodedata, threading, urllib.request, urllib.error, webbrowser
from collections import Counter
from datetime import datetime
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
WEB=ROOT/'web'
DATA.mkdir(exist_ok=True)
PORT=int(os.environ.get('PORT','8765'))
# Seguridad: en Internet los archivos se publican con el repositorio, no por POST.
PUBLIC_DEPLOY=os.environ.get('PUBLIC_DEPLOY','0').strip()=='1'
DATASETS=[
 {'id':'parques-idrd','title':'Parques IDRD (estructurantes)','landing':'https://datosabiertos.bogota.gov.co/dataset/parques-idrd','cutoff':'2025-09-04'},
 {'id':'depor2023','title':'Directorio de parques y escenarios IDRD','landing':'https://datosabiertos.bogota.gov.co/dataset/depor2023','cutoff':'2023-09-06'}
]
API='https://datosabiertos.bogota.gov.co/api/3/action/package_show?id='
DIRECT='https://datosabiertos.bogota.gov.co/dataset/c4118610-b7cf-4dd9-bc75-66849d978cfc/resource/06510918-188e-492b-809b-50ac5ed63f95/download/directorio-parques-y-escenarios-2023-datos-abiertos-v1.0.csv'
LOCALITIES=['Usaquén','Chapinero','Santa Fe','San Cristóbal','Usme','Tunjuelito','Bosa','Kennedy','Fontibón','Engativá','Suba','Barrios Unidos','Teusaquillo','Los Mártires','Antonio Nariño','Puente Aranda','La Candelaria','Rafael Uribe Uribe','Ciudad Bolívar','Sumapaz']
# ÚNICAS cifras incorporadas desde el pitch facilitado por el equipo, no son registros CSV.
PITCH_SNAPSHOT={'total':210,'localities':19,'counts':{'Suba':27,'Kennedy':22,'Engativá':18},'source':'Pitch_Que_dirIA_Bogota_v2.pdf, páginas 1 y 3 / presentación, página 5','note':'Cifras declaradas por el equipo; todavía no verificadas contra los CSV originales.'}

state={'records':[], 'sources':[], 'warnings':[], 'last_check':None,'loaded':False}
lock=threading.RLock()

def norm(v):
    text=unicodedata.normalize('NFKD',str(v or ''))
    text=''.join(c for c in text if not unicodedata.combining(c)).lower()
    return re.sub(r'[^a-z0-9]+',' ',text).strip()

def key(v):return norm(v).replace(' ','')

def read_csv(raw):
    for enc in ('utf-8-sig','utf-8','cp1252','latin-1'):
        try:
            text=raw.decode(enc)
            if '\ufffd' not in text: break
        except UnicodeDecodeError: continue
    else: text=raw.decode('utf-8',errors='replace')
    header=text[:2000]
    try: dialect=csv.Sniffer().sniff(header,delimiters=',;\t|')
    except Exception: dialect=csv.excel
    rows=list(csv.DictReader(io.StringIO(text),dialect=dialect))
    return [{str(k or '').strip():str(v or '').strip() for k,v in r.items() if k is not None} for r in rows if isinstance(r,dict)]

def detect_col(columns, ordered, partial=True):
    pairs=[(c,norm(c)) for c in columns]
    for val in ordered:
        for c,k in pairs:
            if k==norm(val):return c
    if partial:
        for val in ordered:
            for c,k in pairs:
                if norm(val) in k:return c
    return None

def loc_value(v):
    if not str(v).strip(): return ''
    val=norm(v)
    # aceptar num de localidad solo cuando la columna se llama claramente localidad
    codes={'1':'Usaquén','2':'Chapinero','3':'Santa Fe','4':'San Cristóbal','5':'Usme','6':'Tunjuelito','7':'Bosa','8':'Kennedy','9':'Fontibón','10':'Engativá','11':'Suba','12':'Barrios Unidos','13':'Teusaquillo','14':'Los Mártires','15':'Antonio Nariño','16':'Puente Aranda','17':'La Candelaria','18':'Rafael Uribe Uribe','19':'Ciudad Bolívar','20':'Sumapaz'}
    if val in codes:return codes[val]
    for loc in sorted(LOCALITIES,key=len,reverse=True):
        if val==norm(loc) or val.endswith(' '+norm(loc)) or val.startswith(norm(loc)+' '):return loc
    return str(v).strip().title()

def fnum(v):
    s=str(v or '').strip().replace(' ','')
    if not s:return None
    s=s.replace(',','.') if s.count(',')==1 and '.' not in s else s.replace(',','')
    try: return float(s)
    except ValueError:return None

def geopoint(row, cols):
    lat=detect_col(cols,['latitud','lat','y coordenada','coordenada y','coordy','latitude'],True)
    lon=detect_col(cols,['longitud','lon','lng','x coordenada','coordenada x','coordx','longitude'],True)
    if lat and lon:
        a,b=fnum(row.get(lat)),fnum(row.get(lon))
        if a is not None and b is not None and 4.3<a<5.1 and -75<b<-73.4:return [a,b]
    return None

def build_records(all_sets):
    merged=[]; sources=[]; warnings=[]; seen=set(); avail_cols=set()
    for info, rows in all_sets:
        if not rows:
            warnings.append(f"{info.get('title','Fuente')}: archivo sin filas legibles.");continue
        columns=list(rows[0].keys()); avail_cols.update(columns)
        name=detect_col(columns,['nombre del parque','nombre parque y o escenario','nombre parque','nombre del escenario','nombre escenario','nom_parque','nombre','parque','escenario','nomb_parq'])
        locality=detect_col(columns,['nombre localidad','localidad','nom_loc','localid','cod_localidad'])
        ptype=detect_col(columns,['tipo parque','tipologia','categoria','tipo de parque','tipo de escenario','tipo','clasificacion','escala'])
        code=detect_col(columns,['codigo parque y o escenario','codigo parque','codigo del parque','cod_parque','codigo','codpark'])
        area=detect_col(columns,['area ha','area m2','area del parque','area','superficie'])
        if not name:
            warnings.append(f"{info['title']}: no se identificó columna de nombre ({', '.join(columns[:9])}).");continue
        for pos,r in enumerate(rows):
            namev=str(r.get(name,'')).strip()
            if not namev:continue
            loc=loc_value(r.get(locality,'')) if locality else ''
            typ=str(r.get(ptype,'')).strip() if ptype else ''
            cv=str(r.get(code,'')).strip() if code else ''
            dedup=('code',norm(cv)) if cv and len(norm(cv))>3 else ('name-loc',norm(namev),norm(loc))
            if dedup in seen:continue
            seen.add(dedup)
            obj={'id':f'p{len(merged)+1}','name':namev,'locality':loc,'type':typ,'code':cv,'area':str(r.get(area,'')) if area else '',
                 'coords':geopoint(r,columns),'source_title':info['title'],'source_url':info['landing'],'source_cutoff':info.get('cutoff','No disponible'),
                 'raw':{k:v for k,v in list(r.items())[:24]}}
            merged.append(obj)
        sources.append({'title':info['title'],'url':info['landing'],'cutoff':info.get('cutoff','No disponible'),'rows':len(rows),'columns':columns,'detected':{'name':name,'locality':locality,'type':ptype,'code':code,'area':area}})
        if not locality:warnings.append(f"{info['title']}: no se pudo identificar la columna de localidad.")
    return merged,sources,warnings

def get_bytes(url):
    if not url.startswith('https://datosabiertos.bogota.gov.co/'):
        raise ValueError('Solo se descargan fuentes oficiales declaradas.')
    req=urllib.request.Request(url,headers={'User-Agent':'Que-dirIA-Bogota/1.0 (uso academico)','Accept':'*/*'})
    with urllib.request.urlopen(req,timeout=15) as res:
        if res.status!=200:raise ValueError(f'HTTP {res.status}')
        dat=res.read(12_000_001)
        if len(dat)>12_000_000:raise ValueError('Archivo mayor a 12 MB')
        return dat

def download_source(item):
    errors=[]
    try:
        payload=json.loads(get_bytes(API+item['id']))
        if not payload.get('success'):raise ValueError('CKAN sin éxito')
        resources=payload['result'].get('resources',[])
        options=[r for r in resources if norm(r.get('format')) in ('csv','text csv') and not any(x in norm(r.get('name','')) for x in ('meta','diccionario','data dictionary'))]
        for resource in options:
            try:
                u=resource.get('url','')
                if u.startswith('http://datosabiertos.bogota.gov.co'):
                    u='https://'+u.split('://',1)[1]
                if not u.startswith('https://datosabiertos.bogota.gov.co/'):
                    continue
                b=get_bytes(u)
                rows=read_csv(b)
                if rows:
                    p=DATA/(item['id']+'.csv');p.write_bytes(b)
                    return rows,None
            except Exception as e:errors.append(str(e))
    except Exception as e:errors.append(str(e))
    if item['id']=='depor2023':
        try:
            b=get_bytes(DIRECT)
            rows=read_csv(b)
            if rows:
                (DATA/'depor2023.csv').write_bytes(b)
                return rows,None
        except Exception as e:errors.append(str(e))
    return [],'; '.join(errors[:2]) or 'No se logró descargar'

def load_data(remote=False, fetch_if_missing=True):
    all_sets=[];warnings=[]
    # uploads guardados individualmente, con metadata en un archivo local
    uploaded=DATA/'uploaded.json'
    if uploaded.exists():
        try:
            for meta in json.loads(uploaded.read_text('utf-8')):
                filename=DATA/meta['file']
                if filename.is_file():all_sets.append((meta,read_csv(filename.read_bytes())))
        except Exception as e:warnings.append(f'Error de archivos cargados: {e}')
    for item in DATASETS:
        path=DATA/(item['id']+'.csv')
        if remote or (fetch_if_missing and not path.exists()):
            rows,err=download_source(item)
            if err:warnings.append(f"{item['title']}: {err}")
        else:
            rows=read_csv(path.read_bytes()) if path.exists() else []
        if rows:all_sets.append((item,rows))
    # Una descarga en segundo plano no debe borrar un CSV importado mientras tanto.
    if uploaded.exists():
        try:
            already={i.get('file') for i,_ in all_sets}
            for meta in json.loads(uploaded.read_text('utf-8')):
                file_path=DATA/meta['file']
                if meta['file'] not in already and file_path.is_file():
                    all_sets.append((meta,read_csv(file_path.read_bytes())))
        except Exception as e:warnings.append(f'Actualización de importaciones: {e}')
    records,sources,warns=build_records(all_sets)
    with lock:
        state.update({'records':records,'sources':sources,'warnings':warnings+warns,'last_check':datetime.now().isoformat(timespec='seconds'),'loaded':bool(records)})
    return len(records)

def get_stats():
    with lock:
        recs=list(state['records']);sources=list(state['sources']);warnings=list(state['warnings']);check=state['last_check']
    if not recs:
        return {'mode':'snapshot','total':PITCH_SNAPSHOT['total'],'localities':PITCH_SNAPSHOT['localities'],'counts':PITCH_SNAPSHOT['counts'],
                'top':sorted([{'name':k,'count':v} for k,v in PITCH_SNAPSHOT['counts'].items()],key=lambda x:-x['count']),
                'types':[],'places':[],'sources':[],'warnings':warnings,'last_check':check,'snapshot_note':PITCH_SNAPSHOT['note'],
                'mapped':0,'columns':[],'coverage':'Cifras parciales del pitch, no inventario exhaustivo'}
    counts=Counter(r['locality'] for r in recs if r['locality'])
    types=Counter(r['type'] for r in recs if r['type'])
    return {'mode':'csv_loaded','total':len(recs),'localities':len(counts),'counts':dict(counts),
            'top':[{'name':k,'count':v} for k,v in counts.most_common(20)],
            'types':[{'name':k,'count':v} for k,v in types.most_common(20)],
            'places':[{k:r[k] for k in ('id','name','locality','type','code','coords','source_url','source_title','source_cutoff')} for r in recs],
            'sources':sources,'warnings':warnings,'last_check':check,'snapshot_note':None,
            'mapped':sum(bool(r['coords']) for r in recs),
            'columns':[{'source':s['title'],'detected':s['detected']} for s in sources],
            'coverage':'Inventario cargado; no equivale al total de parques de Bogotá'}

# Traducción de lenguaje natural a un objeto de consulta. Gemini solo ve pregunta y esquema.
def guess_intent(q):
    n=norm(q)
    locations=[l for l in LOCALITIES if re.search(r'(?<!\w)'+re.escape(norm(l))+r'(?!\w)',n)]
    if re.search(r'\b(horarios?|reserv(ar|a|as)|disponib(le|ilidad)|precios?|pagos?|cuanto cuesta|segur(o|idad))\b',n) or any(t in n for t in ('mas grande','mas extenso','mayor area','mayor tamano','mas cercan','cerca de mi','mas seguro')):intent='unsupported'
    elif re.search(r'\b(mas|mayor|mayores|menos|menor)\b',n) and re.search(r'\b(localidad|localidades|donde|cual|que)\b',n):intent='rank'
    elif any(w in n for w in ('compara','comparar','versus',' vs ','diferencia entre')):intent='compare'
    elif any(w in n for w in ('cuantos','cuantas','cantidad','numero de','total de')):intent='count'
    elif any(w in n for w in ('tipos de','categorias','clases de','clasificacion','tipologia')):intent='types'
    elif any(w in n for w in ('donde queda','ubicacion','direccion','mapa','ubica')):intent='list'
    else:intent='list'
    if len(locations)>1 and intent not in ('unsupported','rank'): intent='compare'
    orientation='min' if any(w in n for w in ('menos','menor','pocos','minimo')) else 'max'
    query_type=''
    if 'estructurant' in n:query_type='estructurante'
    elif 'metropolitan' in n:query_type='metropolitano'
    elif 'zonal' in n:query_type='zonal'
    elif 'vecinal' in n:query_type='vecinal'
    elif 'bolsillo' in n:query_type='bolsillo'
    elif 'regional' in n:query_type='regional'
    sport=any(x in n for x in ('cancha','futbol','baloncesto','tenis','voleibol','gimnasio','piscina'))
    # nombre específico por comillas; mejor no interpretar palabras como parques como nombre
    match=re.search(r'["“](.+?)["”]',q)
    name=match.group(1).strip() if match else ''
    return {'intent':intent,'localities':locations,'type':query_type,'sport':sport,'name':name,'orientation':orientation,'question':q}

gemini_quota={'window':time.monotonic(),'used':0}
gemini_quota_lock=threading.Lock()

def gemini_intent(q):
    api_key=os.environ.get('GEMINI_API_KEY','').strip()
    if not api_key:return None
    # Control básico de consumo en despliegues públicos; reinicia al reiniciar servidor.
    if PUBLIC_DEPLOY:
        with gemini_quota_lock:
            now=time.monotonic()
            if now-gemini_quota['window']>=3600:
                gemini_quota.update(window=now,used=0)
            limit=max(1,int(os.environ.get('GEMINI_HOURLY_LIMIT','40')))
            if gemini_quota['used']>=limit:return None
            gemini_quota['used']+=1
    model=os.environ.get('GEMINI_MODEL','gemini-2.5-flash')
    guidance='''Eres un parser de intención de consultas sobre parques en Bogotá, NO respondes la pregunta. Devuelve solo JSON puro sin markdown con campos intent (list|count|rank|types|compare|unsupported), localities (array de nombres oficiales Bogotá), type (estructurante|zonal|vecinal|metropolitano|bolsillo|regional|''), name (nombre parque si explícito, o ''), orientation (max|min), sport (boolean). Para reservas, disponibilidad en tiempo real, seguridad, tarifas u horarios indica unsupported. No inventes campos de datos ni resultados. Pregunta: '''+q
    try:
        url=f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}'
        req=urllib.request.Request(url,data=json.dumps({'contents':[{'parts':[{'text':guidance}]}],'generationConfig':{'temperature':0,'responseMimeType':'application/json'}}).encode(),headers={'Content-Type':'application/json'},method='POST')
        with urllib.request.urlopen(req,timeout=13) as res:payload=json.load(res)
        out=payload['candidates'][0]['content']['parts'][0]['text']
        obj=json.loads(out)
        if not isinstance(obj,dict) or obj.get('intent') not in {'list','count','rank','types','compare','unsupported'}:return None
        permitted=[]
        for l in obj.get('localities',[]):
            for official in LOCALITIES:
                if norm(l)==norm(official) and official not in permitted:permitted.append(official)
        return {'intent':obj['intent'],'localities':permitted[:3], 'type':str(obj.get('type','')).lower() if str(obj.get('type','')).lower() in {'estructurante','zonal','vecinal','metropolitano','bolsillo','regional'} else '',
                'name':str(obj.get('name',''))[:100],'orientation':obj.get('orientation','max') if obj.get('orientation') in ('max','min') else 'max',
                'sport':bool(obj.get('sport',False)),'question':q}
    except Exception:return None

def answer(question,allow_gemini=True):
    q=str(question or '').strip()[:500]
    if not q:return {'ok':False,'answer':'Escribe una pregunta para comenzar.'}
    parsed=gemini_intent(q) if allow_gemini else None
    engine='Gemini (interpretación de intención)' if parsed else 'Intérprete local (reglas)'
    p=parsed or guess_intent(q)
    with lock:allrecs=list(state['records']);sources=list(state['sources'])
    # Reconocer nombres de parques presentes en los datos, incluso sin comillas.
    if not p.get('name') and p['intent']=='list' and allrecs:
        nq=norm(q)
        matches=sorted({r['name'] for r in allrecs if len(norm(r['name']))>=8 and norm(r['name']) in nq},key=len,reverse=True)
        if matches:p['name']=matches[0]
    if p['intent']=='unsupported':
        return response('No dispongo de información verificada para esta consulta (reservas, horarios, precios, disponibilidad, seguridad, cercanía a tu ubicación o tamaños comparados sin un análisis específico). Este prototipo consulta el inventario, no servicios en vivo.',p,engine,[],None,allrecs,[])
    if p['sport']:
        # Nunca deducir canchas de un inventario que no tenga variables de ese tipo.
        sport_cols=[norm(k) for s in sources for k in s['detected'].values() if k]
        contains_sport=any(any(word in norm(str(v)) for word in ('cancha','futbol','tenis','baloncesto')) for r in allrecs for v in (r['type'],))
        if not contains_sport:
            return response('La fuente cargada no permite confirmar qué parques tienen canchas o equipamiento para ese deporte. Puedo buscar por localidad, nombre y tipología; para instalaciones específicas necesitamos otro inventario oficial.',p,engine,[],None,allrecs,[])
    if not allrecs:
        return answer_snapshot(p,engine)
    recs=allrecs
    if p['localities'] and p['intent']!='compare':recs=[r for r in recs if r['locality'] in p['localities']]
    if p['type']:
        if not any(r['type'] for r in allrecs):
            return response('Los datos cargados no incluyen una columna de tipología reconocible. No puedo filtrar por tipo sin inventar la clasificación.',p,engine,[],None,allrecs,[])
        recs=[r for r in recs if norm(p['type']) in norm(r['type'])]
    if p['sport']:
        nq=norm(q)
        words=[x for x in ('futbol','tenis','baloncesto','voleibol','piscina','gimnasio') if x in nq]
        if not words:words=['cancha']
        recs=[r for r in recs if any(w in norm(r['type']+' '+r['name']) for w in words)]
    if p['name']:
        recs=[r for r in recs if norm(p['name']) in norm(r['name'])]
    if p['intent']=='types':
        types=Counter(r['type'] for r in recs if r['type'])
        if not types:return response('La fuente consultada no contiene tipologías reconocibles para esta consulta.',p,engine,[],None,allrecs,[])
        top=types.most_common(12)
        return response('Según los registros cargados, estas son las tipologías identificadas: '+', '.join(f'{k}: {v}' for k,v in top)+'.',p,engine,recs[:12],{'kind':'bars','data':[{'label':k,'value':v} for k,v in top]},allrecs,source_list(recs))
    if p['intent']=='compare' and len(p['localities'])>=2:
        counts={l:sum(r['locality']==l and (not p['type'] or p['type'] in norm(r['type'])) for r in allrecs) for l in p['localities']}
        phrase='; '.join(f'{l}: {v} registros' for l,v in counts.items())
        return response('En el inventario cargado, '+phrase+'. Esta comparación solo cubre las fuentes seleccionadas.',p,engine,[r for r in allrecs if r['locality'] in counts][:12],{'kind':'bars','data':[{'label':k,'value':v} for k,v in counts.items()]},allrecs,source_list(allrecs))
    if p['intent']=='rank':
        if not any(r['locality'] for r in recs):
            return response('Este archivo no trae localidades reconocibles para calcular un ranking.',p,engine,[],None,allrecs,[])
        counts=Counter(r['locality'] for r in recs if r['locality'])
        if not counts:return response('No hay registros en el filtro solicitado.',p,engine,[],None,allrecs,[])
        ordered=sorted(counts.items(),key=lambda x:(x[1],x[0]) if p['orientation']=='min' else (-x[1],x[0]))
        win=ordered[0]
        res=f'En **este inventario** la localidad con {"menos" if p["orientation"]=="min" else "más"} registros es **{win[0]}**, con **{win[1]}**. Esto no representa necesariamente el total de todos los parques de Bogotá.'
        return response(res,p,engine,[r for r in recs if r['locality']==win[0]][:12],{'kind':'bars','data':[{'label':a,'value':b} for a,b in ordered[:10]]},allrecs,source_list(recs))
    if p['intent']=='count':
        if not p['localities'] and any(x in norm(q) for x in ('por localidad','distribucion por localidad','cada localidad')):
            counter=Counter(r['locality'] for r in recs if r['locality'])
            items=counter.most_common(15)
            if items:
                txt='Distribución de los **'+str(len(recs))+' registros** consultados: '+', '.join(f'{l}: {v}' for l,v in items[:5])+'. El desglose corresponde al inventario cargado.'
                return response(txt,p,engine,recs[:10],{'kind':'bars','data':[{'label':l,'value':v} for l,v in items]},allrecs,source_list(recs))
        desc=' para '+', '.join(p['localities']) if p['localities'] else ''
        typ=' de tipo '+p['type'] if p['type'] else ''
        txt=f'Encontré **{len(recs)} registros**{typ}{desc} en los conjuntos de datos cargados. El conteo corresponde al inventario consultado, no necesariamente a todos los parques de Bogotá.'
        return response(txt,p,engine,recs[:12],None,allrecs,source_list(recs or allrecs))
    if not recs:
        return response('No encontré registros que coincidan con los filtros en los datos cargados. Esto no significa que el parque no exista, sino que no figura en este inventario.',p,engine,[],None,allrecs,source_list(allrecs))
    heads=', '.join('**'+r['name']+'**'+(' ('+r['locality']+')' if r['locality'] else '') for r in recs[:5])
    txt=f'Encontré **{len(recs)} registros** que coinciden con tu consulta. Algunos son: {heads}.'+(' Puedes ver más resultados en el explorador.' if len(recs)>5 else '')
    return response(txt,p,engine,recs[:15],None,allrecs,source_list(recs))

def source_list(recs):
    seen=set();out=[]
    for r in recs:
        if r['source_url'] not in seen:
            seen.add(r['source_url']);out.append({'title':r['source_title'],'url':r['source_url'],'cutoff':r['source_cutoff']})
    return out

def response(txt,p,engine,matches,chart,allrecs,sources):
    return {'ok':True,'answer':txt,'interpretation':p,'engine':engine,'mode':'csv_loaded' if allrecs else 'snapshot','results':matches,
           'chart':chart,'sources':sources,'audit':{'scope':'Datos cargados' if allrecs else 'Resumen del pitch','candidate_rows':len(allrecs),'returned_rows':len(matches),
           'filters':{'localidades':p['localities'],'tipo':p['type'],'nombre':p['name'],'intención':p['intent']}}}

def answer_snapshot(p,engine):
    src=[{'title':'Pitch del equipo – cifras declaradas (sin CSV)','url':'','cutoff':'No verificable desde el PDF'}]
    if p['sport'] or p['type'] or p['name']:
        txt='La presentación del equipo no incluye registros individuales ni campos para esa consulta. **Carga el CSV oficial del IDRD** para obtener una respuesta verificable.'
    elif p['intent']=='count':
        if p['localities']:
            nums=[(l,PITCH_SNAPSHOT['counts'].get(l)) for l in p['localities']]
            txt='; '.join(f'{l}: {v} registros' if v is not None else f'{l}: sin cifra en la presentación' for l,v in nums)+'. **Estas cifras provienen del pitch, no de un CSV verificado.**'
        else:txt='El pitch del equipo declara **210 registros en 19 localidades urbanas**. Es una cifra del material de presentación, aún no validada frente a los CSV.'
    elif p['intent']=='compare' and len(p['localities'])>=2:
        txt='; '.join(f'{l}: {PITCH_SNAPSHOT["counts"].get(l,"sin cifra disponible")}' for l in p['localities'])+'. Estos son datos parciales del pitch, no el inventario completo.'
    elif p['intent']=='rank':txt='No es posible establecer un ranking fiable sin disponer del inventario completo. El pitch solo muestra Suba (27), Kennedy (22) y Engativá (18) como ejemplos.'
    else:txt='Puedo ayudarte a consultar parques por localidad, nombre o tipo, pero primero necesito cargar el CSV oficial. Mientras tanto, el pitch reporta 210 registros en 19 localidades, cifras pendientes de verificación.'
    obj=response(txt,p,engine,[],None,[],src)
    obj['mode']='snapshot'
    obj['audit']['scope']='Diapositivas del equipo, datos agregados parciales'
    return obj

def run_benchmark():
    """Prueba funcional interna: expectativas calculadas del CSV, NO estudio con ciudadanos."""
    with lock:recs=list(state['records'])
    if not recs:return {'ok':False,'message':'Carga primero un CSV para ejecutar pruebas automáticas.'}
    counts=Counter(r['locality'] for r in recs if r['locality'])
    if not counts:return {'ok':False,'message':'El CSV no incluye localidades legibles para crear preguntas de control.'}
    templates=[
      '¿Cuántos registros hay en {loc}?',
      '¿Cuál es el número de registros en {loc}?',
      '¿Qué cantidad de parques registrados hay en {loc}?',
    ]
    cases=[]
    for template in templates:
      for loc in sorted(counts):
        if len(cases)>=30:break
        question=template.format(loc=loc)
        a=answer(question,allow_gemini=False)
        match=re.search(r'\*\*(\d+) registros\*\*',a.get('answer',''))
        actual=int(match.group(1)) if match else None
        cases.append({'question':question,'expected':counts[loc],'obtained':actual,'passed':actual==counts[loc]})
    return {'ok':True,'executed':len(cases),'passed':sum(c['passed'] for c in cases),
      'cases':cases,'note':'Prueba funcional sobre conteos del CSV; no equivale a precisión global de IA ni a evaluación con usuarios.'}

class Handler(BaseHTTPRequestHandler):
    def log_message(self,fmt,*args):pass
    def reply(self,obj,code=200):
        raw=json.dumps(obj,ensure_ascii=False,default=str).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Length',str(len(raw)))
        self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/api/state':
            stats=get_stats();stats['ai_active']=bool(os.getenv('GEMINI_API_KEY'));stats['public_deploy']=PUBLIC_DEPLOY
            return self.reply(stats)
        if path=='/api/health':return self.reply({'ok':True})
        if path=='/api/benchmark':return self.reply(run_benchmark())
        if path=='/':path='/index.html'
        candidate=(WEB/path.lstrip('/')).resolve()
        if not str(candidate).startswith(str(WEB.resolve())) or not candidate.is_file():
            self.send_error(404);return
        ext=candidate.suffix.lower()
        mime={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'application/javascript; charset=utf-8','.svg':'image/svg+xml','.png':'image/png','.ico':'image/x-icon'}.get(ext,'application/octet-stream')
        content=candidate.read_bytes();self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(content)));self.end_headers();self.wfile.write(content)
    def do_POST(self):
        path=urlparse(self.path).path
        length=int(self.headers.get('Content-Length','0'))
        if length>12_000_000:return self.reply({'error':'El archivo supera 12MB'},413)
        raw=self.rfile.read(length)
        if path=='/api/chat':
            try:
                data=json.loads(raw)
                return self.reply(answer(data.get('question','')))
            except Exception as e:return self.reply({'error':str(e)},400)
        if path=='/api/upload':
            if PUBLIC_DEPLOY:return self.reply({'error':'Importación pública deshabilitada por seguridad. El administrador debe agregar los CSV al repositorio /data y publicar una nueva versión.'},403)
            filename=str(self.headers.get('X-Filename','archivo.csv'))[:120]
            if not filename.lower().endswith('.csv'):
                return self.reply({'error':'Sube un archivo CSV, no Excel o PDF.'},400)
            try:
                rows=read_csv(raw)
                if not rows:return self.reply({'error':'El archivo CSV no contiene registros legibles.'},400)
                safe='upload_'+str(int(time.time()))+'.csv'
                (DATA/safe).write_bytes(raw)
                registry=DATA/'uploaded.json'
                metas=json.loads(registry.read_text('utf-8')) if registry.exists() else []
                if len(metas)>=5:return self.reply({'error':'Máximo 5 archivos cargados; reinicia importaciones para reemplazarlos.'},400)
                selected_source=str(self.headers.get('X-Source-Id','unknown'))
                official=next((d for d in DATASETS if d['id']==selected_source),None)
                metas.append({'id':safe,'title':'CSV aportado: '+Path(filename).name+' (procedencia declarada)',
                              'landing':official['landing'] if official else '',
                              'cutoff':'Fecha del CSV por verificar', 'file':safe})
                registry.write_text(json.dumps(metas,ensure_ascii=False,indent=2),'utf-8')
                n=load_data(False, fetch_if_missing=False)
                return self.reply({'ok':True,'total':n,'uploaded_rows':len(rows),'name':filename})
            except Exception as e:return self.reply({'error':str(e)},400)
        if path=='/api/refresh':
            if PUBLIC_DEPLOY:return self.reply({'error':'La actualización pública está deshabilitada. Los archivos de datos se actualizan desde el repositorio.'},403)
            n=load_data(True)
            return self.reply({'ok':True,'total':n,'warnings':get_stats()['warnings']})
        return self.reply({'error':'Ruta no encontrada'},404)

def main():
    print('\n'+'='*60+'\n  ¿QUÉ dirIA BOGOTÁ?  |  Demo interactiva IDRD\n'+'='*60)
    print('Buscando datos oficiales guardados o en línea...')
    count=load_data(False, fetch_if_missing=False)
    print(('Registros cargados: '+str(count)) if count else 'Modo ilustrativo: cifras del pitch pendientes de validación con CSV.')
    if os.getenv('GEMINI_API_KEY'):print('Gemini: activo (solo interpreta intenciones)')
    else:print('Gemini: no configurado (funciona con intérprete de reglas)')
    httpd=ThreadingHTTPServer(('0.0.0.0',PORT),Handler)
    url=f'http://localhost:{PORT}'
    print(f'Abre en el navegador: {url}\nPara cerrar, presiona Ctrl+C.\n')
    if os.environ.get('OPEN_BROWSER','0' if PUBLIC_DEPLOY else '1')=='1':threading.Timer(1.0,lambda:webbrowser.open(url)).start()
    threading.Thread(target=lambda: load_data(False), daemon=True).start()  # Consulta oficial sin bloquear el inicio
    try:httpd.serve_forever()
    except KeyboardInterrupt:pass
    finally:httpd.server_close()
if __name__=='__main__':main()
