/**
 * Authentication hook and context for Firebase Auth integration.
 */
import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { initializeApp } from 'firebase/app';
import {
  getAuth,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInWithPopup,
  GoogleAuthProvider,
  signOut,
  onAuthStateChanged,
  User as FirebaseUser,
  Auth
} from 'firebase/auth';
import { User } from '../types';
import apiService from '../services/api';
import toast from 'react-hot-toast';

// Firebase configuration
const firebaseConfig = {
  apiKey: process.env.REACT_APP_FIREBASE_API_KEY,
  authDomain: process.env.REACT_APP_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.REACT_APP_FIREBASE_PROJECT_ID,
  storageBucket: process.env.REACT_APP_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.REACT_APP_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.REACT_APP_FIREBASE_APP_ID
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth: Auth = getAuth(app);
const googleProvider = new GoogleAuthProvider();

interface AuthContextType {
  currentUser: User | null;
  firebaseUser: FirebaseUser | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, displayName?: string) => Promise<void>;
  signInWithGoogle: () => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [firebaseUser, setFirebaseUser] = useState<FirebaseUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      setFirebaseUser(user);
      
      if (user) {
        try {
          // Get ID token and verify with backend
          const idToken = await user.getIdToken();
          apiService.setAuthToken(idToken);
          
          const response = await apiService.verifyToken(idToken);
          if (response.data) {
            setCurrentUser(response.data.user);
          } else {
            console.error('Failed to verify token:', response.error);
            setCurrentUser(null);
            apiService.clearAuthToken();
          }
        } catch (error) {
          console.error('Error verifying user:', error);
          setCurrentUser(null);
          apiService.clearAuthToken();
        }
      } else {
        setCurrentUser(null);
        apiService.clearAuthToken();
      }
      
      setLoading(false);
    });

    return unsubscribe;
  }, []);

  const signIn = async (email: string, password: string): Promise<void> => {
    setLoading(true);
    try {
      await signInWithEmailAndPassword(auth, email, password);
      toast.success('Signed in successfully!');
    } catch (error: any) {
      console.error('Sign in error:', error);
      toast.error(getAuthErrorMessage(error.code));
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const signUp = async (email: string, password: string, displayName?: string): Promise<void> => {
    setLoading(true);
    try {
      const result = await createUserWithEmailAndPassword(auth, email, password);
      
      // Update display name if provided
      if (displayName && result.user) {
        await result.user.updateProfile({
          displayName: displayName
        });
      }
      
      toast.success('Account created successfully!');
    } catch (error: any) {
      console.error('Sign up error:', error);
      toast.error(getAuthErrorMessage(error.code));
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const signInWithGoogle = async (): Promise<void> => {
    setLoading(true);
    try {
      await signInWithPopup(auth, googleProvider);
      toast.success('Signed in with Google successfully!');
    } catch (error: any) {
      console.error('Google sign in error:', error);
      if (error.code !== 'auth/popup-closed-by-user') {
        toast.error(getAuthErrorMessage(error.code));
      }
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const logout = async (): Promise<void> => {
    try {
      await apiService.logout();
      await signOut(auth);
      setCurrentUser(null);
      setFirebaseUser(null);
      apiService.clearAuthToken();
      toast.success('Signed out successfully!');
    } catch (error: any) {
      console.error('Logout error:', error);
      // Still clear local state even if backend call fails
      await signOut(auth);
      setCurrentUser(null);
      setFirebaseUser(null);
      apiService.clearAuthToken();
    }
  };

  const refreshUser = async (): Promise<void> => {
    if (firebaseUser) {
      try {
        const idToken = await firebaseUser.getIdToken(true); // Force refresh
        apiService.setAuthToken(idToken);
        
        const response = await apiService.getProfile();
        if (response.data) {
          setCurrentUser(response.data.user);
        }
      } catch (error) {
        console.error('Error refreshing user:', error);
      }
    }
  };

  const value: AuthContextType = {
    currentUser,
    firebaseUser,
    loading,
    signIn,
    signUp,
    signInWithGoogle,
    logout,
    refreshUser
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

// Helper function to get user-friendly error messages
const getAuthErrorMessage = (errorCode: string): string => {
  switch (errorCode) {
    case 'auth/user-not-found':
      return 'No account found with this email address.';
    case 'auth/wrong-password':
      return 'Incorrect password.';
    case 'auth/email-already-in-use':
      return 'An account with this email already exists.';
    case 'auth/weak-password':
      return 'Password should be at least 6 characters.';
    case 'auth/invalid-email':
      return 'Please enter a valid email address.';
    case 'auth/too-many-requests':
      return 'Too many failed attempts. Please try again later.';
    case 'auth/network-request-failed':
      return 'Network error. Please check your connection.';
    case 'auth/popup-blocked':
      return 'Popup was blocked. Please allow popups and try again.';
    case 'auth/cancelled-popup-request':
    case 'auth/popup-closed-by-user':
      return 'Sign-in cancelled.';
    default:
      return 'An error occurred. Please try again.';
  }
};