/**
 * Firebase Profile Management Module
 * 
 * This module provides functions for managing user profiles with Firebase Authentication
 */

import { auth } from './firebase-auth.js';
import { 
    EmailAuthProvider, 
    updateProfile, 
    updateEmail, 
    updatePassword, 
    sendEmailVerification, 
    reauthenticateWithCredential 
} from 'https://www.gstatic.com/firebasejs/11.0.2/firebase-auth.js';

/**
 * Get the current user's profile from the server
 * @returns {Promise<Object>} User profile data
 */
export async function getUserProfile() {
    try {
        const response = await fetch('/api/auth/profile');
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to get user profile');
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
        // First update Firebase profile if needed
        const currentUser = auth.currentUser;
        if (currentUser && (profileData.firstName || profileData.lastName)) {
            const displayName = `${profileData.firstName || ''} ${profileData.lastName || ''}`.trim();
            await updateProfile(currentUser, {
                displayName: displayName
            });
        }
        
        // Then update server profile
        const response = await fetch('/api/auth/profile', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(profileData)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to update profile');
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error updating profile:', error);
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
        const user = auth.currentUser;
        if (!user) {
            throw new Error('No authenticated user');
        }
        
        // Re-authenticate user before changing password
        const credential = EmailAuthProvider.credential(user.email, currentPassword);
        await reauthenticateWithCredential(user, credential);
        
        // Update password
        await updatePassword(user, newPassword);
        
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
        const user = auth.currentUser;
        if (!user) {
            throw new Error('No authenticated user');
        }
        
        await sendEmailVerification(user);
        
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
        const response = await fetch('/api/auth/sync-profile', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to sync profile');
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error syncing profile:', error);
        throw error;
    }
}