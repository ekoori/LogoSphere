// File: ./frontend/src/App.js
// Description: This is the main component where routing is set up and different page components & layout components are loaded based on routing. 
//              It also manages global state for user authentication using Context API.
// Classes/Components:
//    [+] App - The main application component that sets up routing and global providers
//    [+] AppContent - The main layout component that handles route rendering
//    [+] LoginProvider - Context provider component that manages authentication state
//        Properties:
//            [+] isLoggedIn - Boolean state indicating if user is logged in
//            [+] userId - String state containing current user's ID
//        Methods:
//            [+] handleLogout() - Handles user logout process
//            [+] checkSession() - Verifies if current session is valid
//    [+] useLogin - Custom hook for accessing login context
//        Returns: { isLoggedIn, setIsLoggedIn, userId, setUserId, handleLogout }

import './styles/App.css';
import React, { createContext, useState, useEffect, useContext, useCallback } from 'react';
import { BrowserRouter as Router, Route, Routes, useNavigate, Navigate, useLocation } from 'react-router-dom';

// Page Imports
import About from './pages/About';
import Home from './pages/Home';
import ProfilePage from './pages/ProfilePage';
import Spheres from './pages/Spheres';
import SpherePage from './pages/SpherePage';
import SphereManagement from './pages/SphereManagement';
import Alliances from './pages/Alliances';
import AlliancePage from './pages/AlliancePage';
import AllianceManagement from './pages/AllianceManagement';
import ProjectPage from './pages/ProjectPage';
import ProjectManagement from './pages/ProjectManagement';
import UserPage from './pages/UserPage';
import MarketplacePage from './pages/MarketplacePage';
import TransactionPage from './pages/TransactionPage';
import SettingsPage from './pages/Settings';
import Contribute from './pages/Contribute';
import Donate from './pages/Donate';
import Privacy from './pages/Privacy';
import TOS from './pages/TOS';

// Component Imports
import Projects from './components/Projects';
import UserRegistration from './components/UserRegistration';
import Header from './components/Header';
import Footer from './components/Footer';
import ErrorBoundary from './components/ErrorBoundary';
import UserLogin from './components/UserLogin';
import NotFound from './components/NotFound';
import AdminPage from './components/AdminPage';

// Utility Imports
import api from './api';

const LoginContext = createContext();

// Gates a route behind authentication. While the initial session check is in
// flight we render nothing (avoids a redirect flicker for logged-in users);
// once resolved, unauthenticated users are sent to /login (remembering where
// they were headed).
function ProtectedRoute({ children }) {
  const { isLoggedIn, authChecked } = useLogin();
  const location = useLocation();

  if (!authChecked) {
    return <div className="route-loading">Loading…</div>;
  }
  if (!isLoggedIn) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return children;
}

function AppContent() {
  return (
    <div className="app-container">
      <Header className='header'/>
      <Routes>
        {/* Public Routes */}
        <Route path="/" element={<Home/>}/>
        <Route path="/about" element={<About/>}/>
        <Route path="/register" element={<div className='container'><UserRegistration/></div>}/>
        <Route path="/login" element={<div className='container'><UserLogin/></div>}/>
        <Route path="/privacy" element={<div className='container'><Privacy/></div>}/>
        <Route path="/tos" element={<div className='container'><TOS/></div>}/>
        
        {/* Protected Routes — gated by ProtectedRoute (redirects to /login) */}
        <Route path="/profile" element={<ErrorBoundary><ProtectedRoute><ProfilePage/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/settings" element={<ErrorBoundary><ProtectedRoute><SettingsPage/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/projects" element={<ErrorBoundary><ProtectedRoute><Projects/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/project" element={<ErrorBoundary><ProtectedRoute><ProjectPage/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/project-management" element={<ErrorBoundary><ProtectedRoute><ProjectManagement/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/spheres" element={<ErrorBoundary><ProtectedRoute><Spheres/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/sphere" element={<ErrorBoundary><ProtectedRoute><SpherePage/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/sphere-management" element={<ErrorBoundary><ProtectedRoute><SphereManagement/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/alliances" element={<ErrorBoundary><ProtectedRoute><Alliances/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/alliance" element={<ErrorBoundary><ProtectedRoute><AlliancePage/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/alliance-management" element={<ErrorBoundary><ProtectedRoute><AllianceManagement/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/marketplace" element={<ErrorBoundary><ProtectedRoute><MarketplacePage/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/transaction" element={<ErrorBoundary><ProtectedRoute><TransactionPage/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/user" element={<ErrorBoundary><ProtectedRoute><UserPage/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/admin" element={<ErrorBoundary><ProtectedRoute><AdminPage/></ProtectedRoute></ErrorBoundary>} />
        <Route 
          path="/contribute" 
          element={<div className='container'><Contribute/></div>}
        />
        <Route 
          path="/donate" 
          element={<div className='container'><Donate/></div>}
        />
        
        {/* 404 Route */}
        <Route path="*" element={<div className='container'><NotFound/></div>} />
      </Routes>
      <Footer className='footer'/>
    </div>
  );
}

function LoginProvider({ children }) {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userId, setUserId] = useState(null);
  // Tracks whether the initial session check has completed, so protected routes
  // don't redirect to /login before we know the real auth state.
  const [authChecked, setAuthChecked] = useState(false);
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      const response = await api.post('/api/logout', {}, {
        withCredentials: true,
      });
      if (response.data.success) {
        console.log('Logout successful');
        setIsLoggedIn(false);
        setUserId(null);
        navigate('/login', { replace: true });
      } else {
        console.error('Logout failed:', response.data.message);
      }
    } catch (error) {
      console.error('Error during logout:', error);
      alert('Error during logout: ' + error.message);
    }
  };

  const checkSession = useCallback(async () => {
    try {
      const response = await api.get('/api/check_session', {
        withCredentials: true
      });
      console.log('Check session response:', response.data);
      
      if (response.data.status === 'active' && response.data.user_id) {
        setIsLoggedIn(true);
        setUserId(response.data.user_id);
      } else {
        console.log('No active session found');
        setIsLoggedIn(false);
        setUserId(null);
      }
    } catch (error) {
      if (error.response?.status === 500) {
        console.error('Internal Server Error while checking session:', error);
      } else {
        console.info('No active session or error checking session:', error);
        setIsLoggedIn(false);
        setUserId(null);
      }
    } finally {
      setAuthChecked(true);
    }
  }, []);

  useEffect(() => {
    checkSession();
    const intervalId = setInterval(checkSession, 5 * 60 * 1000); // Check every 5 minutes
    return () => clearInterval(intervalId);
  }, [checkSession]);

  return (
    <LoginContext.Provider value={{
      isLoggedIn,
      setIsLoggedIn,
      userId,
      setUserId,
      authChecked,
      handleLogout
    }}>
      {children}
    </LoginContext.Provider>
  );
}

export function useLogin() {
  const context = useContext(LoginContext);
  if (!context) {
    throw new Error('useLogin must be used within a LoginProvider');
  }
  return context;
}

function App() {
  return (
    <Router>
      <LoginProvider>
        <AppContent />
      </LoginProvider>
    </Router>
  );
}

export default App;