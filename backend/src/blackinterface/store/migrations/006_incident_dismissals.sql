-- Operator dismissals for open incidents (Module B, local workflow only).
--
-- This is NOT OneATS alarm acknowledgement. OAAlarm.Ack* is a write surface
-- and stays closed (I1). "Done" here means the operator has seen or handled
-- the incident in Black Interface — a local note, not a command to SCADA.
--
-- The payload is a JSON snapshot of IncidentOut at dismiss time so history
-- remains readable after the underlying alarms clear.
CREATE TABLE IF NOT EXISTS incident_dismissals (
    incident_id   TEXT NOT NULL,
    actor         TEXT NOT NULL,
    dismissed_at  TEXT NOT NULL,
    view_scope    TEXT NOT NULL DEFAULT '',
    payload       TEXT NOT NULL,
    PRIMARY KEY (incident_id, actor)
);

CREATE INDEX IF NOT EXISTS idx_incident_dismissals_actor_time
    ON incident_dismissals (actor, dismissed_at DESC);
