// File: ./frontend/src/components/Footer.js
// Description: Represents the Footer component of the application.
// Class: Footer - A fixed footer that provides navigation.
// Properties: None
// Methods: None

import React from 'react';
import { Link } from 'react-router-dom';
import '../styles/App.css';

/*
 * Header component displaying the navigation bar
 * @param {object} props 
 * @returns JSX elements
 */

const Footer = () => {

    
    return (
      <footer>
        <ul>
            <li><Link to="/how-it-works">How it Works</Link></li>
            <li><Link to="/about">About LogoSphere</Link></li>
            <li><Link to="/contribute">Contribute</Link></li>
            <li><Link to="/privacy">Privacy Policy</Link></li>
            <li><Link to="/tos">Terms of Service</Link></li>
        </ul>
      </footer>




    );
};

export default Footer;
