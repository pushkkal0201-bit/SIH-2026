(() => {
  "use strict";

  const body = document.body;
  const toggle = document.querySelector("[data-sidebar-toggle]");
  const sidebar = document.querySelector(".sidebar");

  if (toggle && sidebar) {
    toggle.addEventListener("click", () => {
      const open = body.classList.toggle("sidebar-open");

      toggle.setAttribute(
        "aria-expanded",
        open ? "true" : "false"
      );
    });

    document.addEventListener("click", (event) => {
      if (!body.classList.contains("sidebar-open")) {
        return;
      }

      if (
        sidebar.contains(event.target) ||
        toggle.contains(event.target)
      ) {
        return;
      }

      body.classList.remove("sidebar-open");

      toggle.setAttribute(
        "aria-expanded",
        "false"
      );
    });
  }



  const navButtons = [
    ...document.querySelectorAll(
      ".nav-item[data-scroll-target]"
    )
  ];


  navButtons.forEach((button) => {

    button.addEventListener("click", () => {

      const targetId =
        button.dataset.scrollTarget;


      const target =
        targetId
          ? document.getElementById(targetId)
          : null;



      if (target) {

        target.scrollIntoView({
          behavior: "smooth",
          block: "start"
        });

      }



      navButtons.forEach((item) => {

        item.classList.remove("active");

        item.removeAttribute(
          "aria-current"
        );

      });


      button.classList.add("active");

      button.setAttribute(
        "aria-current",
        "page"
      );



      if (window.innerWidth <= 820) {

        body.classList.remove(
          "sidebar-open"
        );

        toggle?.setAttribute(
          "aria-expanded",
          "false"
        );

      }

    });

  });

})();
