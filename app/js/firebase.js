// js/firebase.js
import { initializeApp } from "https://www.gstatic.com/firebasejs/12.8.0/firebase-app.js";
import {
  getAuth,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  onAuthStateChanged,
  sendEmailVerification,
  sendPasswordResetEmail,
  signOut
} from "https://www.gstatic.com/firebasejs/12.8.0/firebase-auth.js";

/* -------------------------------
   🔧 Firebase Config
---------------------------------*/
const firebaseConfig = {
  apiKey: "AIzaSyBDiTkeE5wCL6JDx_qK0KTdZQc-L654Bls",
  authDomain: "fantasy-tennis-58cad.firebaseapp.com",
  projectId: "fantasy-tennis-58cad",
  storageBucket: "fantasy-tennis-58cad.firebasestorage.app",
  messagingSenderId: "25807215246",
  appId: "1:25807215246:web:03772231bba376e07307df",
  measurementId: "G-L42KER0F02"
};

/* -------------------------------
   🔥 Initialize Firebase
---------------------------------*/
const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);

console.log("Current user on page load:", auth.currentUser);



/* -------------------------------
   DOM ELEMENTS
---------------------------------*/
const emailInput = document.getElementById("email");
const passwordInput = document.getElementById("password");
const loginForm = document.getElementById("loginForm");
const signupBtn = document.getElementById("signupBtn");
const resetBtn = document.getElementById("resetPassword");

/* -------------------------------
   LOGIN
---------------------------------*/
loginForm?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const email = emailInput.value.trim();
  const password = passwordInput.value;

  console.log("Login attempt started");
  console.log("Email:", email);
  console.log("Password length:", password.length);

  try {
    const cred = await signInWithEmailAndPassword(auth, email, password);

    console.log("Login promise resolved:", cred.user);

    // Reload user to get updated emailVerified
    //await cred.user.reload();

    //console.log("After reload, emailVerified:", cred.user.emailVerified);


    if (!cred.user.emailVerified) {
      alert("Please verify your email before logging in.");
      await signOut(auth);
      return;
    }
    console.log("✅ Login successful, redirecting to home.html");
    window.location.replace('home.html')
    // Redirect to home page
  } catch (err) {
    console.log(err.code);
    if (err.code === "auth/user-not-found") {
      alert("No account found. Please sign up.");
    } else if (err.code === "auth/wrong-password") {
      alert("Incorrect password.");
    } else {
      alert("Login error: " + err.message);
    }
  }
});

/* -------------------------------
   SIGNUP
---------------------------------*/
signupBtn?.addEventListener("click", async () => {
  const email = emailInput.value.trim();
  const password = passwordInput.value;

  if (!email || !password) {
    alert("Enter both email and password.");
    return;
  }

  if (password.length < 6) {
    alert("Password must be at least 6 characters.");
    return;
  }

  try {
    const cred = await createUserWithEmailAndPassword(auth, email, password);
    await sendEmailVerification(cred.user);

    alert("Account created! Verification email sent. Please verify before logging in.");
    await signOut(auth); // Prevent auto-login
  } catch (err) {
    if (err.code === "auth/email-already-in-use") {
      alert("Email already registered. Please log in.");
    } else if (err.code === "auth/invalid-email") {
      alert("Invalid email.");
    } else {
      alert("Signup error: " + err.message);
    }
  }
});

/* -------------------------------
   PASSWORD RESET
---------------------------------*/
resetBtn?.addEventListener("click", async () => {
  const email = emailInput.value.trim();
  if (!email) {
    alert("Enter your email first.");
    return;
  }

  try {
    await sendPasswordResetEmail(auth, email);
    alert("Password reset email sent.");
  } catch (err) {
    if (err.code === "auth/user-not-found") {
      alert("No account found with this email.");
    } else {
      alert("Password reset error: " + err.message);
    }
  }
});

/* -------------------------------
   AUTH GUARD (ALL PAGES)*/

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



/*
   LOGOUT FUNCTION
---------------------------------*/
window.logout = async () => {
  await signOut(auth);
  window.location.replace("index.html");
};
