-- ============================================================================
-- TrustSphere — schema extensions for Alliances, Projects and Openings services.
-- Idempotent-ish: uses IF NOT EXISTS where supported.
-- ============================================================================

-- Alliances: federations/partnerships of users, usually nested within a Sphere.
CREATE TABLE IF NOT EXISTS trustsphere.alliances (
    alliance_id uuid PRIMARY KEY,
    name text,
    description text,
    admin1 uuid,
    sphere_id uuid,
    sphere_name text,
    created_at timestamp,
    members list<uuid>,
    member_names list<text>,
    projects list<text>,
    values list<text>,
    value_graph text,
    image blob
);

-- Enrich the existing thin projects table (PRIMARY KEY project_id already exists).
ALTER TABLE trustsphere.projects ADD description text;
ALTER TABLE trustsphere.projects ADD status text;
ALTER TABLE trustsphere.projects ADD owner_alliance text;
ALTER TABLE trustsphere.projects ADD sphere_id uuid;
ALTER TABLE trustsphere.projects ADD sphere_name text;
ALTER TABLE trustsphere.projects ADD created_at timestamp;
ALTER TABLE trustsphere.projects ADD participants list<uuid>;
ALTER TABLE trustsphere.projects ADD participant_names list<text>;
ALTER TABLE trustsphere.projects ADD values list<text>;

-- Openings offers & requests.
CREATE TABLE IF NOT EXISTS trustsphere.services (
    service_id uuid PRIMARY KEY,
    type text,           -- 'offer' | 'need'
    title text,
    description text,
    provider_id uuid,
    provider_name text,
    sphere_id uuid,
    sphere_name text,
    status text,
    created_at timestamp,
    values list<text>
);
