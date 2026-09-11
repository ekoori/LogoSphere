// Openings — a list of opening cards plus the "post an opening" form. Handles
// the accept / confirm / decline actions for its cards and reports failures
// inline (no alert()).
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/App.css';
import '../styles/Openings.css';

import NewServiceForm from './NewServiceForm';
import ServiceCard from './ServiceCard';
import api from '../api';

function Openings({ services, newServiceVisible, onServiceAdded, currentUserId, actingAs = null }) {
  const [isFormVisible, setIsFormVisible] = useState(false);
  const [actionError, setActionError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
      setIsFormVisible(newServiceVisible);
  }, [newServiceVisible]);

  const run = async (fn, fallback) => {
      setActionError('');
      try {
          return await fn();
      } catch (e) {
          setActionError(e.response?.data?.message || fallback);
          return null;
      }
  };

  // Step 1: recipient signals acceptance. No exchange yet — the provider must
  // confirm. `actingAsId` (optional) accepts on behalf of an alliance/project.
  const handleAccept = (serviceId, actingAsId = null) => run(async () => {
      await api.post(`/api/openings/${serviceId}/accept`, actingAsId ? { acting_as_id: actingAsId } : {});
      if (onServiceAdded) await onServiceAdded();
  }, 'Could not accept this opening.');

  // Step 2: provider confirms a pending acceptance → an exchange is created.
  const handleConfirm = (serviceId, accepterId) => run(async () => {
      const res = await api.post(`/api/openings/${serviceId}/confirm`, { accepter_id: accepterId });
      if (onServiceAdded) await onServiceAdded();
      if (res.data?.exchange_id) navigate(`/exchange?id=${res.data.exchange_id}`);
  }, 'Could not confirm this acceptance.');

  // Provider declines a pending acceptance.
  const handleReject = (serviceId, accepterId) => run(async () => {
      await api.post(`/api/openings/${serviceId}/reject`, { accepter_id: accepterId });
      if (onServiceAdded) await onServiceAdded();
  }, 'Could not decline this acceptance.');

  return (
      <div>
          <NewServiceForm isVisible={isFormVisible} onSuccess={onServiceAdded} actingAs={actingAs} />
          {actionError && <p className="form-error" role="alert">{actionError}</p>}
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
