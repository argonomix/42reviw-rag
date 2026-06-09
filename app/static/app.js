const form = document.querySelector("#query-form");
const ingestButton = document.querySelector("#ingest");
const answer = document.querySelector("#answer");
const chunks = document.querySelector("#chunks");
const confidence = document.querySelector("#confidence");
const latency = document.querySelector("#latency");

function filters() {
  const project = document.querySelector("#project").value;
  const passed = document.querySelector("#passed").value;
  return {
    project_name: project || null,
    campus: "42tokyo",
    language: "ja",
    passed: passed === "" ? null : passed === "true",
  };
}

function renderChunks(items) {
  chunks.innerHTML = "";
  for (const item of items) {
    const node = document.createElement("article");
    node.className = "chunk";
    node.innerHTML = `
      <div class="chunk-meta">
        <span>${item.project_name}</span>
        <span>${item.topic_label || "general"}</span>
        <span>score: ${item.score ?? "-"}</span>
        <span>passed: ${item.passed}</span>
        <span>sim: ${item.similarity}</span>
      </div>
      <p>${item.text}</p>
    `;
    chunks.appendChild(node);
  }
}

ingestButton.addEventListener("click", async () => {
  answer.textContent = "Seed data を取り込んでいます...";
  const response = await fetch("/ingest", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reset: true }),
  });
  const data = await response.json();
  answer.textContent = `取り込み完了: reviews=${data.reviews}, chunks=${data.chunks}`;
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  answer.textContent = "検索しています...";
  chunks.innerHTML = "";
  const response = await fetch("/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query: document.querySelector("#query").value,
      filters: filters(),
      top_k: Number(document.querySelector("#top-k").value),
    }),
  });
  const data = await response.json();
  answer.textContent = data.answer || JSON.stringify(data, null, 2);
  confidence.textContent = `confidence: ${data.confidence ?? "-"}`;
  latency.textContent = `latency: ${data.latency_ms ?? "-"}ms`;
  renderChunks(data.retrieved_chunks || []);
});
