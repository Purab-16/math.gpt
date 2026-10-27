// Apply the saved theme before the page is drawn, so there is no flash of the wrong colors.
// Loaded in <head> as a separate file because the CSP blocks inline scripts.
(function () {
    try {
        const savedTheme = localStorage.getItem("theme");
        if (savedTheme === "light" || savedTheme === "dark") {
            document.documentElement.dataset.theme = savedTheme;
        }
    } catch (error) {
        // localStorage can be blocked (private mode). The system theme is used instead.
    }
})();
