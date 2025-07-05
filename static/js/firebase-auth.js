
/**
 * PostgreSQL Authentication Module
 * This module provides functions for handling authentication with PostgreSQL backend
 */

/**
 * Login with email and password
 * @param {string} email - User email
 * @param {string} password - User password
 * @returns {Promise} User data and session info
 */
export async function loginWithEmailPassword(email, password) {
    try {
        console.log('Attempting to sign in with:', email);
        
        if (!email || !password) {
            throw new Error('Email and password are required');
        }
        
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email: email.trim().toLowerCase(),
                password: password
            })
        });

        let responseData;
        try {
            responseData = await response.json();
        } catch (jsonError) {
            console.error('Failed to parse response as JSON:', jsonError);
            throw new Error('Server response was not valid JSON');
        }

        if (!response.ok) {
            const errorMessage = responseData.error || `Login failed with status ${response.status}`;
            console.error('Login failed:', errorMessage);
            throw new Error(errorMessage);
        }

        if (!responseData.success) {
            throw new Error(responseData.error || 'Login failed');
        }

        console.log('Sign in successful, user:', responseData.user.email);
        return responseData;
    } catch (error) {
        console.error('Login error:', error);
        throw error;
    }
}

/**
 * Register with email and password
 * @param {string} email - User email
 * @param {string} password - User password
 * @param {Object} userData - Additional user data
 * @returns {Promise} Object with user data
 */
export async function registerWithEmailPassword(email, password, userData) {
    try {
        console.log('Attempting to register with:', email);
        
        if (!email || !password) {
            throw new Error('Email and password are required');
        }
        
        const registrationData = {
            email: email,
            password: password,
            ...userData
        };

        console.log('Registration data:', registrationData);

        const response = await fetch('/api/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(registrationData)
        });

        let responseData;
        try {
            responseData = await response.json();
        } catch (jsonError) {
            console.error('Failed to parse response as JSON:', jsonError);
            throw new Error('Server response was not valid JSON');
        }

        if (!response.ok) {
            const errorMessage = responseData.error || `Registration failed with status ${response.status}`;
            console.error('Registration failed:', errorMessage);
            throw new Error(errorMessage);
        }

        if (!responseData.success) {
            throw new Error(responseData.error || 'Registration failed');
        }

        console.log('Registration successful, user:', responseData.user.email);

        return { userCredential: responseData, serverData: responseData };
    } catch (error) {
        console.error('Registration error:', error);
        throw error;
    }
}

/**
 * Send password reset email
 * @param {string} email - User email
 * @returns {Promise} Promise that resolves when reset email is sent
 */
export async function sendPasswordReset(email) {
    try {
        const response = await fetch('/api/auth/forgot-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email: email
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Password reset failed');
        }

        return { success: true };
    } catch (error) {
        console.error('Password reset error:', error);
        throw error;
    }
}

/**
 * Create session with server
 * @param {string} email - User email
 * @param {string} password - User password
 * @param {boolean} remember - Whether to remember the session
 * @returns {Promise} Server response
 */
export async function createSession(email, password, remember = false) {
    try {
        console.log('Creating session with server...');

        const response = await fetch('/api/auth/session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email: email,
                password: password,
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

/**
 * Logout user
 * @returns {Promise} Logout response
 */
export async function logoutUser() {
    try {
        const response = await fetch('/logout', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Logout failed');
        }

        console.log('Logout successful');
        return { success: true };
    } catch (error) {
        console.error('Logout error:', error);
        throw error;
    }
}

/**
 * Get current user profile
 * @returns {Promise} User profile data
 */
export async function getCurrentUser() {
    try {
        const response = await fetch('/api/auth/profile', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to get user profile');
        }

        const userData = await response.json();
        return userData.user;
    } catch (error) {
        console.error('Get user error:', error);
        throw error;
    }
}

/**
 * Update user profile
 * @param {Object} profileData - Profile data to update
 * @returns {Promise} Updated user data
 */
export async function updateUserProfile(profileData) {
    try {
        const response = await fetch('/api/auth/profile', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(profileData)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Profile update failed');
        }

        const userData = await response.json();
        return userData.user;
    } catch (error) {
        console.error('Profile update error:', error);
        throw error;
    }
}

/**
 * Change user password
 * @param {string} currentPassword - Current password
 * @param {string} newPassword - New password
 * @returns {Promise} Success response
 */
export async function changePassword(currentPassword, newPassword) {
    try {
        const response = await fetch('/api/auth/change-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Password change failed');
        }

        return await response.json();
    } catch (error) {
        console.error('Password change error:', error);
        throw error;
    }
}

/**
 * Send email verification
 * @returns {Promise} Success response
 */
export async function sendEmailVerification() {
    try {
        const response = await fetch('/api/auth/send-verification', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to send verification email');
        }

        return await response.json();
    } catch (error) {
        console.error('Send verification error:', error);
        throw error;
    }
}

/**
 * Validate session on page load
 * @returns {Promise} User data if session is valid
 */
export async function validateSession() {
    try {
        const response = await fetch('/api/auth/validate-session', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        if (response.ok) {
            const userData = await response.json();
            return userData.user;
        }
        
        return null;
    } catch (error) {
        console.error('Session validation error:', error);
        return null;
    }
}
