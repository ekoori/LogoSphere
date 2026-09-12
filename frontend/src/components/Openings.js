// Openings — a list of opening cards plus the "post an opening" form. Handles
// the accept / confirm / decline actions for its cards and reports failures
// inline, on the card the action came from (no alert(), no banner at the top
// of a long list where nobody sees it).
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/App.css';
import '../styles/Openings.css';

import NewServiceForm from './NewServiceForm';
import ServiceCard from './ServiceCard';
import api from '../api';

function Openings({ services, newServiceVisible, onServiceAdded, currentUserId, actingAs = null }) {
  const [isFormVisible, setIsFormVisible] = useState(false);
  // { id: <opening id>, message } — shown inside that opening's card.
  const [actionError, setActionError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
      setIsFormVisible(newServiceVisible);
  }, [newServiceVisible]);

  const run = async (serviceId, fn, fallback) => {
      setActionError(null);
      try {
          return await fn();
      } catch (e) {
          setActionError({ id: serviceId, message: e.response?.data?.message || fallback });
          return null;
      }
  };

  // Step 1: recipient signals acceptance. No exchange yet — the provider must
  // confirm. `actingAsId` (optional) accepts on behalf of an alliance/project.
  const handleAccept = (serviceId, actingAsId = null) => run(serviceId, async () => {
      await api.post(`/api/openings/${serviceId}/accept`, actingAsId ? { acting_as_id: actingAsId } : {});
      if (onServiceAdded) await onServiceAdded();
  }, 'Could not accept this opening.');

  // Step 2: provider confirms a pending acceptance → an exchange is created.
  const handleConfirm = (serviceId, accepterId) => run(serviceId, async () => {
      const res = await api.post(`/api/openings/${serviceId}/confirm`, { accepter_id: accepterId });
      if (onServiceAdded) await onServiceAdded();
      if (res.data?.exchange_id) navigate(`/exchange?id=${res.data.exchange_id}`);
  }, 'Could not confirm this acceptance.');

  // Provider declines a pending acceptance.
  const handleReject = (serviceId, accepterId) => run(serviceId, async () => {
      await api.post(`/api/openings/${serviceId}/reject`, { accepter_id: accepterId });
      if (onServiceAdded) await onServiceAdded();
  }, 'Could not decline this acceptance.');

  return (
      <div>
          <NewServiceForm isVisible={isFormVisible} onSuccess={onServiceAdded} actingAs={actingAs} />
          <section className="openings">
              {services.map(service => (
                  <ServiceCard
                      key={service.id}
                      {...service}
                      currentUserId={currentUserId}
                      actionError={actionError?.id === service.id ? actionError.message : null}
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
