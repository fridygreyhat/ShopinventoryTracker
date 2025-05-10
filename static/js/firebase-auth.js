// Firebase Authentication setup
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.0/firebase-app.js";
import { 
  getAuth, 
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  signOut
} from "https://www.gstatic.com/firebasejs/10.7.0/firebase-auth.js";

// Firebase configuration will be injected by the server
const firebaseConfig = {
  apiKey: FIREBASE_API_KEY,
  projectId: FIREBASE_PROJECT_ID,
  appId: FIREBASE_APP_ID,
  authDomain: `${FIREBASE_PROJECT_ID}.firebaseapp.com`,
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

// Login with email and password
export async function loginWithEmailPassword(email, password) {
  try {
    const userCredential = await signInWithEmailAndPassword(auth, email, password);
    const token = await userCredential.user.getIdToken();
    
    // Send token to server to create session
    const response = await fetch('/api/auth/session', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ idToken: token }),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to authenticate with server');
    }
    
    // Redirect to dashboard on success
    window.location.href = '/';
    return await response.json();
  } catch (error) {
    console.error('Login error:', error);
    throw error;
  }
}

// Register with email and password
export async function registerWithEmailPassword(email, password, userData) {
  try {
    const userCredential = await createUserWithEmailAndPassword(auth, email, password);
    const token = await userCredential.user.getIdToken();
    
    // Send token and user data to server
    const response = await fetch('/api/auth/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        idToken: token,
        ...userData
      }),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to register with server');
    }
    
    // Redirect to dashboard on success
    window.location.href = '/';
    return await response.json();
  } catch (error) {
    console.error('Registration error:', error);
    throw error;
  }
}

// Logout
export async function logoutUser() {
  try {
    await signOut(auth);
    
    // Clear session on server
    const response = await fetch('/logout', {
      method: 'GET',
    });
    
    if (!response.ok) {
      console.error('Error during server logout');
    }
    
    // Redirect to login page
    window.location.href = '/login';
  } catch (error) {
    console.error('Logout error:', error);
    throw error;
  }
}

// Check authentication state
export function checkAuthState(callback) {
  return onAuthStateChanged(auth, callback);
}