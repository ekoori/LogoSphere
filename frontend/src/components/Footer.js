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
            <li><a href="/about">About LogoSphere</a></li>
            <li><a href="/contribute">Contribute</a></li>
            <li><a href="/privacy">Privacy Policy</a></li>
            <li><a href="/tos">Terms of Service</a></li>
        </ul>
      </footer>




    );
};

export default Footer;
