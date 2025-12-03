import dotenv from "dotenv";
import express from "express";
import fs from "fs";
import fetch from "node-fetch";
import path from "path";
import { fileURLToPath } from "url";

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.static(path.join(__dirname, "public")));

function mapApiToSimplified(apiJson, limitCount) {
  try {
    const earthquakes = apiJson?.records?.Earthquake || [];
    const sliced = earthquakes.slice(0, limitCount);
    return sliced.map((eq) => ({
      EarthquakeNo: eq.EarthquakeNo,
      ReportImageURI: eq.ReportImageURI,
      ReportContent: eq.ReportContent,
      OriginTime: eq.EarthquakeInfo?.OriginTime,
      MagnitudeValue: eq.EarthquakeInfo?.EarthquakeMagnitude?.MagnitudeValue,
      MagnitudeType: eq.EarthquakeInfo?.EarthquakeMagnitude?.MagnitudeType,
      IntensityAreas: (eq.Intensity?.ShakingArea || []).map((area) => ({
        AreaDesc: area.AreaDesc,
        CountyName: area.CountyName,
        AreaIntensity: area.AreaIntensity,
      })),
    }));
  } catch (e) {
    return [];
  }
}

app.get("/api/earthquakes", async (req, res) => {
  const token = process.env.API_TOKEN;
  const useApi = !!token;
  try {
    if (useApi) {
      const url = `https://opendata.cwa.gov.tw/api/v1/rest/datastore/E-A0015-001?Authorization=${token}&limit=10`;
      const r = await fetch(url);
      if (!r.ok) throw new Error(`CWA API error ${r.status}`);
      const apiJson = await r.json();
      const simplified = mapApiToSimplified(apiJson, 10);
      return res.json({
        source: "api",
        count: simplified.length,
        data: simplified,
      });
    }
    const samplePath = path.join(__dirname, "sample_data.json");
    let text = fs.readFileSync(samplePath, "utf-8");
    // 去掉檔案開頭可能存在的 UTF-8 BOM
    text = text.replace(/^\uFEFF/, "");
    const sampleJson = JSON.parse(text);
    const simplified = mapApiToSimplified(sampleJson, 5);
    return res.json({
      source: "sample",
      count: simplified.length,
      data: simplified,
    });
  } catch (err) {
    console.error("ERROR in /api/earthquakes:", err);
    res.status(500).json({
      error: "Failed to load earthquake data",
      message: err.message,
    });
  }
});

app.get("*", (req, res) => {
  res.sendFile(path.join(__dirname, "public", "index.html"));
});

app.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
});
