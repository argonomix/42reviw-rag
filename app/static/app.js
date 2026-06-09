const form = document.querySelector("#query-form");
const ingestButton = document.querySelector("#ingest");
const answer = document.querySelector("#answer");
const chunks = document.querySelector("#chunks");
const confidence = document.querySelector("#confidence");
const latency = document.querySelector("#latency");
const generateAnswer = document.querySelector("#generate-answer");

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
    const meta = document.createElement("div");
    meta.className = "chunk-meta";
    for (const value of [
      item.project_name,
      item.topic_label || "general",
      `score: ${item.score ?? "-"}`,
      `passed: ${item.passed}`,
      `sim: ${item.similarity}`,
      `source: ${item.retrieval_source ?? "-"}`,
    ]) {
      const span = document.createElement("span");
      span.textContent = value;
      meta.appendChild(span);
    }
    const text = document.createElement("p");
    text.textContent = item.text;
    node.append(meta, text);
    chunks.appendChild(node);
  }
}

function errorDetail(data) {
  if (Array.isArray(data.detail)) {
    return data.detail.map((item) => item.msg).join("\n");
  }
  return data.detail || "検索リクエストに失敗しました。";
}

function handleStreamEvent(data, shouldGenerateAnswer) {
  if (data.event === "retrieval") {
    renderChunks(data.retrieved_chunks || []);
    confidence.textContent = `confidence: ${data.confidence ?? "-"}`;
    latency.textContent = `retrieval: ${data.latency_ms ?? "-"}ms`;
    answer.textContent = shouldGenerateAnswer
      ? "検索結果を表示しました。推論中..."
      : "検索結果を表示しました。推論はオフです。";
    return;
  }

  if (data.event === "answer") {
    answer.textContent = data.answer || "回答を生成できませんでした。";
    confidence.textContent = `confidence: ${data.confidence ?? "-"}`;
    latency.textContent = `latency: ${data.latency_ms ?? "-"}ms`;
    return;
  }

  if (data.event === "error") {
    answer.textContent = data.detail || "検索または推論中にエラーが発生しました。";
  }
}

async function readQueryStream(response, shouldGenerateAnswer) {
  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("ストリームを読み取れませんでした。");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    for (const line of lines) {
      if (!line.trim()) {
        continue;
      }
      handleStreamEvent(JSON.parse(line), shouldGenerateAnswer);
    }
  }

  buffer += decoder.decode();
  if (buffer.trim()) {
    handleStreamEvent(JSON.parse(buffer), shouldGenerateAnswer);
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
  const query = document.querySelector("#query").value.trim();
  if (!query) {
    answer.textContent = "質問を入力してください。";
    confidence.textContent = "confidence: -";
    latency.textContent = "latency: -";
    chunks.innerHTML = "";
    return;
  }
  answer.textContent = "検索しています...";
  confidence.textContent = "confidence: -";
  latency.textContent = "latency: -";
  chunks.innerHTML = "";
  const shouldGenerateAnswer = generateAnswer.checked;
  try {
    const response = await fetch("/query/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        filters: filters(),
        top_k: Number(document.querySelector("#top-k").value),
        generate_answer: shouldGenerateAnswer,
      }),
    });

    if (!response.ok) {
      const data = await response.json();
      answer.textContent = errorDetail(data);
      confidence.textContent = "confidence: -";
      latency.textContent = "latency: -";
      renderChunks([]);
      return;
    }

    await readQueryStream(response, shouldGenerateAnswer);
  } catch (error) {
    answer.textContent =
      error instanceof Error ? error.message : "検索リクエストに失敗しました。";
    confidence.textContent = "confidence: -";
    latency.textContent = "latency: -";
    renderChunks([]);
  }
});
