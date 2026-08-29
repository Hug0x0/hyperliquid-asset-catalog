# Market session policy

Daily return correlations are aligned on the local calendar date of the underlying reference
market. Crypto and explicitly 24/7 instruments use UTC. Known equity reference countries use an
IANA timezone; global commodities and unclassified markets fall back to UTC.

Holidays and missing sessions are not forward-filled. A pair contributes an observation only when
both markets have a return assigned to the same local session date. This prevents positional pairing
but does not attempt to infer an official exchange calendar or auction close. Exact exchange
calendars can be added later when reliable reference-exchange metadata is available.
