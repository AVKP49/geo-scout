"use strict";
const csrfToken = () => document.querySelector('meta[name="csrf-token"]').content;
async function postJSON(url, payload) {
  if (document.body.dataset.staticPreview === "true") {
    if (url !== "/api/v1/queries/suggest") throw new Error("Live scans are not available in this preview. Explore a sample report below.");
    const response = await fetch("/geo-scout/static/preview-questions.json");
    if (!response.ok) throw new Error("Could not load the preview questions. Please try again.");
    const config = await response.json(), category = config.categories[payload.category];
    if (!category) throw new Error("Choose a business category.");
    return {queries: (category.queries || config.default_queries).map(text => text.replace(/\{(city|business|service)\}/g, (_, key) => ({city: payload.city.trim(), business: payload.business_name.trim(), service: category.service})[key]))};
  }
  const response = await fetch(url, {method: "POST", headers: {"Content-Type": "application/json", "X-CSRFToken": csrfToken()}, body: JSON.stringify(payload)});
  let body;
  try { body = await response.json(); } catch { throw new Error("The request could not finish. Please try again."); }
  if (!response.ok) throw new Error(body.error?.message || "Please try again later.");
  return body.data;
}
const form = document.getElementById("scan-form");
if (form) {
  let step = 1;
  const maximum = Number(form.dataset.maxQueries), minimum = Number(form.dataset.minQueries);
  const list = document.getElementById("query-list");
  const error = document.getElementById("form-error");
  function relabel() {
    list.querySelectorAll(".query-item").forEach((row, index) => {
      const input = row.querySelector("input"), label = row.querySelector("label");
      input.id = "query-" + index; label.htmlFor = input.id; label.textContent = "Question " + (index + 1);
    });
    document.getElementById("add-query").hidden = list.children.length >= maximum;
  }
  function addQuery(text = "") {
    if (list.children.length >= maximum) return;
    const row = document.createElement("div"); row.className = "query-item";
    const label = document.createElement("label"), input = document.createElement("input"), remove = document.createElement("button");
    input.value = text; input.required = true; input.maxLength = 200; input.name = "query";
    remove.type = "button"; remove.className = "remove-query"; remove.textContent = "×"; remove.setAttribute("aria-label", "Remove question");
    remove.addEventListener("click", () => {row.remove(); relabel();});
    row.append(label, input, remove); list.append(row); relabel();
  }
  document.getElementById("add-query").addEventListener("click", () => {addQuery(); list.lastElementChild?.querySelector("input").focus();});
  document.getElementById("back-button").addEventListener("click", () => {
    step = 1; document.getElementById("business-fields").hidden = false; document.getElementById("query-fields").hidden = true;
    document.getElementById("step-label").textContent = "01 / 02"; list.replaceChildren(); document.getElementById("business_name").focus();
  });
  form.addEventListener("submit", async event => {
    event.preventDefault(); error.hidden = true;
    const button = document.getElementById(step === 1 ? "suggest-button" : "start-button");
    const original = button.textContent; button.disabled = true; button.textContent = step === 1 ? "Preparing questions…" : "Starting your scan…";
    try {
      const payload = Object.fromEntries(new FormData(form));
      if (step === 1) {
        const data = await postJSON("/api/v1/queries/suggest", payload);
        list.replaceChildren(); data.queries.forEach(addQuery); step = 2;
        document.getElementById("business-fields").hidden = true; document.getElementById("query-fields").hidden = false;
        document.getElementById("step-label").textContent = "02 / 02"; list.querySelector("input").focus();
      } else {
        payload.queries = [...list.querySelectorAll("input")].map(input => input.value.trim());
        if (payload.queries.length < minimum) throw new Error(`Keep at least ${minimum} questions.`);
        if (document.body.dataset.staticPreview === "true") {
          const kind = ({plumber: "plumber", food_blog: "food"})[payload.category] || "hvac";
          window.location.assign("/geo-scout/sample/" + kind + "/");
          return;
        }
        payload.captcha = payload["cf-turnstile-response"] || "";
        const data = await postJSON("/api/v1/free-scans", payload); window.location.assign(data.status_url);
      }
    } catch (failure) {error.textContent = failure.message; error.hidden = false;} finally {button.disabled = false; button.textContent = original;}
  });
}
const emailForm = document.getElementById("email-form");
if (emailForm) emailForm.addEventListener("submit", async event => {
  event.preventDefault(); const button = emailForm.querySelector("button"), message = document.getElementById("email-message"); button.disabled = true;
  try {const data = await postJSON(emailForm.action, {email: document.getElementById("email").value, consent: document.getElementById("consent").checked}); message.textContent = data.message;}
  catch (error) {message.textContent = error.message; button.disabled = false;}
});
document.getElementById("copy-link")?.addEventListener("click", async event => {
  try {await navigator.clipboard.writeText(window.location.href); event.currentTarget.textContent = "Link copied ✓";}
  catch {event.currentTarget.textContent = "Copy this page’s address to share";}
});
document.body.addEventListener("htmx:afterSwap", event => {
  const progress = document.getElementById("scan-progress");
  if (progress?.dataset.reportUrl) window.location.assign(progress.dataset.reportUrl);
});
