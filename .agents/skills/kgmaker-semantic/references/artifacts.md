# Semantic artifact and patch contracts

Use the actual manifest's `relations` and node IDs. Every edge cites a current
repository-relative `source_file`, exact `source_line`, and concise `evidence`.
EXTRACTED means an explicit source statement with score 1.0. INFERRED scores are
0.55, 0.65, 0.75, 0.85 or 0.95; AMBIGUOUS scores range from 0.1 to 0.3.
Do not promote heuristic calls into confirmed behavior.

Initial artifact shape (replace examples with verified current values):

```json
{
  "schema_version": 3,
  "files": {"docs/domain.md": "SHA-256 copied from the input manifest"},
  "nodes": [],
  "edges": [],
  "episodes": []
}
```

Copy the manifest's full `files` map. A concept has `id`, `name`, `source_file`,
`source_line`, `summary`. Its ID is `concept:<source_file>:<slug>`, where slug
lowercases the name, replaces runs of non-ASCII-alphanumeric characters with `_`,
and trims `_`. Edges have `source`, `target`, `kind`, `confidence`,
`confidence_score`, `source_file`, `source_line`, `evidence`. Endpoints must be
manifest node IDs or concepts defined in the artifact. Preserve existing valid
episodes and unrelated entries if updating an existing layer.

Incremental patch shape:

```json
{
  "schema_version": 1,
  "update_id": "exact current semantic-update.json update_id",
  "nodes": [],
  "edges": [],
  "remove_nodes": [],
  "remove_edges": []
}
```

New entries cite changed or previously affected files. Only packet-scoped entries
can be removed; `remove_edges` entries copy `source`, `target`, `kind` exactly.
Do not reuse an older patch. `semantic apply` performs the merge; do not replace
the whole semantic layer with an incremental patch. Validation errors require
source/schema correction, not fabricated evidence or broader confidence.
