import os
from typing import List
import geopandas as gpd
import pandas as pd
import xml.etree.ElementTree as ET
from shapely.geometry import Polygon, MultiPolygon

def prefecture_directories():
    path = "./shape_org"
    entries = os.listdir(path)
    directories = [
        entry for entry in entries if os.path.isdir(os.path.join(path, entry))
    ]
    return directories

def find_shp_files(root_dir: str, keyword: str) -> List[str]:
    file_list = []
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".shp") and keyword in file:
                file_list.append(os.path.join(root, file))
    return file_list

def merge_shapefiles(
    file_list: List[str], encoding: str = "shift-jis"
) -> gpd.GeoDataFrame:
    gdfs = [gpd.read_file(file, encoding=encoding) for file in file_list]
    return pd.concat(gdfs, ignore_index=True)

def reduce_coordinate_precision(coords, precision):
    return [(round(x, precision), round(y, precision)) for x, y in coords]

def simplify_geometry(geom, tolerance):
    if geom.geom_type == 'Polygon':
        return Polygon(geom.exterior.simplify(tolerance))
    elif geom.geom_type == 'MultiPolygon':
        return MultiPolygon([Polygon(p.exterior.simplify(tolerance)) for p in geom.geoms])
    return geom

def create_kml_polygon(coordinates, name, description, style_url):
    placemark = ET.Element('Placemark')
    ET.SubElement(placemark, 'name').text = name
    ET.SubElement(placemark, 'description').text = description
    ET.SubElement(placemark, 'styleUrl').text = style_url
    
    polygon = ET.SubElement(placemark, 'Polygon')
    outer_boundary = ET.SubElement(polygon, 'outerBoundaryIs')
    linear_ring = ET.SubElement(outer_boundary, 'LinearRing')
    coords = ET.SubElement(linear_ring, 'coordinates')
    
    coord_str = ' '.join([f"{x},{y}" for x, y in coordinates])
    coords.text = coord_str
    
    return placemark

def create_style(style_id, color):
    style = ET.Element('Style', id=style_id)
    line_style = ET.SubElement(style, 'LineStyle')
    ET.SubElement(line_style, 'color').text = color
    ET.SubElement(line_style, 'width').text = '2'
    poly_style = ET.SubElement(style, 'PolyStyle')
    ET.SubElement(poly_style, 'fill').text = '0'  # 塗りつぶしなし
    ET.SubElement(poly_style, 'outline').text = '1'  # 輪郭線あり
    return style

def save_kml(gdf, output_dir, coordinate_precision=5, simplify_tolerance=0.00001):
    os.makedirs(output_dir, exist_ok=True)

    filename = "都市計画区域.kml"
    filepath = os.path.join(output_dir, filename)
    
    gdf_wgs84 = gdf.to_crs("EPSG:4326")
    
    kml = ET.Element('kml', xmlns="http://www.opengis.net/kml/2.2")
    document = ET.SubElement(kml, 'Document')
    
    style_id = 'style_urban_planning'
    color = 'ff404040'  # 濃いグレー
    document.append(create_style(style_id, color))
    
    for _, row in gdf_wgs84.iterrows():
        geom = simplify_geometry(row['geometry'], simplify_tolerance)
        name = "都市計画区域"
        description = f"<![CDATA[<h3>都市計画区域</h3><table border='1'><tr><th>属性</th><th>値</th></tr>"
        for col in gdf_wgs84.columns:
            if col != 'geometry':
                description += f"<tr><td>{col}</td><td>{row[col]}</td></tr>"
        description += "</table>]]>"
        
        style_url = f"#{style_id}"
        
        if geom.geom_type == 'Polygon':
            coords = reduce_coordinate_precision(list(geom.exterior.coords), coordinate_precision)
            placemark = create_kml_polygon(coords, name, description, style_url)
            document.append(placemark)
        elif geom.geom_type == 'MultiPolygon':
            for poly in geom.geoms:
                coords = reduce_coordinate_precision(list(poly.exterior.coords), coordinate_precision)
                placemark = create_kml_polygon(coords, name, description, style_url)
                document.append(placemark)
    
    tree = ET.ElementTree(kml)
    tree.write(filepath, encoding='utf-8', xml_declaration=True)
    
    print(f"保存完了: {filepath}")

def process_prefecture(prefecture: str):
    print(f"\n処理開始: {prefecture}")
    root_directory = f"./shape_org/{prefecture}"
    file_list = find_shp_files(root_directory, "_tokei")
    print(f"ファイル数: {len(file_list)}")

    if not file_list:
        print(f"警告: {prefecture} にshapeファイルが見つかりません。処理をスキップします。")
        return

    try:
        merged_gdf = merge_shapefiles(file_list)
        print(f"結合後のGeoDataFrameのレコード数: {len(merged_gdf)}")

        if merged_gdf.empty:
            print(f"警告: {prefecture} の結合されたGeoDataFrameが空です。処理をスキップします。")
            return

        output_directory = os.path.abspath(f"./kml_google_map/{prefecture}/01_都市計画区域")
        save_kml(merged_gdf, output_directory, coordinate_precision=7, simplify_tolerance=0.00001)

    except Exception as e:
        print(f"エラー: {prefecture} の処理中に例外が発生しました。")
        print(f"エラー詳細: {str(e)}")
        print("処理を次の都道府県に進めます。")

def main():
    prefectures = prefecture_directories()
    total_prefectures = len(prefectures)

    for i, prefecture in enumerate(prefectures, 1):
        print(f"\n都道府県 {i}/{total_prefectures} 処理中")
        process_prefecture(prefecture)

    print("\n全ての都道府県の処理が完了しました。")

if __name__ == "__main__":
    main()