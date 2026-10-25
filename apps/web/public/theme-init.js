// Applies the saved theme before first paint to avoid a flash (kept external for the CSP).
try {
  var prefs = JSON.parse(localStorage.getItem("caneca-prefs") || "{}").state || {};
  var theme = prefs.theme === "light" || prefs.theme === "dark"
    ? prefs.theme
    : (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  document.documentElement.dataset.theme = theme;
  if (prefs.fontScale) document.documentElement.style.setProperty("--font-scale", String(prefs.fontScale));
} catch (e) {
  /* storage unavailable: defaults apply */
}
