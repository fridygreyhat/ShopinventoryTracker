/**
 * Firebase Authentication Module
 * This module provides functions for handling authentication with Firebase
 */

// Firebase configuration will be injected from the server
let firebaseConfig = {};
let app;
let auth;

/**
 * Initialize Firebase with configuration
 * @param {Object} config - Firebase configuration object
 */
export function initializeFirebase(config) {
    firebaseConfig = config;
    
    // Only initialize once
    if (!app) {
        app = firebase.initializeApp(firebaseConfig);
        auth = firebase.auth();
    }
    
    return { app, auth };
}

/**
 * Login with email and password
 * @param {string} email - User email
 * @param {string} password - User password
 * @returns {Promise} Firebase user credential
 */
export async function loginWithEmailPassword(email, password) {
    try {
        const userCredential = await auth.signInWithEmailAndPassword(email, password);
        return userCredential;
    } catch (error) {
        console.error('Login error:', error);
        throw error;
    }
}

/**
 * Send password reset email
 * @param {string} email - User email
 * @returns {Promise} Promise that resolves when reset email is sent
 */
export async function sendPasswordResetEmail(email) {
    try {
        await auth.sendPasswordResetEmail(email);
        return { success: true };
    } catch (error) {
        console.error('Password reset error:', error);
        throw error;
    }
}

/**
 * Register a new user with email and password
 * @param {string} email - User email
 * @param {string} password - User password
 * @param {Object} userData - Additional user data
 * @returns {Promise} Firebase user credential and server response
 */
export async function registerWithEmailPassword(email, password, userData) {
    try {
        // Create user in Firebase
        const userCredential = await auth.createUserWithEmailAndPassword(email, password);
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
 * @returns {Promise} Void
 */
export async function logoutUser() {
    try {
        // Sign out from Firebase
        await auth.signOut();
        
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
 * @param {Function} callback - Callback function to be called with user
 * @returns {Function} Unsubscribe function
 */
export function checkAuthState(callback) {
    return auth.onAuthStateChanged(callback);
}

/**
 * Get current user
 * @returns {Object|null} Firebase user or null
 */
export function getCurrentUser() {
    return auth.currentUser;
}

/**
 * Get ID token for current user
 * @param {boolean} forceRefresh - Whether to force refresh the token
 * @returns {Promise<string>} ID token
 */
export async function getIdToken(forceRefresh = false) {
    const user = getCurrentUser();
    if (!user) {
        throw new Error('No user is signed in');
    }
    
    return await user.getIdToken(forceRefresh);
}