# Convert_to_kml_csv
convertidor de zip kml a csv 
 README - kml_zip_to_csv.py

  Descripción general
  Este script toma un archivo ZIP que contiene uno o varios archivos KML, busca polígonos dentro de esos KML, calcula el
  área geodésica de cada polígono (sobre el elipsoide WGS84) y genera un CSV con:
  - nombre del polígono
  - área en hectáreas (area_ha)

  Archivo principal
  - kml_zip_to_csv.py

  Requisito
  - Python 3
  - Librería: pyproj

  Instalación de dependencia
  pip install pyproj

  Uso rápido
  1. Coloca el ZIP en la misma carpeta del script.
  2. Ejecuta:
  python kml_zip_to_csv.py
  3. Se generará un CSV con nombre:
  <nombre_del_zip>_areas.csv

  Uso con parámetros
  python kml_zip_to_csv.py --zip archivo.zip --out salida.csv

  Parámetros
  - --zip
    Ruta del ZIP a procesar.
  - --out
    Ruta/nombre del CSV de salida.

  Comportamiento si no pasas --zip
  El script intenta encontrar automáticamente el ZIP en este orden:
  1. POLIGONOS_KML_RENOMBRADO.zip
  2. POLIGONOS_KML.zip
  3. Si no existen, busca cualquier *.zip en la carpeta actual.
  4. Si hay más de un ZIP, se detiene y pide usar --zip.
  5. Si no hay ninguno, se detiene y avisa que no encontró ZIP.

  Estructura del CSV de salida
  Columnas:
  - nombre
  - area_ha

  Formato:
  - area_ha se escribe con 4 decimales.
  - Conversión usada: hectáreas = m² / 10000

  Flujo completo del script
  1. Lee argumentos de línea de comandos.
  2. Resuelve qué ZIP procesar.
  3. Abre el ZIP y localiza archivos .kml.
  4. Parsea XML de cada KML.
  5. Encuentra polígonos (dentro de Placemark o como fallback global).
  6. Calcula área geodésica por polígono:
     - suma anillo exterior
     - resta anillos interiores (huecos)
  7. Convierte m² a ha.
  8. Escribe CSV.
  9. Imprime cantidad de polígonos procesados y ruta final del CSV.

  Explicación de cada función

  1) parse_coordinates(coord_text: str) -> list[tuple[float, float]]
  Qué hace:
  - Convierte el texto de coordenadas KML en una lista de puntos (lon, lat).

  Detalle:
  - Separa por espacios/saltos de línea.
  - Cada token lo separa por coma.
  - Toma solo longitud y latitud (ignora altitud si existe).
  - Si el anillo no viene cerrado, lo cierra agregando el primer punto al final.

  Por qué es importante:
  - KML suele traer coordenadas como:
    lon,lat,alt lon,lat,alt ...
  - Para calcular área correctamente el anillo debe estar cerrado.

  2) ring_area_geodesic(points: list[tuple[float, float]]) -> float
  Qué hace:
  - Calcula área geodésica (m²) de un anillo en WGS84.

  Detalle:
  - Si hay menos de 4 puntos (anillo inválido), devuelve 0.0.
  - Usa pyproj.Geod.polygon_area_perimeter.
  - Devuelve valor absoluto del área.

  Por qué es importante:
  - El cálculo es geodésico (curvatura terrestre), no plano.
  - Es más adecuado para datos geográficos reales.

  3) text_of(elem: ET.Element | None) -> str
  Qué hace:
  - Devuelve texto limpio de un nodo XML.

  Detalle:
  - Si el nodo no existe o no tiene texto, devuelve cadena vacía.
  - Si existe, aplica strip().

  Por qué es importante:
  - Evita errores al leer etiquetas opcionales o vacías.

  4) polygon_area_from_element(polygon_elem: ET.Element) -> float
  Qué hace:
  - Calcula área total de un polígono KML considerando huecos internos.

  Detalle:
  - Busca outerBoundaryIs/LinearRing/coordinates (anillo exterior).
  - Calcula su área.
  - Busca todos los innerBoundaryIs (anillos interiores).
  - Resta cada área interior.
  - Devuelve max(area, 0.0) para evitar negativos por geometrías raras.

  Por qué es importante:
  - Un polígono con huecos debe descontar esos huecos del área final.

  5) extract_polygons_from_kml(kml_bytes: bytes, source_name: str) -> list[dict[str, object]]
  Qué hace:
  - Extrae todos los polígonos de un KML y arma filas intermedias con:
    nombre, kml, area_m2

  Detalle:
  - Parsea el XML desde bytes.
  - Busca Placemark.
  - Si no hay Placemark, usa fallback buscando Polygon global.
  - Para cada polígono calcula area_m2.
  - Genera nombres automáticos:
    - Si hay 1 placemark y 1 polígono: nombre = nombre base del archivo KML
    - En casos múltiples: nombre = <stem>_placemark_<i>_polygon_<j>
    - En fallback sin placemark múltiple: <stem>_polygon_<i>

  Por qué es importante:
  - Estandariza extracción y nomenclatura sin depender de nombres manuales.

  6) process_zip(zip_path: Path) -> list[dict[str, object]]
  Qué hace:
  - Recorre el ZIP completo y procesa todos los archivos .kml.

  Detalle:
  - Abre el ZIP en lectura.
  - Filtra nombres que terminen en .kml (case-insensitive).
  - Lee cada KML y acumula resultados de extract_polygons_from_kml.

  Por qué es importante:
  - Permite procesar lotes de KML en un solo paso.

  7) main() -> None
  Qué hace:
  - Orquesta todo el proceso de principio a fin.

  Detalle:
  - Lee argumentos --zip y --out.
  - Resuelve ZIP automático si no se pasó --zip.
  - Define CSV de salida automático si no se pasó --out.
  - Valida que el ZIP exista.
  - Ejecuta process_zip.
  - Escribe CSV con columnas finales:
    nombre, area_ha
  - Imprime resumen final por consola.

  Mensajes de error/validaciones importantes
  - Falta pyproj:
    "Falta dependencia 'pyproj'. Instala con: pip install pyproj"
  - No existe ZIP indicado.
  - Varios ZIP en la carpeta sin --zip (pide especificar).
  - Ningún ZIP encontrado en carpeta actual.

  Notas técnicas
  - Sistema geodésico: WGS84 (equivalente común en Google Earth/GPS).
  - Unidades internas de cálculo: m².
  - Unidades exportadas: hectáreas.
  - El script guarda también "kml" en datos intermedios, pero en el CSV final solo escribe "nombre" y "area_ha".

  Ejemplos de ejecución
  1) Automático:
  python kml_zip_to_csv.py

  2) ZIP específico:
  python kml_zip_to_csv.py --zip POLIGONOS_KML_RENOMBRADO.zip

  3) ZIP y salida personalizada:
  python kml_zip_to_csv.py --zip entrada.zip --out resultado.csv

  Salida esperada en consola (ejemplo)
  Polígonos procesados: 25
  CSV generado: C:\...\resultado.csv
