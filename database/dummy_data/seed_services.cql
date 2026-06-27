-- ============================================================================
-- Enrich marketplace services with likes, a project association, an image key,
-- and varied lifecycle statuses (so the progress control shows real states).
-- image_key maps to a bundled static asset on the frontend.
-- ============================================================================
USE trustsphere;

UPDATE services SET likes=12, project_name='Skill Share', image_key='podcast', status='In Progress'
  WHERE service_id=cccccccc-0000-0000-0000-000000000001;
UPDATE services SET likes=8, project_name='Community Tool Library', image_key='garden', status='Accepted'
  WHERE service_id=cccccccc-0000-0000-0000-000000000002;
UPDATE services SET likes=27, project_name='Open GPU Cluster', image_key='gpu', status='Posted'
  WHERE service_id=cccccccc-0000-0000-0000-000000000003;
UPDATE services SET likes=15, project_name='Pollinator Corridor', image_key='seeds', status='Posted'
  WHERE service_id=cccccccc-0000-0000-0000-000000000004;

-- Two more so the marketplace feels alive.
INSERT INTO services (service_id, type, title, description, provider_id, provider_name, sphere_id, sphere_name, status, created_at, values, likes, project_name, image_key)
VALUES (cccccccc-0000-0000-0000-000000000005, 'offer',
  'Tool restoration & blade-sharpening workshop',
  'Bring your dull, rusty or broken hand tools and we will bring them back to life together. A hands-on Saturday at the Repair Café.',
  16f033ca-2b2c-4745-a537-82999209774c, 'Steve Wozniak',
  11111111-1111-1111-1111-111111111111, 'Riverside Commons', 'Completed', '2026-06-10 10:00:00',
  ['repair culture', 'skill sharing'], 9, 'Community Tool Library', 'tools');

INSERT INTO services (service_id, type, title, description, provider_id, provider_name, sphere_id, sphere_name, status, created_at, values, likes, project_name, image_key)
VALUES (cccccccc-0000-0000-0000-000000000006, 'request',
  'Seeking open datasets for community climate models',
  'Our open research team needs well-labelled climate datasets to train shared forecasting models. Any contribution to the commons welcome.',
  86eb2b6c-1771-4533-9bd8-fca4f83fe61a, 'Bill Gates',
  22222222-2222-2222-2222-222222222222, 'AI Commons', 'Posted', '2026-06-23 11:00:00',
  ['open research', 'knowledge sharing'], 6, 'Open GPU Cluster', 'default');
