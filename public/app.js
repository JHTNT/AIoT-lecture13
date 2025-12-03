async function loadData() {
  const res = await fetch("/api/earthquakes");
  if (!res.ok) throw new Error("API failed");
  const json = await res.json();
  return json;
}

function renderList(data) {
  const ul = document.getElementById("eqList");
  ul.innerHTML = "";
  data.forEach((item, idx) => {
    const li = document.createElement("li");
    li.textContent = `${item.EarthquakeNo}｜芮氏規模 ${
      item.MagnitudeValue ?? "?"
    }｜${item.OriginTime ?? ""}`;
    li.addEventListener("click", () => {
      document
        .querySelectorAll("#eqList li")
        .forEach((el) => el.classList.remove("active"));
      li.classList.add("active");
      renderDetail(item);
    });
    if (idx === 0) li.classList.add("active");
    ul.appendChild(li);
  });
  if (data.length > 0) renderDetail(data[0]);
}

function renderDetail(item) {
  const container = document.getElementById("eqDetail");
  const areas = item.IntensityAreas || [];
  const uniqueAreas = [];
  const seen = new Set();
  for (const a of areas) {
    const key = `${a.CountyName}-${a.AreaDesc}-${a.AreaIntensity}`;
    if (seen.has(key)) continue;
    seen.add(key);
    uniqueAreas.push(a);
  }

  container.innerHTML = `
    <div>
      <div><strong>地震編號：</strong>${item.EarthquakeNo}</div>
      <div><strong>發震時間：</strong>${item.OriginTime ?? ""}</div>
      <div><strong>內容摘要：</strong>${item.ReportContent ?? ""}</div>
      <div><strong>規模：</strong>${item.MagnitudeType ?? ""} ${
    item.MagnitudeValue ?? ""
  }</div>
    </div>
    ${
      item.ReportImageURI
        ? `<img alt="報告圖片" src="${item.ReportImageURI}" />`
        : ""
    }
    <div>
      <h3>各縣市震度</h3>
      <div class="intensity-grid">
        ${uniqueAreas
          .map(
            (a) => `
          <div class="intensity-item">
            <div class="county">${a.CountyName}</div>
            <div class="desc">${a.AreaDesc}</div>
            <div class="level">${a.AreaIntensity}</div>
          </div>
        `
          )
          .join("")}
      </div>
    </div>
  `;
}

(async () => {
  try {
    const { source, data } = await loadData();
    document.getElementById("sourceInfo").textContent =
      source === "api"
        ? "資料來源：中央氣象署 API（最近 10 筆）"
        : "資料來源：範例資料";
    renderList(data);
  } catch (e) {
    document.getElementById("eqDetail").textContent = "載入資料失敗";
    console.error(e);
  }
})();
