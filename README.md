# 地震報告查詢

Demo: <https://aiot-lecture13-bnj7hegwetff8y7k99vxa5.streamlit.app/>

本專案示範如何使用中央氣象署地震開放資料，取得最近數筆地震報告，並用 **Streamlit**（以及原本的 Node.js + 前端網頁）進行展示。

資料來源分為兩種模式：

- 有提供 API Token：呼叫氣象署 OpenData API 取得 **最近 10 筆** 地震報告。
- 未提供 API Token：改用專案內的 `sample_data.json`，展示 **最近 5 筆** 範例資料。

使用者可以從地震編號列表中選擇一筆報告，查看：

- 報告圖片（`ReportImageURI`）
- 各縣市震度（不顯示測站資料）
- 震度列表會依震度大小排序（例如 4 級 > 3 級 > 2 級 > 1 級，震度相同時再依縣市名稱排序）

---

## 1. 專案結構

主要檔案說明：

- `app.py`：Streamlit 版本地震報告展示主程式。
- `sample_data.json`：範例地震資料（結構與中央氣象署 API 回傳相同）。
- `.env`（選填）：可存放 `API_TOKEN`，供 Node 版本使用。
- `requirements.txt`：Streamlit 版本所需 Python 套件列表。

若使用原本 Node + 前端版本，還會用到：

- `server.js`：Node + Express 伺服器，提供 `/api/earthquakes`。
- `public/index.html`：前端 HTML 介面。
- `public/app.js`：前端 JS，向 `/api/earthquakes` 抓資料並渲染畫面。
- `public/styles.css`：前端樣式。

---

## 2. Streamlit 版本使用方式（推薦）

### 2.1 安裝環境

1. 建議建立虛擬環境（可略過）：

   ```bash
   python -m venv .venv
   source .venv/Scripts/activate  # Windows bash / Git Bash
   ```

2. 安裝依賴（需先建立 `requirements.txt`）：

   ```bash
   pip install -r requirements.txt
   ```

   建議的 `requirements.txt` 內容：

   ```txt
   streamlit
   requests
   ```

### 2.2 執行 Streamlit App

在專案根目錄（`app.py` 所在資料夾）執行：

```bash
streamlit run app.py
```

終端機會顯示一個網址（例如 `http://localhost:8501`），用瀏覽器打開即可。

### 2.3 操作說明

- 左側 Sidebar：
  - `API_TOKEN（留空則使用 sample_data.json）`：輸入中央氣象署 OpenData API Token。
    - 有輸入 → 使用 API，最多顯示 10 筆最新地震。
    - 留空 → 使用 `sample_data.json`，最多顯示 5 筆。
  - 「選擇地震報告」：列出可用的地震編號，格式為：
    - `EarthquakeNo｜M<規模>｜<發震時間>`

- 右側主畫面：
  - **基本資訊**：
    - 地震編號
    - 發震時間（`OriginTime`）
    - 規模（`MagnitudeType` + `MagnitudeValue`）
    - 報告文字內容（`ReportContent`）
  - **各縣市震度（依震度排序）**：
    - 僅顯示縣市層級資訊（`AreaDesc`, `CountyName`, `AreaIntensity`）。
    - 去除重複條目，依震度由大到小排序，同震度依縣市名稱排序。
  - **報告圖片**：
    - 若有 `ReportImageURI`，會顯示地震報告圖片。

---

## 3. Node + 前端版本（選用）

> 若只使用 Streamlit 版本，可略過本節。

### 3.1 安裝與執行

1. 建立環境檔（可選）：

   ```bash
   cp .env.example .env  # 或自行建立 .env
   ```

   `.env` 內容範例：

   ```dotenv
   API_TOKEN=你的_API_TOKEN
   PORT=3000
   ```

2. 安裝 Node 套件：

   ```bash
   npm install
   ```

3. 啟動伺服器：

   ```bash
   npm start
   # 或
   node server.js
   ```

4. 瀏覽器開啟：

   ```text
   http://localhost:3000
   ```

### 3.2 Node 版本行為摘要

- `GET /api/earthquakes`：
  - 有 `.env` 中的 `API_TOKEN`：
    - 呼叫 CWA API（limit=10），回傳最近 10 筆的簡化資料。
  - 無 `API_TOKEN`：
    - 讀取 `sample_data.json`，回傳最近 5 筆。
- 前端 `public/app.js`：
  - 向 `/api/earthquakes` 取得資料，列表列出地震編號。
  - 點擊後顯示 `ReportImageURI` 以及各縣市震度（不含測站資料）。

---

## 4. 資料來源與處理邏輯

- API 來源：

  ```text
  https://opendata.cwa.gov.tw/api/v1/rest/datastore/E-A0015-001
  ```

- 無論使用 API 或 `sample_data.json`，處理流程皆為：
  1. 取得原始 JSON。
  2. 從 `records.Earthquake` 取出多筆地震報告。
  3. 對每筆報告萃取：
     - `EarthquakeNo`
     - `ReportImageURI`
     - `ReportContent`
     - `EarthquakeInfo.OriginTime`
     - `EarthquakeInfo.EarthquakeMagnitude.MagnitudeType`
     - `EarthquakeInfo.EarthquakeMagnitude.MagnitudeValue`
     - `Intensity.ShakingArea` 中的 `AreaDesc`, `CountyName`, `AreaIntensity`
  4. 震度顯示時：
     - 去除重複的（`CountyName`, `AreaDesc`, `AreaIntensity`）組合。
     - 依 `AreaIntensity` 中的數字大小排序（例如從「4級」取出 4）。
     - 震度相同時，依縣市名稱排序。
