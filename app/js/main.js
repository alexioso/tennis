onAuthStateChanged(auth, async (user) => {
  const onLoginPage =
    location.pathname.endsWith("index.html") || location.pathname === "/";

  if (!user && !onLoginPage) {
    // Not logged in → redirect to login
    window.location.replace("index.html");
    return;
  }

  if (user && !user.emailVerified && !onLoginPage) {
    alert("Please verify your email.");
    await signOut(auth);
    window.location.replace("index.html");
  }

  // Optional: you can show user info here
  if (user && user.emailVerified && !onLoginPage) {
    console.log("Logged in user:", user.email);
  }
  console.log("Current user on Auth Guard:", auth.currentUser);

});
