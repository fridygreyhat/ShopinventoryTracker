/**
 * Firebase Authentication Module
 * This module provides functions for handling authentication with Firebase
 * Updated to use the modular API structure of Firebase Web SDK v9+
 */

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
        console.log('Attempting to sign in with:', email);
        const userCredential = await signInWithEmailAndPassword(auth, email, password);
        console.log('Sign in successful, user:', userCredential.user.email);
        return userCredential;
    } catch (error) {
        console.error('Login error:', error);
        throw error;
    }
}

/**
 * Register with email and password
 * @param {Object} auth - Firebase Auth instance
 * @param {string} email - User email
 * @param {string} password - User password
 * @param {Object} userData - Additional user data
 * @returns {Promise} Object with userCredential and serverData
 */
export async function registerWithEmailPassword(auth, email, password, userData) {
    try {
        // Import directly to avoid naming conflict
        const { createUserWithEmailAndPassword } = await import('https://www.gstatic.com/firebasejs/10.7.0/firebase-auth.js');

        console.log('Attempting to register with:', email);
        const userCredential = await createUserWithEmailAndPassword(auth, email, password);
        console.log('Registration successful, user:', userCredential.user.email);

        // Get the ID token for server registration
        const token = await userCredential.user.getIdToken();

        // Register with server
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                idToken: token,
                ...userData
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Server registration failed');
        }

        const serverData = await response.json();

        return { userCredential, serverData };
    } catch (error) {
        console.error('Registration error:', error);
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
 * Create session with server
 * @param {string} token - Firebase ID token
 * @param {boolean} remember - Whether to remember the session
 * @returns {Promise} Server response
 */
export async function createSession(token, remember = false) {
    try {
        console.log('Creating session with server...');

        const response = await fetch('/api/auth/session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                idToken: token,
                remember: remember
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Session creation failed');
        }

        const sessionData = await response.json();
        console.log('Session created successfully');
        return sessionData;
    } catch (error) {
        console.error('Session creation error:', error);
        throw error;
    }
}