import os
from typing import List
import geopandas as gpd
import pandas as pd
import xml.etree.ElementTree as ET


def prefecture_directories():
    path = "./shape_org"
    # 指定されたパス内のすべてのエントリを取得
    entries = os.listdir(path)

    # フォルダのみをフィルタリング
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


def create_kml_polygon(coordinates, name, description, style_url):
    placemark = ET.Element("Placemark")
    ET.SubElement(placemark, "name").text = name
    ET.SubElement(placemark, "description").text = description
    ET.SubElement(placemark, "styleUrl").text = style_url

    polygon = ET.SubElement(placemark, "Polygon")
    outer_boundary = ET.SubElement(polygon, "outerBoundaryIs")
    linear_ring = ET.SubElement(outer_boundary, "LinearRing")
    coords = ET.SubElement(linear_ring, "coordinates")

    coord_str = " ".join([f"{x},{y},0" for x, y in coordinates])
    coords.text = coord_str

    return placemark


def create_style(style_id, color):
    style = ET.Element("Style", id=style_id)
    line_style = ET.SubElement(style, "LineStyle")
    ET.SubElement(line_style, "color").text = color
    ET.SubElement(line_style, "width").text = "2"
    poly_style = ET.SubElement(style, "PolyStyle")
    ET.SubElement(poly_style, "color").text = color.replace(
        "ff", "80"
    )  # 50% transparency
    return style


def split_gdf(gdf):
    # '区域区分'の一覧を取得
    list = gdf["区域区分"].unique()

    # 各区域区分ごとにGeoDataFrameを分割
    split_gdfs = {i: gdf[gdf["区域区分"] == i] for i in list}

    return split_gdfs


def save_split_gdfs_to_kml(split_gdfs, output_dir, coordinate_precision=6):
    print(f"開始: save_split_gdfs_to_kml, output_dir: {output_dir}")
    print(f"split_gdfs の数: {len(split_gdfs)}")

    os.makedirs(output_dir, exist_ok=True)

    total_gdfs = len(split_gdfs)
    for i, (kubun, gdf) in enumerate(split_gdfs.items(), 1):
        filename = f"{kubun.replace(' ', '_')}.kml"
        filepath = os.path.join(output_dir, filename)

        gdf_wgs84 = gdf.to_crs("EPSG:4326")

        kml = ET.Element("kml", xmlns="http://www.opengis.net/kml/2.2")
        document = ET.SubElement(kml, "Document")

        # スタイルの定義
        style_ids = {"市街化区域": "style_shigaika", "市街化調整区域": "style_chosei"}
        document.append(create_style(style_ids["市街化区域"], "ff0000ff"))  # 赤色
        document.append(create_style(style_ids["市街化調整区域"], "ff00ff00"))  # 緑色

        for _, row in gdf_wgs84.iterrows():
            geom = row["geometry"]
            kuiki_kubun = row["区域区分"]
            name = kuiki_kubun
            description = "<![CDATA["
            description += f"<h3>{kuiki_kubun}</h3>"
            description += "<table border='1'><tr><th>属性</th><th>値</th></tr>"
            for col in gdf_wgs84.columns:
                if col not in ["geometry", "区域区分"]:
                    description += f"<tr><td>{col}</td><td>{row[col]}</td></tr>"
            description += "</table>]]>"

            style_url = f"#{style_ids.get(kuiki_kubun, 'style_shigaika')}"

            if geom.geom_type == "Polygon":
                coords = reduce_coordinate_precision(
                    list(geom.exterior.coords), coordinate_precision
                )
                placemark = create_kml_polygon(coords, name, description, style_url)
                document.append(placemark)
            elif geom.geom_type == "MultiPolygon":
                for poly in geom.geoms:
                    coords = reduce_coordinate_precision(
                        list(poly.exterior.coords), coordinate_precision
                    )
                    placemark = create_kml_polygon(coords, name, description, style_url)
                    document.append(placemark)

        tree = ET.ElementTree(kml)
        tree.write(filepath, encoding="utf-8", xml_declaration=True)

        print(f"保存完了 ({i}/{total_gdfs}): {filepath}")

    print(f"\n全ての区域区分のKMLファイルが {output_dir} に保存されました。")


def process_prefecture(prefecture: str):
    print(f"\n処理開始: {prefecture}")
    root_directory = f"./shape_org/{prefecture}"
    file_list = find_shp_files(root_directory, "_senbiki")
    print(f"ファイル数: {len(file_list)}")

    if not file_list:
        print(
            f"警告: {prefecture} にshapeファイルが見つかりません。処理をスキップします。"
        )
        return

    try:
        merged_gdf = merge_shapefiles(file_list)
        print(f"結合後のGeoDataFrameのレコード数: {len(merged_gdf)}")

        if merged_gdf.empty:
            print(
                f"警告: {prefecture} の結合されたGeoDataFrameが空です。処理をスキップします。"
            )
            return

        split_gdfs = split_gdf(merged_gdf)
        print(f"分割後のGeoDataFrameの数: {len(split_gdfs)}")

        if not split_gdfs:
            print(
                f"警告: {prefecture} の分割後のGeoDataFrameが空です。処理をスキップします。"
            )
            return

        output_directory = os.path.abspath(f"./kml_google_map/{prefecture}/02_区域区分")
        save_split_gdfs_to_kml(split_gdfs, output_directory, coordinate_precision=7)

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
