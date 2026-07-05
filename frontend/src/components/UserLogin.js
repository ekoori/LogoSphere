// File: ./frontend/src/components/UserLogin.js
// Description: This is the React.js file for the User Login Component.
// Classes/Methods/Properties: 
//    [+] UserLogin - The main component for the user login form.
//        [+] email - State property to store the user's entered email.
//        [+] password - State property to store the user's entered password.
//        [+] handleLogin - Handles the form submission for logging in the user.



import React, { useState } from 'react';
import api from '../api';
import '../styles/App.css'; 
import '../styles/UserLogin.css'; 
import { Link, useNavigate } from 'react-router-dom';
import { useLogin } from '../App';  // Import useLogin hook



const UserLogin = () => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const { setIsLoggedIn, setUserId, setUserName, setIsPlatformAdmin } = useLogin();
    const navigate = useNavigate();

    const handleLogin = async (e) => {
        e.preventDefault();
        setError('');
        setSubmitting(true);
        try {
            const response = await api.post('/api/login', {
                email,
                password
            }, {
                withCredentials: true
            });

            if (response.status === 200 && response.data.data) {
                setIsLoggedIn(true);
                setUserId(response.data.data.user_id);
                setUserName((response.data.data.name || '').trim());
                setIsPlatformAdmin(!!response.data.data.is_platform_admin);
                navigate('/profile');
            }
        } catch (error) {
            console.error('Login error:', error);
            setError(error.response?.data?.message || 'Login failed. Check your email and password.');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="login-container">
            <form className="login-form" onSubmit={handleLogin}>
                <h2>Log in to LogoSphere</h2>
                {error && <p className="auth-error">{error}</p>}
                <input
                    type="email"
                    placeholder="Email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoComplete="email"
                    required
                />
                <input
                    type="password"
                    placeholder="Password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="current-password"
                    required
                />
                <button type="submit" disabled={submitting}>
                    {submitting ? 'Logging in…' : 'Log in'}
                </button>
                <p className="auth-alt">
                    New to LogoSphere? <Link to="/register">Create an account</Link>
                </p>
            </form>
        </div>
    );
};

export default UserLogin;