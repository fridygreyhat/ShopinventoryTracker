/**
 * Firebase Authentication Module
 * This module provides functions for handling authentication with Firebase
 * Updated to use the modular API structure of Firebase Web SDK v9+
 */

// Import Firebase SDK modules as needed - these will be imported in the HTML file
// import { initializeApp } from 'firebase/app';
// import { getAuth, signInWithEmailAndPassword, createUserWithEmailAndPassword } from 'firebase/auth';

// Firebase configuration and instances will be provided from the login/register pages
let app;
let auth;

/**
 * Login with email and password
 * @param {Object} auth - Firebase Auth instance
 * @param {string} email - User email
 * @param {string} password - User password
 * @returns {Promise} Firebase user credential
 */
export async function loginWithEmailPassword(auth, email, password) {
    try {
        // Import directly to avoid naming conflict
        const { signInWithEmailAndPassword } = await import('https://www.gstatic.com/firebasejs/10.7.0/firebase-auth.js');
        
        // Use the auth instance passed from the login page
        const userCredential = await signInWithEmailAndPassword(auth, email, password);
        return userCredential;
    } catch (error) {
        console.error('Login error:', error);
        throw error;
    }
}

/**
 * Send password reset email
 * @param {Object} auth - Firebase Auth instance 
 * @param {string} email - User email
 * @returns {Promise} Promise that resolves when reset email is sent
 */
export async function sendPasswordReset(auth, email) {
    try {
        // Import directly to avoid naming conflict
        const { sendPasswordResetEmail } = await import('https://www.gstatic.com/firebasejs/10.7.0/firebase-auth.js');
        
        // Use the Firebase function with the auth instance passed from the login page
        await sendPasswordResetEmail(auth, email);
        return { success: true };
    } catch (error) {
        console.error('Password reset error:', error);
        throw error;
    }
}

/**
 * Register a new user with email and password
 * @param {Object} auth - Firebase Auth instance
 * @param {string} email - User email
 * @param {string} password - User password
 * @param {Object} userData - Additional user data
 * @returns {Promise} Firebase user credential and server response
 */
export async function registerWithEmailPassword(auth, email, password, userData) {
    try {
        // Import directly to avoid naming conflict
        const { createUserWithEmailAndPassword } = await import('https://www.gstatic.com/firebasejs/10.7.0/firebase-auth.js');
        
        // Create user in Firebase using the modular API
        const userCredential = await createUserWithEmailAndPassword(auth, email, password);
        const token = await userCredential.user.getIdToken();
        
        // Register user with server
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
        
        const serverData = await response.json();
        return { userCredential, serverData };
    } catch (error) {
        console.error('Registration error:', error);
        throw error;
    }
}

/**
 * Create a session with the server
 * @param {string} token - Firebase ID token
 * @param {boolean} remember - Whether to remember the user
 * @returns {Promise} Server response
 */
export async function createSession(token, remember = false) {
    try {
        const response = await fetch('/api/auth/session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                idToken: token,
                remember: remember
            }),
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to create session');
        }
        
        return await response.json();
    } catch (error) {
        console.error('Session creation error:', error);
        throw error;
    }
}

/**
 * Logout the user
 * @param {Object} auth - Firebase Auth instance
 * @returns {Promise} Void
 */
export async function logoutUser(auth) {
    try {
        // Import directly to avoid naming conflict
        const { signOut } = await import('https://www.gstatic.com/firebasejs/10.7.0/firebase-auth.js');
        
        // Sign out from Firebase
        await signOut(auth);
        
        // Clear session with server
        await fetch('/logout', {
            method: 'GET',
        });
        
        return true;
    } catch (error) {
        console.error('Logout error:', error);
        throw error;
    }
}

/**
 * Check authentication state
 * @param {Object} auth - Firebase Auth instance
 * @param {Function} callback - Callback function to be called with user
 * @returns {Function} Unsubscribe function
 */
export async function checkAuthState(auth, callback) {
    // Import directly to avoid naming conflict
    const { onAuthStateChanged } = await import('https://www.gstatic.com/firebasejs/10.7.0/firebase-auth.js');
    
    return onAuthStateChanged(auth, callback);
}

/**
 * Get current user
 * @param {Object} auth - Firebase Auth instance
 * @returns {Object|null} Firebase user or null
 */
export function getCurrentUser(auth) {
    return auth.currentUser;
}

/**
 * Get ID token for current user
 * @param {Object} auth - Firebase Auth instance
 * @param {boolean} forceRefresh - Whether to force refresh the token
 * @returns {Promise<string>} ID token
 */
export async function getIdToken(auth, forceRefresh = false) {
    const user = getCurrentUser(auth);
    if (!user) {
        throw new Error('No user is signed in');
    }
    
    return await user.getIdToken(forceRefresh);
}