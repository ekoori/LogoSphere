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
import { useNavigate } from 'react-router-dom';
import '../styles/App.css';
import '../styles/Openings.css';

import NewServiceForm from './NewServiceForm';
import ServiceCard from './ServiceCard';
import api from '../api';



function Openings({ services, newServiceVisible, onServiceAdded, currentUserId }) {
  const [isFormVisible, setIsFormVisible] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
      setIsFormVisible(newServiceVisible);
  }, [newServiceVisible]);

  const toggleFormVisibility = () => {
      setIsFormVisible(!isFormVisible);
  };

  const handleAccept = async (serviceId) => {
      try {
          const res = await api.post(`/api/openings/${serviceId}/accept`);
          if (onServiceAdded) onServiceAdded();
          if (res.data?.exchange_id) {
              navigate(`/exchange?id=${res.data.exchange_id}`);
          }
      } catch (e) {
          console.error('Failed to accept opening:', e);
          alert(e.response?.data?.message || 'Could not accept this opening.');
      }
  };

  return (
      <div>
          <NewServiceForm isVisible={isFormVisible} onSuccess={onServiceAdded} />
          <section className="openings">
              {services.map(service => (
                  <ServiceCard
                      key={service.id}
                      {...service}
                      currentUserId={currentUserId}
                      onAccept={() => handleAccept(service.id)}
                  />
              ))}
          </section>
      </div>
  );
}

export default Openings;
