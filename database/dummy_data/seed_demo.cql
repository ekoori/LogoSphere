-- ============================================================================
-- LogoSphere — demo seed data
-- A small but coherent story showing what LogoSphere stands for:
--   a gift economy (give freely, build trust), communities (Spheres),
--   collectives (Alliances), shared missions (Projects), and a Meaning Trail that
--   records moments of trust between neighbours.
--
-- Reuses the 20 seeded users (passwords = first name). Demo login:
--   joe.rogan@example.com / Joe   — his Meaning Trail is the centrepiece.
-- ============================================================================

USE logosphere;

-- ---- Spheres (communities) -------------------------------------------------
INSERT INTO spheres (sphere_id, name, description, meaning_graph, location, admin1, created_at, participants, alliances, projects, values)
VALUES (11111111-1111-1111-1111-111111111111,
  'Riverside Commons',
  'A solarpunk neighbourhood where tools, time and skills are shared freely. We grow food, repair what breaks, and look after one another — no money changes hands, only trust.',
  '#mutualaid #repair #gardens #localfirst',
  'Riverside',
  fe878ccf-aba7-4b16-8b5f-847f7db6e0ad,
  '2026-01-12 09:00:00',
  [fe878ccf-aba7-4b16-8b5f-847f7db6e0ad, 9c89c702-6c61-49c8-9f0c-47b8e4e84e4b, 16f033ca-2b2c-4745-a537-82999209774c, aeeb7c42-d2d5-4e4e-8ed3-af313f5d6358, ff52c318-95e0-4f1f-89cc-62551c814a83],
  ['Repair Café Collective', 'Seed Keepers Alliance'],
  ['Community Tool Library', 'Neighbourhood Solar Microgrid'],
  ['mutual aid', 'repair culture', 'food sovereignty', 'trust']);

INSERT INTO spheres (sphere_id, name, description, meaning_graph, location, admin1, created_at, participants, alliances, projects, values)
VALUES (22222222-2222-2222-2222-222222222222,
  'AI Commons',
  'A sphere pooling open compute and knowledge so that powerful AI research is a public good, not a private moat. Members share GPUs, datasets and mentorship in the spirit of the gift.',
  '#opencompute #knowledgecommons #ai',
  'Distributed',
  b4dfd93d-a9e0-4bf8-8685-735dbde17ff7,
  '2026-02-03 12:00:00',
  [b4dfd93d-a9e0-4bf8-8685-735dbde17ff7, 86eb2b6c-1771-4533-9bd8-fca4f83fe61a, 7d6e67f2-5c64-4175-8330-a0d1b2b9c45f, fe878ccf-aba7-4b16-8b5f-847f7db6e0ad],
  ['Open Compute Guild'],
  ['Open GPU Cluster'],
  ['open source', 'knowledge sharing', 'compute as commons']);

INSERT INTO spheres (sphere_id, name, description, meaning_graph, location, admin1, created_at, participants, alliances, projects, values)
VALUES (33333333-3333-3333-3333-333333333333,
  'Earthsong Gardens',
  'A regenerative growing community restoring soil and pollinators. We swap heirloom seeds, share harvests, and govern the land together through liquid democracy.',
  '#regenerative #seeds #pollinators #biodiversity',
  'Greenvale',
  aeeb7c42-d2d5-4e4e-8ed3-af313f5d6358,
  '2026-03-21 08:00:00',
  [aeeb7c42-d2d5-4e4e-8ed3-af313f5d6358, ff52c318-95e0-4f1f-89cc-62551c814a83, 9c89c702-6c61-49c8-9f0c-47b8e4e84e4b],
  ['Seed Keepers Alliance'],
  ['Pollinator Corridor'],
  ['regeneration', 'biodiversity', 'stewardship']);

-- ---- Alliances (collectives within spheres) --------------------------------
INSERT INTO alliances (alliance_id, name, description, admin1, sphere_id, sphere_name, created_at, members, member_names, projects, values, meaning_graph)
VALUES (aaaaaaaa-0000-0000-0000-000000000001,
  'Repair Café Collective',
  'Neighbours who fix things together every Saturday — bikes, toasters, fences, friendships. Knowledge is shared, never sold.',
  16f033ca-2b2c-4745-a537-82999209774c,
  11111111-1111-1111-1111-111111111111, 'Riverside Commons',
  '2026-01-20 10:00:00',
  [16f033ca-2b2c-4745-a537-82999209774c, fe878ccf-aba7-4b16-8b5f-847f7db6e0ad, 9c89c702-6c61-49c8-9f0c-47b8e4e84e4b],
  ['Steve Wozniak', 'Joe Rogan', 'Marie Kondo'],
  ['Community Tool Library'],
  ['repair culture', 'skill sharing'],
  '#repair #skillshare');

INSERT INTO alliances (alliance_id, name, description, admin1, sphere_id, sphere_name, created_at, members, member_names, projects, values, meaning_graph)
VALUES (aaaaaaaa-0000-0000-0000-000000000002,
  'Open Compute Guild',
  'Stewards of the shared GPU cluster. We allocate compute by need and contribution, decided by the members themselves.',
  86eb2b6c-1771-4533-9bd8-fca4f83fe61a,
  22222222-2222-2222-2222-222222222222, 'AI Commons',
  '2026-02-10 14:00:00',
  [86eb2b6c-1771-4533-9bd8-fca4f83fe61a, b4dfd93d-a9e0-4bf8-8685-735dbde17ff7, 7d6e67f2-5c64-4175-8330-a0d1b2b9c45f],
  ['Bill Gates', 'Elon Musk', 'Stephen Hawking'],
  ['Open GPU Cluster'],
  ['open compute', 'fair allocation'],
  '#compute #governance');

INSERT INTO alliances (alliance_id, name, description, admin1, sphere_id, sphere_name, created_at, members, member_names, projects, values, meaning_graph)
VALUES (aaaaaaaa-0000-0000-0000-000000000003,
  'Seed Keepers Alliance',
  'Guardians of heirloom seed diversity. Members save, label and swap seeds so no variety is lost.',
  ff52c318-95e0-4f1f-89cc-62551c814a83,
  33333333-3333-3333-3333-333333333333, 'Earthsong Gardens',
  '2026-03-25 09:30:00',
  [ff52c318-95e0-4f1f-89cc-62551c814a83, aeeb7c42-d2d5-4e4e-8ed3-af313f5d6358],
  ['Emma Watson', 'David Attenborough'],
  ['Pollinator Corridor'],
  ['seed sovereignty', 'biodiversity'],
  '#seeds #biodiversity');

-- ---- Projects (shared missions) --------------------------------------------
INSERT INTO projects (project_id, name, description, owner, owner_alliance, status, sphere_id, sphere_name, created_at, participants, participant_names, values)
VALUES (bbbbbbbb-0000-0000-0000-000000000001,
  'Community Tool Library',
  'A free lending library of power tools, garden equipment and know-how. Borrow what you need, return it cared-for, teach the next person.',
  'Steve Wozniak', 'Repair Café Collective', 'In Progress',
  11111111-1111-1111-1111-111111111111, 'Riverside Commons',
  '2026-02-01 10:00:00',
  [16f033ca-2b2c-4745-a537-82999209774c, fe878ccf-aba7-4b16-8b5f-847f7db6e0ad, 9c89c702-6c61-49c8-9f0c-47b8e4e84e4b],
  ['Steve Wozniak', 'Joe Rogan', 'Marie Kondo'],
  ['sharing over owning', 'repair culture']);

INSERT INTO projects (project_id, name, description, owner, owner_alliance, status, sphere_id, sphere_name, created_at, participants, participant_names, values)
VALUES (bbbbbbbb-0000-0000-0000-000000000002,
  'Neighbourhood Solar Microgrid',
  'Rooftop panels feeding a shared battery so the block keeps the lights on together. Surplus energy is gifted to households that need it most.',
  'Joe Rogan', 'Repair Café Collective', 'Initiated',
  11111111-1111-1111-1111-111111111111, 'Riverside Commons',
  '2026-04-05 11:00:00',
  [fe878ccf-aba7-4b16-8b5f-847f7db6e0ad, 16f033ca-2b2c-4745-a537-82999209774c],
  ['Joe Rogan', 'Steve Wozniak'],
  ['energy as commons', 'resilience']);

INSERT INTO projects (project_id, name, description, owner, owner_alliance, status, sphere_id, sphere_name, created_at, participants, participant_names, values)
VALUES (bbbbbbbb-0000-0000-0000-000000000003,
  'Open GPU Cluster',
  'A community-run cluster of donated GPUs for open AI research. Time is allocated by the Open Compute Guild through transparent, member-led voting.',
  'Elon Musk', 'Open Compute Guild', 'In Progress',
  22222222-2222-2222-2222-222222222222, 'AI Commons',
  '2026-02-15 13:00:00',
  [b4dfd93d-a9e0-4bf8-8685-735dbde17ff7, 86eb2b6c-1771-4533-9bd8-fca4f83fe61a, fe878ccf-aba7-4b16-8b5f-847f7db6e0ad],
  ['Elon Musk', 'Bill Gates', 'Joe Rogan'],
  ['open research', 'compute commons']);

INSERT INTO projects (project_id, name, description, owner, owner_alliance, status, sphere_id, sphere_name, created_at, participants, participant_names, values)
VALUES (bbbbbbbb-0000-0000-0000-000000000004,
  'Pollinator Corridor',
  'A ribbon of wildflower meadows linking gardens across the valley so bees and butterflies can travel safely. Planted and tended by volunteers.',
  'David Attenborough', 'Seed Keepers Alliance', 'Completed',
  33333333-3333-3333-3333-333333333333, 'Earthsong Gardens',
  '2026-03-28 08:30:00',
  [aeeb7c42-d2d5-4e4e-8ed3-af313f5d6358, ff52c318-95e0-4f1f-89cc-62551c814a83],
  ['David Attenborough', 'Emma Watson'],
  ['biodiversity', 'stewardship']);

-- ---- Openings (offers & needs in the gift economy) -------------------
INSERT INTO services (service_id, type, title, description, provider_id, provider_name, sphere_id, sphere_name, status, created_at, values)
VALUES (cccccccc-0000-0000-0000-000000000001, 'offer',
  'Free podcasting & audio workshop',
  'I will teach anyone who is curious how to record, edit and publish a podcast. Bring your story; the gear is provided.',
  fe878ccf-aba7-4b16-8b5f-847f7db6e0ad, 'Joe Rogan',
  11111111-1111-1111-1111-111111111111, 'Riverside Commons', 'Posted', '2026-06-20 10:00:00',
  ['skill sharing', 'storytelling']);

INSERT INTO services (service_id, type, title, description, provider_id, provider_name, sphere_id, sphere_name, status, created_at, values)
VALUES (cccccccc-0000-0000-0000-000000000002, 'need',
  'Hands needed for Saturday fence rebuild',
  'The community garden fence came down in the storm. Looking for a few neighbours to help rebuild it this Saturday — lunch is on the garden.',
  9c89c702-6c61-49c8-9f0c-47b8e4e84e4b, 'Marie Kondo',
  11111111-1111-1111-1111-111111111111, 'Riverside Commons', 'Open', '2026-06-22 08:00:00',
  ['mutual aid', 'gardens']);

INSERT INTO services (service_id, type, title, description, provider_id, provider_name, sphere_id, sphere_name, status, created_at, values)
VALUES (cccccccc-0000-0000-0000-000000000003, 'offer',
  '7x H100 GPUs for open research',
  'Donating time on seven H100 GPUs to any open, non-commercial AI project. Allocated through the Open Compute Guild.',
  b4dfd93d-a9e0-4bf8-8685-735dbde17ff7, 'Elon Musk',
  22222222-2222-2222-2222-222222222222, 'AI Commons', 'Posted', '2026-06-18 15:00:00',
  ['open compute', 'generosity']);

INSERT INTO services (service_id, type, title, description, provider_id, provider_name, sphere_id, sphere_name, status, created_at, values)
VALUES (cccccccc-0000-0000-0000-000000000004, 'offer',
  'Heirloom seeds to share',
  'Tomato, bean and squash seeds saved from this years harvest. Take what you will grow; bring some back next season.',
  ff52c318-95e0-4f1f-89cc-62551c814a83, 'Emma Watson',
  33333333-3333-3333-3333-333333333333, 'Earthsong Gardens', 'Posted', '2026-06-15 09:00:00',
  ['seed sovereignty', 'generosity']);

-- ============================================================================
-- Joe Rogan's Meaning Trail — the heart of the demo.
-- Each row is a moment of trust: a gift given or received, sometimes followed
-- by a gratitude note (a Receipt) or a public Acknowledgement.
-- ============================================================================

-- 1) Rebuilt the community garden fence with Marie Kondo (completed, receipted)
INSERT INTO meaning_trail (user_id, interaction_id, other_user_id, other_user_name,
  interaction_description, interaction_status, project_id, project_name, project_start_timestamp,
  gratitude_comment, gratitude_comment_id, gratitude_comment_timestamp,
  other_comment, other_comment_author_id, other_comment_author_name, other_comment_id, other_comment_timestamp)
VALUES (fe878ccf-aba7-4b16-8b5f-847f7db6e0ad, 10000000-0000-0000-0000-000000000001,
  9c89c702-6c61-49c8-9f0c-47b8e4e84e4b, 'Marie Kondo',
  'Rebuilt the community garden fence after the spring storm', 'Receipted',
  bbbbbbbb-0000-0000-0000-000000000001, 'Community Tool Library', '2026-05-02 09:00:00',
  'Joe showed up at dawn with his own tools and stayed until every post was solid. The garden is safe again because of him.',
  20000000-0000-0000-0000-000000000001, '2026-05-04 18:00:00',
  'Could not have done this without Marie organising the whole crew. True community spirit.',
  9c89c702-6c61-49c8-9f0c-47b8e4e84e4b, 'Marie Kondo', 30000000-0000-0000-0000-000000000001, '2026-05-04 19:00:00');

-- 2) Shared 7 H100 GPUs with the Open GPU Cluster (in progress)
INSERT INTO meaning_trail (user_id, interaction_id, other_user_id, other_user_name,
  interaction_description, interaction_status, project_id, project_name, project_start_timestamp,
  gratitude_comment, gratitude_comment_id, gratitude_comment_timestamp)
VALUES (fe878ccf-aba7-4b16-8b5f-847f7db6e0ad, 10000000-0000-0000-0000-000000000002,
  b4dfd93d-a9e0-4bf8-8685-735dbde17ff7, 'Elon Musk',
  'Offered 7 H100 GPUs to the Open GPU Cluster for open research', 'In Progress',
  bbbbbbbb-0000-0000-0000-000000000003, 'Open GPU Cluster', '2026-06-01 12:00:00',
  'Joe pledged serious compute to the commons, no strings attached. This unblocks three research teams.',
  20000000-0000-0000-0000-000000000002, '2026-06-02 10:00:00');

-- 3) Taught a free podcasting workshop (completed, acknowledgement)
INSERT INTO meaning_trail (user_id, interaction_id, other_user_id, other_user_name,
  interaction_description, interaction_status, project_name, project_start_timestamp,
  other_comment, other_comment_author_id, other_comment_author_name, other_comment_id, other_comment_timestamp)
VALUES (fe878ccf-aba7-4b16-8b5f-847f7db6e0ad, 10000000-0000-0000-0000-000000000003,
  ff52c318-95e0-4f1f-89cc-62551c814a83, 'Emma Watson',
  'Ran a free podcasting & audio workshop at Riverside Commons', 'Finished', 'Skill Share', '2026-06-10 17:00:00',
  'I came in knowing nothing and left having recorded my first episode. Joe gives his time so generously.',
  ff52c318-95e0-4f1f-89cc-62551c814a83, 'Emma Watson', 30000000-0000-0000-0000-000000000003, '2026-06-12 20:00:00');

-- 4) Received carpentry mentorship from Steve Wozniak (completed, Joe's thanks)
INSERT INTO meaning_trail (user_id, interaction_id, other_user_id, other_user_name,
  interaction_description, interaction_status, project_id, project_name, project_start_timestamp,
  user_comment, user_comment_id, user_comment_timestamp)
VALUES (fe878ccf-aba7-4b16-8b5f-847f7db6e0ad, 10000000-0000-0000-0000-000000000004,
  16f033ca-2b2c-4745-a537-82999209774c, 'Steve Wozniak',
  'Learned joinery and tool restoration from Steve at the Repair Café', 'Finished',
  bbbbbbbb-0000-0000-0000-000000000001, 'Community Tool Library', '2026-04-18 10:00:00',
  'Steve is endlessly patient. He taught me to sharpen a plane and to value fixing over buying. Paying it forward next week.',
  40000000-0000-0000-0000-000000000004, '2026-04-25 16:00:00');

-- 5) Helping start the Neighbourhood Solar Microgrid (initiated)
INSERT INTO meaning_trail (user_id, interaction_id, other_user_id, other_user_name,
  interaction_description, interaction_status, project_id, project_name, project_start_timestamp)
VALUES (fe878ccf-aba7-4b16-8b5f-847f7db6e0ad, 10000000-0000-0000-0000-000000000005,
  16f033ca-2b2c-4745-a537-82999209774c, 'Steve Wozniak',
  'Kicked off the Neighbourhood Solar Microgrid — mapping rooftops this month', 'Initiated',
  bbbbbbbb-0000-0000-0000-000000000002, 'Neighbourhood Solar Microgrid', '2026-06-24 09:00:00');
