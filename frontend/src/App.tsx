import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';
import { getFirestore } from 'firebase/firestore';

// Import components and pages
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import DraftRoom from './pages/DraftRoom';
import MyTeam from './pages/MyTeam';
import PlayersView from './pages/PlayersView';
import LeagueView from './pages/LeagueView';
import PlayoffBracket from './pages/PlayoffBracket';
import ChatView from './pages/ChatView';
import AdminPanel from './pages/AdminPanel';

// Import context providers
import { AppProvider } from './store';
import { useAuth } from './hooks/useAuth';

// Import CSS
import './App.css';

// Firebase configuration - replace with your actual config
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
export const auth = getAuth(app);
export const db = getFirestore(app);

interface AppContentProps {
  children: React.ReactNode;
}

const AppContent: React.FC<AppContentProps> = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <Router>
      <div className="App min-h-screen bg-gray-50">
        <Routes>
          {/* Public routes */}
          <Route 
            path="/login" 
            element={user ? <Navigate to="/dashboard" replace /> : <Login />} 
          />
          
          {/* Protected routes */}
          <Route 
            path="/dashboard" 
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            } 
          />
          
          <Route 
            path="/draft/:leagueId" 
            element={
              <ProtectedRoute>
                <DraftRoom />
              </ProtectedRoute>
            } 
          />
          
          <Route 
            path="/my-team/:leagueId" 
            element={
              <ProtectedRoute>
                <MyTeam />
              </ProtectedRoute>
            } 
          />
          
          <Route 
            path="/players/:leagueId" 
            element={
              <ProtectedRoute>
                <PlayersView />
              </ProtectedRoute>
            } 
          />
          
          <Route 
            path="/league/:leagueId" 
            element={
              <ProtectedRoute>
                <LeagueView />
              </ProtectedRoute>
            } 
          />
          
          <Route 
            path="/playoffs/:leagueId" 
            element={
              <ProtectedRoute>
                <PlayoffBracket />
              </ProtectedRoute>
            } 
          />
          
          <Route 
            path="/chat/:leagueId" 
            element={
              <ProtectedRoute>
                <ChatView />
              </ProtectedRoute>
            } 
          />
          
          <Route 
            path="/admin/:leagueId" 
            element={
              <ProtectedRoute>
                <AdminPanel />
              </ProtectedRoute>
            } 
          />
          
          {/* Default redirect */}
          <Route 
            path="/" 
            element={<Navigate to={user ? "/dashboard" : "/login"} replace />} 
          />
          
          {/* Catch all - redirect to dashboard or login */}
          <Route 
            path="*" 
            element={<Navigate to={user ? "/dashboard" : "/login"} replace />} 
          />
        </Routes>
        {children}
      </div>
    </Router>
  );
};

const App: React.FC = () => {
  return (
    <AppProvider>
      <AppContent>
        <></>
      </AppContent>
    </AppProvider>
  );
};

export default App;