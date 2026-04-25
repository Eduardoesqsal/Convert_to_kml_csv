#!/usr/bin/env python3
"""Convierte polígonos KML dentro de un ZIP a un CSV con áreas.

Uso:
  python kml_zip_to_csv.py --zip archivo.zip --out salida.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

try:
    from pyproj import Geod
except ImportError as exc:
    raise SystemExit(
        "Falta dependencia 'pyproj'. Instala con: pip install pyproj"
    ) from exc

# Geodésica elipsoidal WGS84 (alineada con mediciones d Google Earth)
WGS84_GEOD = Geod(ellps="WGS84")


def parse_coordinates(coord_text: str) -> list[tuple[float, float]]:
    """Parsea texto KML de coordenadas a lista de pares (lon, lat)."""
    points: list[tuple[float, float]] = []
    if not coord_text:
        return points

    tokens = re.split(r"\s+", coord_text.strip())
    for token in tokens:
        if not token:
            continue
        parts = token.split(",")
        if len(parts) < 2:
            continue
        lon = float(parts[0])
        lat = float(parts[1])
        points.append((lon, lat))

    if len(points) > 2 and points[0] != points[-1]:
        points.append(points[0])
    return points


def ring_area_geodesic(points: list[tuple[float, float]]) -> float:
    """Área geodésica de un anillo en WGS84 (m²)."""
    if len(points) < 4:
        return 0.0

    lons = [p[0] for p in points]
    lats = [p[1] for p in points]
    area_m2, _ = WGS84_GEOD.polygon_area_perimeter(lons, lats)
    return abs(area_m2)


def text_of(elem: ET.Element | None) -> str:
    if elem is None or elem.text is None:
        return ""
    return elem.text.strip()


def polygon_area_from_element(polygon_elem: ET.Element) -> float:
    outer_coords_elem = polygon_elem.find("./{*}outerBoundaryIs/{*}LinearRing/{*}coordinates")
    outer = parse_coordinates(text_of(outer_coords_elem))
    area = ring_area_geodesic(outer)

    for inner_coords_elem in polygon_elem.findall("./{*}innerBoundaryIs/{*}LinearRing/{*}coordinates"):
        inner = parse_coordinates(text_of(inner_coords_elem))
        area -= ring_area_geodesic(inner)

    return max(area, 0.0)


def extract_polygons_from_kml(kml_bytes: bytes, source_name: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    root = ET.fromstring(kml_bytes)
    kml_stem = Path(source_name).stem

    placemarks = root.findall(".//{*}Placemark")
    if not placemarks:
        # Fallback: buscar polígonos globales sin placemark
        polygons = root.findall(".//{*}Polygon")
        for i, poly in enumerate(polygons, start=1):
            area_m2 = polygon_area_from_element(poly)
            rows.append(
                {
                    "nombre": kml_stem if len(polygons) == 1 else f"{kml_stem}_polygon_{i}",
                    "kml": source_name,
                    "area_m2": area_m2,
                }
            )
        return rows

    for p_idx, placemark in enumerate(placemarks, start=1):
        polygons = placemark.findall(".//{*}Polygon")
        for poly_idx, poly in enumerate(polygons, start=1):
            area_m2 = polygon_area_from_element(poly)
            if len(polygons) == 1 and len(placemarks) == 1:
                name = kml_stem
            else:
                name = f"{kml_stem}_placemark_{p_idx}_polygon_{poly_idx}"

            rows.append(
                {
                    "nombre": name,
                    "kml": source_name,
                    "area_m2": area_m2,
                }
            )
    return rows


def process_zip(zip_path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        kml_files = [n for n in zf.namelist() if n.lower().endswith(".kml")]
        for kml_name in kml_files:
            data = zf.read(kml_name)
            rows.extend(extract_polygons_from_kml(data, kml_name))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Extrae áreas de polígonos KML dentro de ZIP y las exporta a CSV")
    parser.add_argument("--zip", dest="zip_file", required=False, help="Ruta del archivo ZIP")
    parser.add_argument("--out", dest="out_csv", required=False, help="Ruta del CSV de salida")
    args = parser.parse_args()

    zip_path: Path
    if args.zip_file:
        zip_path = Path(args.zip_file)
    else:
        cwd = Path.cwd()
        preferred = [
            cwd / "POLIGONOS_KML_RENOMBRADO.zip",
            cwd / "POLIGONOS_KML.zip",
        ]
        zip_path = next((p for p in preferred if p.exists()), None)  # type: ignore[assignment]
        if zip_path is None:
            zips = sorted(cwd.glob("*.zip"))
            if len(zips) == 1:
                zip_path = zips[0]
            elif len(zips) > 1:
                raise SystemExit(
                    "Hay varios ZIP en la carpeta. Usa --zip para indicar cuál procesar."
                )
            else:
                raise SystemExit(
                    "No se encontró ZIP en la carpeta actual. Usa --zip para indicar archivo."
                )

    if args.out_csv:
        out_path = Path(args.out_csv)
    else:
        out_path = Path(f"{zip_path.stem}_areas.csv")

    if not zip_path.exists():
        raise SystemExit(f"No existe el ZIP: {zip_path}")

    rows = process_zip(zip_path)

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["nombre", "area_ha"])
        writer.writeheader()
        for row in rows:
            area_m2 = float(row["area_m2"])
            writer.writerow(
                {
                    "nombre": row["nombre"],
                    "area_ha": f"{(area_m2 / 10000.0):.4f}",
                }
            )

    print(f"Polígonos procesados: {len(rows)}")
    print(f"CSV generado: {out_path.resolve()}")


if __name__ == "__main__":
    main()
