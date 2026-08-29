# Output schema versioning

Public model rows and matrix envelopes carry a `schema_version` string. JSON Schemas live in
`schemas/` and use JSON Schema Draft 2020-12.

- Patch releases may add optional fields without changing the schema version.
- Removing or renaming a field, changing its meaning, or changing an output envelope requires a new
  major schema version.
- Readers should reject unknown major versions and may ignore unknown optional fields within a known
  version.

Version 1.0 introduced explicit row versions and `{schema_version, data}` envelopes for correlation
and observation matrices. Legacy unversioned matrices can be migrated by wrapping their former
top-level mapping as the `data` value and setting `schema_version` to `1.0`.
