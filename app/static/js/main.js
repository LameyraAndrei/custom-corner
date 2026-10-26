document.addEventListener("DOMContentLoaded", () => {
  // Auto-dismiss flash messages after a few seconds.
  document.querySelectorAll(".flash-msg").forEach((el, i) => {
    setTimeout(() => {
      el.style.transition = "opacity 0.4s ease, max-height 0.4s ease";
      el.style.opacity = "0";
      setTimeout(() => el.remove(), 400);
    }, 4500 + i * 300);
  });
});
