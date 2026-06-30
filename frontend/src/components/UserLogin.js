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
    const { setIsLoggedIn, setUserId } = useLogin();
    const navigate = useNavigate();

    const handleLogin = async (e) => {
        e.preventDefault();
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
                navigate('/profile');
            }
        } catch (error) {
            console.error('Login error:', error);
            alert('Login failed: ' + (error.response?.data?.message || 'Unknown error'));
        }
    };

    return (
        <div className="login-container">
            <form className="login-form" onSubmit={handleLogin}>
                <h2>Login to LogoSphere</h2>
                <input
                    type="email"
                    placeholder="Email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                />
                <input
                    type="password"
                    placeholder="Password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                />
                <button type="submit">Login</button>
            </form>
        </div>
    );
};

export default UserLogin;