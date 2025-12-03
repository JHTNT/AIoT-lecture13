import json
import re
from pathlib import Path

import requests
import streamlit as st

API_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/E-A0015-001"


def load_from_api(api_token: str, limit: int = 10):
    params = {
        "Authorization": api_token,
        "limit": str(limit),
    }
    r = requests.get(API_URL, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def load_from_sample(limit: int = 5):
    sample_path = Path(__file__).parent / "sample_data.json"
    text = sample_path.read_text(encoding="utf-8")
    # 去掉可能的 BOM
    text = text.lstrip("\ufeff")
    data = json.loads(text)
    # 保險只取前 limit 筆
    data["records"]["Earthquake"] = data["records"]["Earthquake"][:limit]
    return data


def map_api_to_simplified(api_json, limit: int):
    earthquakes = api_json.get("records", {}).get("Earthquake", [])[:limit]
    simplified = []
    for eq in earthquakes:
        info = eq.get("EarthquakeInfo", {})
        mag = info.get("EarthquakeMagnitude", {})
        intensity = eq.get("Intensity", {}) or {}
        areas = intensity.get("ShakingArea", []) or []

        # 只保留縣市層級資訊，不含測站
        intensity_areas = []
        for area in areas:
            intensity_areas.append(
                {
                    "AreaDesc": area.get("AreaDesc"),
                    "CountyName": area.get("CountyName"),
                    "AreaIntensity": area.get("AreaIntensity"),
                }
            )

        simplified.append(
            {
                "EarthquakeNo": eq.get("EarthquakeNo"),
                "ReportImageURI": eq.get("ReportImageURI"),
                "ReportContent": eq.get("ReportContent"),
                "OriginTime": info.get("OriginTime"),
                "MagnitudeValue": mag.get("MagnitudeValue"),
                "MagnitudeType": mag.get("MagnitudeType"),
                "IntensityAreas": intensity_areas,
            }
        )
    return simplified


def sort_intensity_areas(areas):
    def level_num(s):
        if not s:
            return 0
        m = re.search(r"\d+", s)
        return int(m.group()) if m else 0

    # 先依震度由大到小，再依縣市名稱排序
    return sorted(
        areas,
        key=lambda a: (-level_num(a.get("AreaIntensity")), a.get("CountyName") or ""),
    )


def main():
    st.set_page_config(page_title="地震報告展示", layout="wide")
    st.title("地震報告展示（Streamlit）")

    st.sidebar.header("設定")
    api_token = st.sidebar.text_input(
        "API_TOKEN（留空則使用範例資料）",
        help="來自中央氣象署 OpenData 的 Token",
    )
    use_api = bool(api_token)

    limit_api = 10
    limit_sample = 5

    if st.sidebar.button("重新載入資料"):
        st.rerun()

    # 載入資料
    with st.spinner("載入資料中..."):
        try:
            if use_api:
                raw = load_from_api(api_token, limit=limit_api)
                data = map_api_to_simplified(raw, limit_api)
                source = f"中央氣象署 API（最多 {limit_api} 筆）"
            else:
                raw = load_from_sample(limit=limit_sample)
                data = map_api_to_simplified(raw, limit_sample)
                source = f"sample_data.json（最多 {limit_sample} 筆）"
        except Exception as e:
            st.error(f"載入資料失敗：{e}")
            return

    st.caption(f"資料來源：{source}")
    if not data:
        st.warning("沒有任何地震資料。")
        return

    # 左側選單：地震編號清單
    eq_options = {
        f"{item['EarthquakeNo']}｜M{item.get('MagnitudeValue', '?')}｜{item.get('OriginTime', '')}": idx
        for idx, item in enumerate(data)
    }
    selected_label = st.sidebar.radio("選擇地震報告", list(eq_options.keys()))
    selected_idx = eq_options[selected_label]
    item = data[selected_idx]

    # 右側顯示詳情
    col_info, col_img = st.columns([2, 3])

    with col_info:
        st.subheader("基本資訊")
        st.write(f"**地震編號：** {item['EarthquakeNo']}")
        st.write(f"**發震時間：** {item.get('OriginTime', '')}")
        st.write(f"**規模：** {item.get('MagnitudeType', '')} {item.get('MagnitudeValue', '')}")
        st.write(f"**內容摘要：** {item.get('ReportContent', '')}")

        st.subheader("各縣市震度（依震度排序）")
        areas = item.get("IntensityAreas") or []
        # 去重 + 排序
        unique = []
        seen = set()
        for a in areas:
            key = (
                (a.get("CountyName") or ""),
                (a.get("AreaDesc") or ""),
                (a.get("AreaIntensity") or ""),
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(a)

        unique_sorted = sort_intensity_areas(unique)

        if not unique_sorted:
            st.info("此筆資料無震度分布資訊。")
        else:
            for a in unique_sorted:
                st.markdown(
                    f"- **{a.get('CountyName','')}**｜{a.get('AreaDesc','')}｜震度：`{a.get('AreaIntensity','')}`"
                )

    with col_img:
        st.subheader("報告圖片")
        if item.get("ReportImageURI"):
            st.image(item["ReportImageURI"], caption="ReportImageURI", )
        else:
            st.info("此筆資料沒有 ReportImageURI。")


if __name__ == "__main__":
    main()
