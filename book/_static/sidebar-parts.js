if (!window.__compneuSidebarPartsInitialized) {
  window.__compneuSidebarPartsInitialized = true;

  document.addEventListener("DOMContentLoaded", () => {
    const storageKey = "compneu-sidebar-parts";
    let storedState = {};

    try {
      storedState = JSON.parse(localStorage.getItem(storageKey) || "{}");
    } catch {
      storedState = {};
    }

    const captions = document.querySelectorAll(".bd-sidebar-primary p.caption");

    captions.forEach((caption, index) => {
      const nav = caption.nextElementSibling;
      if (!nav || !nav.matches("ul.nav.bd-sidenav")) {
        return;
      }

      const label = caption.textContent.trim();
      const isActiveSection = !!nav.querySelector(".current, .active");
      const isOpen = Object.prototype.hasOwnProperty.call(storedState, label)
        ? Boolean(storedState[label])
        : isActiveSection;

      caption.classList.add("sidebar-part-caption");
      nav.classList.add("sidebar-part-nav");
      nav.hidden = !isOpen;

      const button = document.createElement("button");
      button.type = "button";
      button.className = "sidebar-part-toggle";
      button.setAttribute("aria-expanded", String(isOpen));
      button.setAttribute("aria-controls", `sidebar-part-${index}`);
      button.textContent = label;

      nav.id = `sidebar-part-${index}`;
      caption.replaceChildren(button);

      button.addEventListener("click", () => {
        const nextOpen = nav.hidden;
        nav.hidden = !nextOpen;
        button.setAttribute("aria-expanded", String(nextOpen));
        storedState[label] = nextOpen;
        localStorage.setItem(storageKey, JSON.stringify(storedState));
      });
    });
  });
}
