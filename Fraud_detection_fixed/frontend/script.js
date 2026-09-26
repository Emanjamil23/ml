// ============================================================
// Fraud Detection Frontend Logic
// ============================================================

// 1. API endpoint URL deployed on Vercel
const API_URL = "https://fraud-detection-api-jade.vercel.app/predict";
const LOCAL_API_URL = "http://127.0.0.1:8000/predict";

// 2. Get references to HTML elements
const form = document.getElementById("fraudForm");
const submitBtn = document.getElementById("submitBtn");
const resultBox = document.getElementById("resultBox");

// 3. Listen for form submission
form.addEventListener("submit", async function (event) {
  // Prevent the default page reload
  event.preventDefault();

  // Disable button and show loading state
  submitBtn.disabled = true;
  resultBox.className = "result-box checking";
  resultBox.textContent = "Checking...";
  resultBox.classList.remove("hidden");

  // 4. Collect values from form inputs into a JavaScript object
  const transactionData = {
    step: parseInt(document.getElementById("step").value, 10),
    type: document.getElementById("type").value,
    amount: parseFloat(document.getElementById("amount").value),
    oldbalanceOrg: parseFloat(document.getElementById("oldbalanceOrg").value),
    newbalanceOrig: parseFloat(document.getElementById("newbalanceOrig").value),
    oldbalanceDest: parseFloat(document.getElementById("oldbalanceDest").value),
    newbalanceDest: parseFloat(document.getElementById("newbalanceDest").value)
  };

  try {
    // 5. Send POST request to FastAPI backend using fetch()
    let response;
    try {
      response = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(transactionData)
      });
    } catch (networkError) {
      // Fallback to local server if remote Vercel API is unreachable or CORS blocked
      response = await fetch(LOCAL_API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(transactionData)
      });
    }

    // Check if the server responded with an error HTTP status
    if (!response || !response.ok) {
      throw new Error(`Server returned status: ${response ? response.status : 'offline'}`);
    }

    // 6. Parse JSON response from backend
    const data = await response.json();

    // 7. Display prediction result based on response
    if (data.prediction === 1 || data.result === "Fraudulent Transaction") {
      resultBox.className = "result-box fraudulent";
      resultBox.textContent = "Fraudulent Transaction";
    } else {
      resultBox.className = "result-box legitimate";
      resultBox.textContent = "Legitimate Transaction";
    }
  } catch (error) {
    // Handle network or server errors
    resultBox.className = "result-box error";
    resultBox.textContent = "Error: Could not check transaction. Please try again.";
    console.error("Error communicating with API:", error);
  } finally {
    // Re-enable the submit button
    submitBtn.disabled = false;
  }
});
