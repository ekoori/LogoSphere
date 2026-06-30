/*
File : ./frontend/src/components/Openings.js
Description: This file creates a React component for the Openings, where users can post and view services. 
        It contains functionality for loading the services from the API and displaying them.
Class: Openings
Properties: 
  [-] state: contains a list of services fetched from the API.
Methods: 
  [-] componentDidMount(): calls the API to fetch the list of services when the component is first mounted.
  [-] handleServiceSubmission(): submits a new service to the API (not yet implemented).
*/

import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import '../styles/App.css';
import '../styles/Openings.css';

import NewServiceForm from './NewServiceForm';
import ServiceCard from './ServiceCard';



function Openings({ services, newServiceVisible, onServiceAdded }) {
  const [isFormVisible, setIsFormVisible] = useState(false);

  useEffect(() => {
      setIsFormVisible(newServiceVisible);
  }, [newServiceVisible]);

  const toggleFormVisibility = () => {
      setIsFormVisible(!isFormVisible);
  };

  const handleAccept = (serviceId) => {
      console.log(`Accept service: ${serviceId}`);
      // Logic to accept the service
  };

  const handleConfirm = (serviceId) => {
      console.log(`Confirm service: ${serviceId}`);
      // Logic to confirm the service
  };

  return (
      <div>
          <NewServiceForm isVisible={isFormVisible} onSuccess={onServiceAdded} />
          <section className="openings">
              {services.map(service => (
                  <ServiceCard
                      key={service.id}
                      {...service}
                      onAccept={() => handleAccept(service.id)}
                      onConfirm={() => handleConfirm(service.id)}
                  />
              ))}
          </section>
      </div>
  );
}

export default Openings;

