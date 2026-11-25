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
import HowItWorks from './pages/HowItWorks';
import Home from './pages/Home';
import ProfilePage from './pages/ProfilePage';
import EntityListPage from './pages/EntityListPage';
import EntityPage from './pages/EntityPage';
import EntityManagement from './pages/EntityManagement';
import UserPage from './pages/UserPage';
import OpeningsPage from './pages/OpeningsPage';
import OpeningPage from './pages/OpeningPage';
import ExchangePage from './pages/ExchangePage';
import SettingsPage from './pages/Settings';
import ResetPassword from './pages/ResetPassword';
import { ConfirmEmailPage, JoinPage, UnsubscribePage } from './pages/EmailLinkPages';
import SearchPage from './pages/SearchPage';
import MeaningGraphPage from './pages/MeaningGraphPage';
import NearbyPage from './pages/NearbyPage';
import MessagesPage from './pages/MessagesPage';
import EventsPage from './pages/EventsPage';
import EventPage from './pages/EventPage';
import EventEditPage from './pages/EventEditPage';
import InvitePage from './pages/InvitePage';
import MapPickerPage from './pages/MapPickerPage';
import { SIMPLE, modeOfAccount, rememberMode, rememberedMode } from './utils/modes';
import Contribute from './pages/Contribute';
import Donate from './pages/Donate';
import Privacy from './pages/Privacy';
import TOS from './pages/TOS';
import ChildSafety from './pages/ChildSafety';

// Component Imports
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
        <Route path="/how-it-works" element={<HowItWorks/>}/>
        <Route path="/register" element={<div className='container'><UserRegistration/></div>}/>
        <Route path="/login" element={<div className='container'><UserLogin/></div>}/>
        <Route path="/reset-password" element={<div className='container'><ResetPassword/></div>}/>
        {/* Where emailed links land; each carries its own proof, so no session is needed. */}
        <Route path="/join" element={<div className='container'><JoinPage/></div>}/>
        <Route path="/confirm-email" element={<div className='container'><ConfirmEmailPage/></div>}/>
        <Route path="/unsubscribe" element={<div className='container'><UnsubscribePage/></div>}/>
        <Route path="/invite" element={<div className='container'><InvitePage/></div>}/>
        {/* The method is public; the page itself gates the graph. */}
        <Route path="/meaning-graph" element={<ErrorBoundary><MeaningGraphPage/></ErrorBoundary>}/>
        <Route path="/privacy" element={<Privacy/>}/>
        <Route path="/tos" element={<TOS/>}/>
        <Route path="/child-safety" element={<ChildSafety/>}/>
        
        {/* Protected Routes — gated by ProtectedRoute (redirects to /login) */}
        <Route path="/profile" element={<ErrorBoundary><ProtectedRoute><ProfilePage/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/settings" element={<ErrorBoundary><ProtectedRoute><SettingsPage/></ProtectedRoute></ErrorBoundary>} />
        {/* Spheres / alliances / projects share one list, one detail and one
            management page, parameterised by kind. */}
        <Route path="/spheres" element={<ErrorBoundary><ProtectedRoute><EntityListPage kind="sphere"/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/alliances" element={<ErrorBoundary><ProtectedRoute><EntityListPage kind="alliance"/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/projects" element={<ErrorBoundary><ProtectedRoute><EntityListPage kind="project"/></ProtectedRoute></ErrorBoundary>} />
        {/* Public: a sphere flagged "public activity" is viewable without an
            account; EntityPage itself gates private spheres. */}
        <Route path="/sphere" element={<ErrorBoundary><EntityPage kind="sphere"/></ErrorBoundary>} />
        <Route path="/alliance" element={<ErrorBoundary><ProtectedRoute><EntityPage kind="alliance"/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/project" element={<ErrorBoundary><ProtectedRoute><EntityPage kind="project"/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/sphere-management" element={<ErrorBoundary><ProtectedRoute><EntityManagement kind="sphere"/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/alliance-management" element={<ErrorBoundary><ProtectedRoute><EntityManagement kind="alliance"/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/project-management" element={<ErrorBoundary><ProtectedRoute><EntityManagement kind="project"/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/openings" element={<ErrorBoundary><ProtectedRoute><OpeningsPage/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/exchange" element={<ErrorBoundary><ProtectedRoute><ExchangePage/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/opening" element={<ErrorBoundary><ProtectedRoute><OpeningPage/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/messages" element={<ErrorBoundary><ProtectedRoute><MessagesPage/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/events" element={<ErrorBoundary><ProtectedRoute><EventsPage/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/event" element={<ErrorBoundary><ProtectedRoute><EventPage/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/event-edit" element={<ErrorBoundary><ProtectedRoute><EventEditPage/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/nearby" element={<ErrorBoundary><ProtectedRoute><NearbyPage/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/user" element={<ErrorBoundary><ProtectedRoute><UserPage/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/admin" element={<ErrorBoundary><ProtectedRoute><AdminPage/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/search" element={<ErrorBoundary><ProtectedRoute><SearchPage/></ProtectedRoute></ErrorBoundary>} />
        <Route path="/contribute" element={<Contribute/>}/>
        <Route path="/donate" element={<Donate/>}/>
        
        {/* 404 Route */}
        <Route path="*" element={<div className='container'><NotFound/></div>} />
      </Routes>
      <Footer className='footer'/>
    </div>
  );
}

function LoginProvider({ children }) {
  // Simple or Advanced (utils/modes.js). Account data; presentation only.
  const [uiMode, setUiModeState] = useState(rememberedMode);
  const adoptUiMode = useCallback((mode) => {
    setUiModeState(mode);
    rememberMode(mode);
  }, []);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userId, setUserId] = useState(null);
  // The signed-in user's first name, for the nav account button.
  const [userName, setUserName] = useState('');
  // Platform administrators can see all data and manage any sphere.
  const [isPlatformAdmin, setIsPlatformAdmin] = useState(false);
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
        setUserName('');
        setIsPlatformAdmin(false);
        adoptUiMode(SIMPLE);
        navigate('/login', { replace: true });
      } else {
        console.error('Logout failed:', response.data.message);
      }
    } catch (error) {
      console.error('Error during logout:', error);
      // Best effort: clear local auth state even if the server call failed.
      setIsLoggedIn(false);
      setUserId(null);
      navigate('/login', { replace: true });
    }
  };

  // Shown at once, put back if the account didn't take it.
  const changeUiMode = useCallback(async (mode) => {
    const was = uiMode;
    adoptUiMode(mode);
    try {
      await api.post('/api/account/preferences', { ui_mode: mode });
      return true;
    } catch (error) {
      adoptUiMode(was);
      return false;
    }
  }, [uiMode, adoptUiMode]);

  const checkSession = useCallback(async () => {
    try {
      const response = await api.get('/api/check_session', {
        withCredentials: true
      });

      if (response.data.status === 'active' && response.data.user_id) {
        setIsLoggedIn(true);
        setUserId(response.data.user_id);
        setUserName((response.data.user_data?.name || '').trim());
        setIsPlatformAdmin(!!response.data.user_data?.is_platform_admin);
        adoptUiMode(modeOfAccount(response.data.user_data));
      } else {
        setIsLoggedIn(false);
        setUserId(null);
        setUserName('');
        setIsPlatformAdmin(false);
        adoptUiMode(SIMPLE);
      }
    } catch (error) {
      // Only the server saying "no session" signs you out. A 503 (database
      // busy), a 500 or a dropped connection says nothing about the session:
      // keep the current state and let the next check settle it.
      if (error.response?.status === 401) {
        setIsLoggedIn(false);
        setUserId(null);
      } else {
        console.warn('Could not check the session just now:', error.message);
      }
    } finally {
      setAuthChecked(true);
    }
  }, [adoptUiMode]);

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
      userName,
      setUserName,
      isPlatformAdmin,
      setIsPlatformAdmin,
      authChecked,
      uiMode,
      adoptUiMode,
      changeUiMode,
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

// The app's map page is only a map: no header, no session, no API calls.
function Shell() {
  const { pathname } = useLocation();
  if (pathname === '/map-picker') return <ErrorBoundary><MapPickerPage/></ErrorBoundary>;
  return (
    <LoginProvider>
      <AppContent />
    </LoginProvider>
  );
}

function App() {
  return (
    <Router>
      <Shell />
    </Router>
  );
}

export default App;