document.getElementById("loginForm")?.addEventListener("submit", (e) => {
  e.preventDefault();

  const email = email.value;
  const password = password.value;

  if (email && password) {
    localStorage.setItem("loggedIn", "true");
    window.location.href = "home.html";
  } else {
    document.getElementById("authMessage").textContent =
      "Invalid login credentials";
  }
});

function logout() {
  localStorage.removeItem("loggedIn");
  window.location.href = "index.html";
}
