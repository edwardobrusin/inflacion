import io
import os
import re
import pandas as pd
import requests

# 1. Diccionario CCIF
ccif_diccionario = {
    'Arroz': '908714',
    'Botanas elaboradas con cereales': '908715',
    'Cereales en hojuelas': '908716',
    'Galletas': '908717',
    'Harinas de trigo': '908718',
    'Maíz': '908719',
    'Masa y harinas de maíz': '908720',
    'Pan blanco': '908721',
    'Pan de caja': '908722',
    'Pan dulce': '908723',
    'Pasta para sopa': '908724',
    'Pasteles, pastelillos y pan dulce empaquetado': '908725',
    'Pastelillos y pasteles a granel': '908726',
    'Tortilla de maíz': '908727',
    'Tortillas de harina de trigo': '908728',
    'Tostadas': '908729',
    'Carne de cerdo': '908731',
    'Carne de res': '908732',
    'Carnes secas, procesadas y otros embutidos': '908733',
    'Chorizo': '908734',
    'Jamón': '908735',
    'Pollo': '908736',
    'Salchichas': '908737',
    'Tocino': '908738',
    'Vísceras de res': '908739',
    'Atún y sardina en lata': '908741',
    'Camarón': '908742',
    'Pescado': '908743',
    'Otros pescados y mariscos en conserva': '908744',
    'Crema y otros productos a base de leche': '908746',
    'Huevo': '908747',
    'Leche en polvo': '908748',
    'Leche evaporada y condensada': '908749',
    'Leche pasteurizada y fresca': '908750',
    'Leches de origen vegetal': '908751',
    'Queso amarillo': '908752',
    'Queso fresco': '908753',
    'Queso manchego y Chihuahua': '908754',
    'Queso Oaxaca y asadero': '908755',
    'Otros quesos': '908756',
    'Yogurt': '908757',
    'Aceites y grasas vegetales comestibles': '908759',
    'Manteca de cerdo': '908760',
    'Mantequilla': '908761',
    'Aguacate': '908763',
    'Durazno': '908764',
    'Guayaba': '908765',
    'Limón': '908766',
    'Manzana': '908767',
    'Melón': '908768',
    'Naranja': '908769',
    'Papaya': '908770',
    'Pera': '908771',
    'Piña': '908772',
    'Plátanos': '908773',
    'Sandía': '908774',
    'Uva': '908775',
    'Otras conservas de frutas': '908776',
    'Otras frutas': '908777',
    'Calabacita': '908779',
    'Cebolla': '908780',
    'Chayote': '908781',
    'Chile poblano': '908782',
    'Chile seco': '908783',
    'Chile serrano': '908784',
    'Chiles envasados': '908785',
    'Ejotes': '908786',
    'Frijol': '908787',
    'Frijol procesado': '908788',
    'Jitomate': '908789',
    'Lechuga y col': '908790',
    'Nopales': '908791',
    'Papa y otros tubérculos': '908792',
    'Papas fritas': '908793',
    'Pepino': '908794',
    'Tomate verde': '908795',
    'Verduras envasadas': '908796',
    'Zanahoria': '908797',
    'Otras legumbres secas': '908798',
    'Otras verduras y legumbres': '908799',
    'Otros chiles frescos': '908800',
    'Azúcar': '908802',
    'Chocolate líquido y para preparar bebida': '908803',
    'Chocolate y productos de confitería': '908804',
    'Gelatina, miel y mermeladas': '908805',
    'Helados, nieves y paletas de hielo': '908806',
    'Cilantro, epazote y perejil': '908808',
    'Concentrados de pollo y sal': '908809',
    'Gelatina en polvo': '908810',
    'Leche maternizada y alimentos para bebé': '908811',
    'Mayonesa y mostaza': '908812',
    'Moles y salsas': '908813',
    'Sopas instantáneas y puré de tomate': '908814',
    'Otros condimentos': '908815',
    'Jugos o néctares envasados': '908818',
    'Café soluble': '908820',
    'Café tostado': '908821',
    'Té': '908823',
    'Agua embotellada': '908825',
    'Refrescos envasados': '908827',
    'Bebidas energéticas': '908829',
    'Concentrados para refrescos': '908830',
    'Brandy': '908834',
    'Ron': '908835',
    'Tequila': '908836',
    'Otros licores': '908837',
    'Vino de mesa': '908839',
    'Cerveza': '908841',
    'Cigarrillos': '908844',
    'Blusas y playeras para mujer': '908848',
    'Calcetas, medias y pantimedias': '908849',
    'Calcetines y calcetas para hombre': '908850',
    'Calcetines y calcetas para niños': '908851',
    'Camisas y playeras para hombre': '908852',
    'Camisas y playeras para niños': '908853',
    'Pantalones para hombre': '908854',
    'Pantalones para mujer': '908855',
    'Pantalones para niño': '908856',
    'Ropa de abrigo': '908857',
    'Ropa interior para hombre': '908858',
    'Ropa interior para mujer': '908859',
    'Ropa interior para niños, niñas y adolescentes': '908860',
    'Ropa para bebés': '908861',
    'Traje para hombre': '908862',
    'Uniformes escolares': '908863',
    'Vestidos y faldas para mujer': '908864',
    'Vestidos, faldas y pantalones para niñas': '908865',
    'Otras prendas de vestir para hombre': '908866',
    'Otras prendas de vestir para mujer': '908867',
    'Complementos de vestir': '908869',
    'Servicio de lavandería': '908871',
    'Servicio de tintorería': '908872',
    'Sandalias y huaraches': '908875',
    'Zapatos para hombre': '908876',
    'Zapatos para mujer': '908877',
    'Zapatos para niños y niñas': '908878',
    'Zapatos tenis': '908879',
    'Renta de vivienda': '908883',
    'Vivienda propia': '908886',
    'Productos para reparación menor de la vivienda': '908889',
    'Servicios para el mantenimiento, reparación y seguridad de la vivienda': '908891',
    'Derechos por el suministro de agua': '908894',
    'Otros servicios relacionados con la vivienda': '908896',
    'Electricidad': '908899',
    'Gas doméstico LP': '908901',
    'Gas doméstico natural': '908902',
    'Colchones': '908906',
    'Comedores y antecomedores': '908907',
    'Muebles diversos para el hogar': '908908',
    'Muebles para cocina': '908909',
    'Recámaras': '908910',
    'Salas': '908911',
    'Colchas y cobijas': '908914',
    'Sábanas': '908915',
    'Toallas, cortinas y otros blancos': '908916',
    'Aparatos de aire acondicionado': '908919',
    'Aspiradoras y otros aparatos para el hogar': '908920',
    'Estufas': '908921',
    'Horno de microondas': '908922',
    'Lavadoras de ropa': '908923',
    'Refrigeradores': '908924',
    'Cafeteras, tostadoras, ventiladores y otros electrodomésticos pequeños': '908926',
    'Licuadoras': '908927',
    'Planchas eléctricas': '908928',
    'Artículos y utensilios para el hogar': '908931',
    'Baterías de cocina': '908932',
    'Loza, cristalería y cubiertos': '908933',
    'Utensilios de plástico para el hogar': '908934',
    'Focos': '908937',
    'Herramientas y equipo para el hogar': '908938',
    'Pilas': '908939',
    'Artículos desechables y no duraderos': '908942',
    'Blanqueadores': '908943',
    'Cerillos': '908944',
    'Desodorantes ambientales': '908945',
    'Detergentes': '908946',
    'Escobas, fibras y estropajos': '908947',
    'Jabón para lavar': '908948',
    'Plaguicidas': '908949',
    'Servilletas de papel': '908950',
    'Suavizantes y limpiadores': '908951',
    'Velas y veladoras': '908952',
    'Servicio doméstico': '908954',
    'Analgésicos': '908958',
    'Antibióticos': '908959',
    'Antigripales': '908960',
    'Antiinflamatorios': '908961',
    'Cardiovasculares': '908962',
    'Dermatológicos': '908963',
    'Expectorantes y descongestivos': '908964',
    'Gastrointestinales': '908965',
    'Medicamentos para alergias': '908966',
    'Medicamentos para diabetes': '908967',
    'Medicinas homeopáticas y naturistas': '908968',
    'Nutricionales': '908969',
    'Otros medicamentos': '908970',
    'Material de curación': '908972',
    'Lentes, aparatos para sordera y ortopédicos': '908974',
    'Consulta médica': '908977',
    'Consulta y prótesis dental': '908979',
    'Atención médica durante el parto': '908982',
    'Hospitalización general': '908983',
    'Hospitalización parto': '908984',
    'Operación quirúrgica': '908985',
    'Análisis clínicos': '908988',
    'Automóviles': '908992',
    'Motocicletas': '908994',
    'Bicicletas': '908996',
    'Acumuladores': '908999',
    'Neumáticos': '909000',
    'Partes, accesorios y otras refacciones para vehículos': '909001',
    'Aceites lubricantes': '909003',
    'Gasolina de alto octanaje': '909004',
    'Gasolina de bajo octanaje': '909005',
    'Lavado y engrasado de automóvil': '909007',
    'Mantenimiento de automóvil': '909008',
    'Reparación de automóvil': '909009',
    'Cuotas de autopistas': '909011',
    'Estacionamiento': '909012',
    'Trámites vehiculares': '909013',
    'Metro o transporte eléctrico': '909016',
    'Autobús foráneo': '909018',
    'Autobús urbano': '909019',
    'Colectivo': '909020',
    'Taxi': '909021',
    'Transporte escolar': '909022',
    'Transporte aéreo': '909024',
    'Equipo terminal de comunicación': '909028',
    'Computadoras': '909030',
    'Reproductores de audio y video, y sus accesorios': '909032',
    'Televisores': '909033',
    'Servicios de telefonía fija': '909036',
    'Servicio de telefonía móvil': '909038',
    'Servicio de internet': '909040',
    'Paquetes de internet, telefonía y televisión de paga': '909042',
    'Servicio de televisión de paga': '909044',
    'Streaming de películas y música': '909045',
    'Material y aparatos fotográficos': '909049',
    'Consolas, discos y descargas de videojuegos': '909052',
    'Juguetes y juegos de mesa': '909053',
    'Artículos deportivos': '909055',
    'Plantas y flores': '909058',
    'Alimento para mascotas': '909060',
    'Servicios para mascotas': '909063',
    'Club deportivo': '909065',
    'Servicios recreativos y centros nocturnos': '909066',
    'Instrumentos musicales y descargas de audio y video': '909069',
    'Cine': '909072',
    'Museos y sitios culturales': '909074',
    'Paquetes para fiesta': '909076',
    'Libros de texto': '909079',
    'Otros libros': '909080',
    'Periódicos y revistas': '909082',
    'Material escolar': '909084',
    'Servicios turísticos en paquete': '909087',
    'Preescolar': '909091',
    'Primaria': '909092',
    'Secundaria': '909095',
    'Preparatoria': '909098',
    'Universidad': '909101',
    'Carrera corta': '909104',
    'Enseñanza adicional': '909105',
    'Barbacoa o birria': '909109',
    'Carnitas': '909110',
    'Loncherías, fondas, torterías y taquerías': '909111',
    'Pizzas': '909112',
    'Pollos rostizados': '909113',
    'Restaurantes y similares': '909114',
    'Otros alimentos cocinados': '909115',
    'Hoteles': '909118',
    'Seguro de automóvil': '909122',
    'Aparatos eléctricos para el cuidado personal': '909126',
    'Artículos de maquillaje': '909128',
    'Crema y productos para higiene dental': '909129',
    'Cremas para la piel': '909130',
    'Desodorantes personales': '909131',
    'Jabón de tocador': '909132',
    'Lociones y perfumes': '909133',
    'Navajas y máquinas de afeitar': '909134',
    'Pañales': '909135',
    'Papel higiénico y pañuelos desechables': '909136',
    'Productos para el cabello': '909137',
    'Toallas sanitarias': '909138',
    'Otros artículos de tocador': '909139',
    'Corte de cabello': '909141',
    'Sala de belleza y masajes': '909142',
    'Relojes, joyas y bisutería': '909145',
    'Bolsas y mochilas': '909147',
    'Guarderías y estancias infantiles': '909150',
    'Expedición de documentos del sector público': '909153',
    'Servicios funerarios': '909154',
    'Servicios profesionales': '909155'
}

MESES = {
    'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12
}

def parse_inegi_date(date_str):
    if not date_str or str(date_str).strip() == '':
        return None
    raw = str(date_str).strip().lower()

    # 1. Formato numérico YYYY-MM o YYYY/MM
    m_num = re.search(r'\b(\d{4})[-/](\d{1,2})\b', raw)
    if m_num:
        return f"{m_num.group(1)}-{int(m_num.group(2)):02d}-01"

    # 2. Reemplazo de signos (en-dash, puntos, diagonales) por espacio
    s = re.sub(r'[^a-z0-9]', ' ', raw)

    for mes_abbr, mes_num in MESES.items():
        if re.search(r'\b' + mes_abbr, s):
            # Año de 4 dígitos
            m4 = re.search(r'\b(19\d\d|20\d\d)\b', s)
            if m4:
                return f"{m4.group(1)}-{mes_num:02d}-01"
            # Año de 2 dígitos (ej. ene-22 -> 2022)
            m2 = re.search(r'\b(\d{2})\b', s)
            if m2:
                yr = int(m2.group(1))
                yr += 2000 if yr <= 50 else 1900
                return f"{yr:04d}-{mes_num:02d}-01"

    return None

id_a_concepto = {v: k for k, v in ccif_diccionario.items()}

# 2. Petición POST a Exportacion.aspx
url = "https://www.inegi.org.mx/app/indicesdepreciosv2/Exportacion.aspx"
series_str = "e|" + ",".join(ccif_diccionario.values())

payload = {
    '_series': series_str,
    '_formato': 'IQY',
    '_orient': 'horizontal',
    '_anioI': '2000',
    '_anioF': '2026',
    '_meta': '0',
    '_tipo': 'Tipo de información',
    '_info': 'Tipo de información',
    'st': '',
    'idEstructura': '112001700080'
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
    'Referer': 'https://www.inegi.org.mx/app/indicesdepreciosv2/'
}

print("Enviando petición POST a Exportacion.aspx...")
response = requests.post(url, data=payload, headers=headers, timeout=60)
response.raise_for_status()
response.encoding = 'utf-8-sig' if 'utf-8' in response.text[:250].lower() else 'latin-1'

# 3. Localizar la tabla de datos y extraer la cabecera real
tables = pd.read_html(io.StringIO(response.text))
if not tables:
    raise SystemExit("El servidor no devolvió tablas HTML.")

df_data = None

for t in tables:
    # Opción A: los encabezados ya están en t.columns
    cols_lower = [str(c).strip().lower() for c in t.columns]
    if 'serie' in cols_lower and any('título' in c or 'titulo' in c for c in cols_lower):
        df_data = t.copy()
        break
    # Opción B: los encabezados están en alguna fila interna
    for idx, row in t.iterrows():
        vals = [str(x).strip().lower() for x in row.values]
        if 'serie' in vals and any('título' in v or 'titulo' in v for v in vals):
            df_data = t.iloc[idx + 1:].copy()
            df_data.columns = [str(c).strip() for c in t.iloc[idx].values]
            break
    if df_data is not None:
        break

if df_data is None:
    raise SystemExit("No se encontró la fila con 'Título' y 'Serie' en la respuesta.")

# 4. Identificar columnas clave y columnas de fecha
serie_col = next(c for c in df_data.columns if str(c).strip().lower() == 'serie')
titulo_col = next((c for c in df_data.columns if any(kw in str(c).strip().lower() for kw in ['título', 'titulo'])), None)

# Se buscan columnas que sean fechas; si no, se toman todas las columnas posteriores a Título y Serie
date_cols = [c for c in df_data.columns if parse_inegi_date(c) is not None]
if not date_cols:
    date_cols = [c for c in df_data.columns if c not in [serie_col, titulo_col]]

print(f"Columnas de fechas detectadas: {len(date_cols)} (primeras: {date_cols[:3]}, últimas: {date_cols[-3:]})")

# 5. Despivote (melt)
id_vars = [c for c in [serie_col, titulo_col] if c is not None]

df_melted = df_data.melt(
    id_vars=id_vars,
    value_vars=date_cols,
    var_name='Fecha_Raw',
    value_name='Indice_Raw'
)

# 6. Limpieza y tipado
df_melted['ID_API'] = df_melted[serie_col].astype(str).str.extract(r'(\d{6})')[0]
df_melted['Fecha'] = pd.to_datetime(df_melted['Fecha_Raw'].apply(parse_inegi_date), errors='coerce')
df_melted['Indice'] = pd.to_numeric(
    df_melted['Indice_Raw'].astype(str).str.extract(r'(\d+(?:\.\d+)?)')[0],
    errors='coerce'
)

# Descartar renglones sin fecha o índice
df_clean = df_melted.dropna(subset=['ID_API', 'Fecha', 'Indice']).copy()

# Mapeo de conceptos
df_clean['Concepto'] = df_clean['ID_API'].map(id_a_concepto)
if titulo_col is not None:
    # Si la serie no estaba en el diccionario, rescata la descripción que viene en la columna Título
    df_clean['Concepto'] = df_clean['Concepto'].fillna(
        df_clean[titulo_col].astype(str).str.split(',').str[-1].str.strip()
    )

df_final = df_clean[['ID_API', 'Concepto', 'Fecha', 'Indice']].sort_values(by=['ID_API', 'Fecha']).reset_index(drop=True)

print(f"\nExtracción exitosa: {len(df_final):,} registros consolidados.")
print(df_final.head(10))

# 7. Guardar en Parquet
os.makedirs('data/intermediate', exist_ok=True)
df_final.to_parquet('data/intermediate/ccif_historico.parquet', index=False)
df_final.to_csv('data/intermediate/ccif_historico.csv', index=False)
print("Archivo guardado correctamente en 'data/intermediate/ccif_historico.parquet'.")