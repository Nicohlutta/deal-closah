let currentCompany = "";
let currentSlides = [];

const form = document.getElementById("deckForm");
const slides = document.getElementById("slides");
const log = document.getElementById("log");
const message = document.getElementById("message");

function values() {
  return Object.fromEntries(new FormData(form).entries());
}

async function post(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await response.text());
  return response;
}

function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function addMsg(kind, text) {
  const node = document.createElement("div");
  node.className = `msg ${kind}`;
  node.textContent = text;
  log.appendChild(node);
  log.scrollTop = log.scrollHeight;
}

function render(deck) {
  currentCompany = deck.company_name;
  currentSlides = deck.slides || [];
  document.getElementById("deckTitle").textContent = `${currentCompany} pitch deck`;
  document.getElementById("meta").textContent = `${currentSlides.length} slides | saved to data/decks`;
  slides.innerHTML = currentSlides.map((slide) => {
    const needs = slide.needs_input?.length
      ? `<div class="needs">Needs input: ${esc(slide.needs_input.join(", "))}</div>`
      : "";
    return `
      <article class="slide">
        <div class="num">SLIDE ${esc(slide.slide)}</div>
        <h3>${esc(slide.title)}</h3>
        <div class="content">${esc(slide.content)}</div>
        <div class="notes">${esc(slide.speaker_notes || "")}${needs}</div>
      </article>
    `;
  }).join("");
}

async function generate() {
  const response = await post("/api/deck", values());
  const deck = await response.json();
  render(deck);
  addMsg("agent", "Generated and saved a 7-slide deck. Send edits here, then download the updated PPTX.");
}

async function sendEdit() {
  const text = message.value.trim();
  if (!text) return;
  if (!currentCompany) await generate();
  addMsg("user", text);
  message.value = "";
  const response = await post("/api/chat", { company_name: currentCompany, message: text });
  const payload = await response.json();
  render(payload.deck);
  addMsg("agent", payload.reply);
}

async function downloadPptx() {
  if (!currentCompany) await generate();
  const response = await post("/api/export", { company_name: currentCompany });
  const blob = await response.blob();
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${currentCompany.toLowerCase().replaceAll(" ", "_")}_pitch_deck.pptx`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(link.href);
}

document.getElementById("generate").addEventListener("click", generate);
document.getElementById("send").addEventListener("click", sendEdit);
document.getElementById("pptx").addEventListener("click", downloadPptx);
document.getElementById("clear").addEventListener("click", () => { log.innerHTML = ""; });
message.addEventListener("keydown", (event) => {
  if (event.key === "Enter") sendEdit();
});

generate();
