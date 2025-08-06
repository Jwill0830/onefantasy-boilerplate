// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyC34zCeIFa2Ebe8TmVd_W0aXkGVfM-wQQg",
  authDomain: "onefantasy-app.firebaseapp.com",
  projectId: "onefantasy-app",
  storageBucket: "onefantasy-app.firebasestorage.app",
  messagingSenderId: "204749662769",
  appId: "1:204749662769:web:eddcb4e588a490f6db0310",
  measurementId: "G-6514QWJQMC"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);