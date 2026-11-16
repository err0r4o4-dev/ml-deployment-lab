"use strict";

const features = ["MedInc", "HouseAge", "AveRooms", "AveBedrms", "Population", "AveOccup", "Latitude", "Longitude"];
const sample = [8.3, 25, 6, 1, 1200, 3, 34.2, -118.3];
const form = document.getElementById("form");
const output = document.getElementById("output");
const predictButton = document.getElementById("predict");
const sampleButton = document.getElementById("sample");
let activeRequest = null;

function showOutput(message, state) {
  output.textContent = message;
  output.dataset.state = state;
  output.hidden = false;
}

function clearOutput() {
  if (activeRequest) activeRequest.abort();
  activeRequest = null;
  predictButton.disabled = false;
  predictButton.textContent = "Predict";
  form.removeAttribute("aria-busy");
  output.hidden = true;
  output.textContent = "";
}

sampleButton.addEventListener("click", () => {
  clearOutput();
  features.forEach((name, index) => { document.getElementById(name).value = sample[index]; });
});

form.addEventListener("reset", () => {
  clearOutput();
  features.forEach((name) => { document.getElementById(name).defaultValue = ""; });
});

form.addEventListener("input", clearOutput);

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!form.reportValidity()) return;
  clearOutput();
  const values = features.map((name) => Number(document.getElementById(name).value));
  if (!values.every(Number.isFinite)) {
    showOutput("Error: Enter a finite number for every field.", "error");
    return;
  }
  const controller = new AbortController();
  activeRequest = controller;
  const timeout = setTimeout(() => controller.abort(), 15000);
  predictButton.disabled = true;
  predictButton.textContent = "Predicting...";
  form.setAttribute("aria-busy", "true");
  showOutput("Calculating your prediction...", "loading");
  try {
    const response = await fetch("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ features: values }),
      signal: controller.signal,
    });
    const data = await response.json();
    if (activeRequest !== controller) return;
    if (!response.ok) throw new Error(data.error || "Prediction failed. Please try again.");
    if (typeof data.prediction !== "number" || !Number.isFinite(data.prediction)) {
      throw new Error("The server returned an invalid prediction. Please try again.");
    }
    const dollars = new Intl.NumberFormat("en-US", {
      style: "currency", currency: "USD", maximumFractionDigits: 0,
    }).format(data.prediction * 100000);
    showOutput(`Prediction: ${data.prediction.toFixed(3)} (units of $100,000)\nEstimated median house value: ${dollars}\nInputs: [${values.join(", ")}]`, "success");
  } catch (error) {
    if (activeRequest !== controller) return;
    const message = error.name === "AbortError"
      ? "Request timed out. Check that the server is running, then try again."
      : error instanceof TypeError
        ? "Cannot reach the server. Check your connection and try again."
        : error.message;
    showOutput(`Error: ${message}`, "error");
  } finally {
    clearTimeout(timeout);
    if (activeRequest === controller) {
      activeRequest = null;
      predictButton.disabled = false;
      predictButton.textContent = "Predict";
      form.removeAttribute("aria-busy");
    }
  }
});
