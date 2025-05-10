/**
 * Firebase Profile Management Module
 * This module provides functions for managing user profiles with Firebase
 */

// Import authentication functions
import { getCurrentUser, getIdToken } from './firebase-auth.js';

/**
 * Get the current user's profile from the server
 * @returns {Promise<Object>} User profile data
 */
export async function getUserProfile() {
    try {
        // Check if user is logged in
        const firebaseUser = getCurrentUser();
        if (!firebaseUser) {
            throw new Error('User not logged in');
        }
        
        // Get ID token for authentication
        const token = await getIdToken();
        
        // Get profile from server
        const response = await fetch('/api/auth/profile', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            }
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to get user profile');
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error getting user profile:', error);
        throw error;
    }
}

/**
 * Update the current user's profile on the server
 * @param {Object} profileData - Profile data to update
 * @returns {Promise<Object>} Updated user profile
 */
export async function updateUserProfile(profileData) {
    try {
        // Check if user is logged in
        const firebaseUser = getCurrentUser();
        if (!firebaseUser) {
            throw new Error('User not logged in');
        }
        
        // Get ID token for authentication
        const token = await getIdToken();
        
        // Update profile on server
        const response = await fetch('/api/auth/profile', {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(profileData),
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to update user profile');
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error updating user profile:', error);
        throw error;
    }
}

/**
 * Change user password
 * @param {string} currentPassword - Current password
 * @param {string} newPassword - New password
 * @returns {Promise<boolean>} Success status
 */
export async function changePassword(currentPassword, newPassword) {
    try {
        // Check if user is logged in
        const firebaseUser = getCurrentUser();
        if (!firebaseUser) {
            throw new Error('User not logged in');
        }
        
        // Get ID token for authentication
        const token = await getIdToken();
        
        // Change password on server
        const response = await fetch('/api/auth/change-password', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword,
            }),
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to change password');
        }
        
        return true;
    } catch (error) {
        console.error('Error changing password:', error);
        throw error;
    }
}

/**
 * Verify user email
 * @returns {Promise<boolean>} Success status
 */
export async function sendEmailVerification() {
    try {
        // Check if user is logged in
        const firebaseUser = getCurrentUser();
        if (!firebaseUser) {
            throw new Error('User not logged in');
        }
        
        // Get ID token for authentication
        const token = await getIdToken();
        
        // Send verification email
        const response = await fetch('/api/auth/send-verification', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            }
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to send verification email');
        }
        
        return true;
    } catch (error) {
        console.error('Error sending verification email:', error);
        throw error;
    }
}

/**
 * Sync user profile with Firebase
 * This updates the local database with the latest Firebase profile data
 * @returns {Promise<Object>} Synced user profile
 */
export async function syncUserProfile() {
    try {
        // Check if user is logged in
        const firebaseUser = getCurrentUser();
        if (!firebaseUser) {
            throw new Error('User not logged in');
        }
        
        // Get ID token for authentication
        const token = await getIdToken();
        
        // Sync profile with server
        const response = await fetch('/api/auth/sync-profile', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            }
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to sync user profile');
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error syncing user profile:', error);
        throw error;
    }
}