const ratingButtons = [...document.querySelectorAll(".rating")];
const form = document.getElementById("feedbackForm");
const note = document.getElementById("formNote");
const message = document.getElementById("message");
const charCount = document.getElementById("charCount");
const cursorGlow = document.querySelector(".cursor-glow");
let selectedRating = 0;

ratingButtons.forEach((button) => {
  button.addEventListener("click", () => {
    selectedRating = Number(button.dataset.rating);
    ratingButtons.forEach((item) => {
      const active = item === button;
      item.classList.toggle("selected", active);
      item.setAttribute("aria-pressed", String(active));
    });
    note.textContent = "";
  });
});

message.addEventListener("input", () => {
  charCount.textContent = message.value.length;
});

window.addEventListener("pointermove", (event) => {
  if (!cursorGlow || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  cursorGlow.style.left = `${event.clientX}px`;
  cursorGlow.style.top = `${event.clientY}px`;
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!selectedRating) {
    note.textContent = "Choose a rating first so we know how your experience felt.";
    ratingButtons[0].focus();
    return;
  }
  if (!form.reportValidity()) return;

  const feedback = {
    rating: selectedRating,
    category: document.getElementById("category").value,
    message: message.value.trim(),
    email: document.getElementById("email").value.trim(),
    submittedAt: new Date().toISOString()
  };

  // Demo behavior: store feedback in this browser only.
  // Connect a backend or form service to receive submissions elsewhere.
  try {
    const saved = JSON.parse(localStorage.getItem("kindredFeedback") || "[]");
    saved.push(feedback);
    localStorage.setItem("kindredFeedback", JSON.stringify(saved));
    note.textContent = "Thank you for sharing your thoughts. Your feedback is saved in this browser ✳";
    form.reset();
    selectedRating = 0;
    ratingButtons.forEach((item) => {
      item.classList.remove("selected");
      item.setAttribute("aria-pressed", "false");
    });
    charCount.textContent = "0";
  } catch (error) {
    note.textContent = "Thanks for your feedback! To receive submissions, connect this form to a backend.";
  }
});
