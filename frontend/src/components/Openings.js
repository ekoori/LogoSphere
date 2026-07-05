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



function Openings({ services, newServiceVisible, onServiceAdded, currentUserId, actingAs = null }) {
  const [isFormVisible, setIsFormVisible] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
      setIsFormVisible(newServiceVisible);
  }, [newServiceVisible]);

  // Step 1: recipient signals acceptance. No exchange yet — the provider must
  // confirm. `actingAsId` (optional) accepts on behalf of an alliance/project.
  // Refetch so the card reflects the pending state.
  const handleAccept = async (serviceId, actingAsId = null) => {
      try {
          await api.post(`/api/openings/${serviceId}/accept`, actingAsId ? { acting_as_id: actingAsId } : {});
          if (onServiceAdded) onServiceAdded();
      } catch (e) {
          console.error('Failed to accept opening:', e);
          alert(e.response?.data?.message || 'Could not accept this opening.');
      }
  };

  // Step 2: provider confirms a pending acceptance → an exchange is created.
  const handleConfirm = async (serviceId, accepterId) => {
      try {
          const res = await api.post(`/api/openings/${serviceId}/confirm`, { accepter_id: accepterId });
          if (onServiceAdded) onServiceAdded();
          if (res.data?.exchange_id) {
              navigate(`/exchange?id=${res.data.exchange_id}`);
          }
      } catch (e) {
          console.error('Failed to confirm acceptance:', e);
          alert(e.response?.data?.message || 'Could not confirm this acceptance.');
      }
  };

  // Provider declines a pending acceptance.
  const handleReject = async (serviceId, accepterId) => {
      try {
          await api.post(`/api/openings/${serviceId}/reject`, { accepter_id: accepterId });
          if (onServiceAdded) onServiceAdded();
      } catch (e) {
          console.error('Failed to reject acceptance:', e);
          alert(e.response?.data?.message || 'Could not decline this acceptance.');
      }
  };

  return (
      <div>
          <NewServiceForm isVisible={isFormVisible} onSuccess={onServiceAdded} actingAs={actingAs} />
          <section className="openings">
              {services.map(service => (
                  <ServiceCard
                      key={service.id}
                      {...service}
                      currentUserId={currentUserId}
                      onAccept={(actingAsId) => handleAccept(service.id, actingAsId)}
                      onConfirm={(accepterId) => handleConfirm(service.id, accepterId)}
                      onReject={(accepterId) => handleReject(service.id, accepterId)}
                  />
              ))}
          </section>
      </div>
  );
}

export default Openings;
