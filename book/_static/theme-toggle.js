if (!window.__compneuThemeToggleInitialized) {
  window.__compneuThemeToggleInitialized = true;

  document.addEventListener("DOMContentLoaded", () => {
  const root = document.documentElement;

  const setTheme = (theme) => {
    const normalizedTheme = theme === "dark" ? "dark" : "light";
    const nextLabel =
      normalizedTheme === "dark" ? "Switch to light mode" : "Switch to dark mode";

    root.dataset.mode = normalizedTheme;
    root.dataset.theme = normalizedTheme;
    localStorage.setItem("mode", normalizedTheme);
    localStorage.setItem("theme", normalizedTheme);

    document.querySelectorAll(".theme-toggle-button").forEach((button) => {
      button.setAttribute("title", nextLabel);
      button.setAttribute("aria-label", nextLabel);
    });
  };

  // Normalize any old three-state setting into an explicit light/dark choice.
  setTheme(localStorage.getItem("theme"));

  document.querySelectorAll(".theme-toggle-button").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();

      const currentTheme = root.dataset.theme === "dark" ? "dark" : "light";
      setTheme(currentTheme === "dark" ? "light" : "dark");
    });
  });
  });
}
