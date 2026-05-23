# 摄入登记地图

- memory_core/project-map/**: incoming-raw
- memory_core/memory/kb/global/**: active-legal
- memory_core/memory/kb/projects/**: compatibility-only
- memory_core/memory/docs/**: incoming-raw
- memory_core/memory/log/**: incoming-raw
- memory_core/projects/**: incoming-raw
- memory_core/tools/**: incoming-raw
- tests/**: incoming-raw
- 状态：`absorbed`，`retired`
- 同次 `git commit` 提交后才生效

---

<!-- LEGACY_SOURCE_REGISTRATION_BEGIN
Source: workspace/memory
Archived-Source: history-projects/memory/retired-workspace-memory-20260513-043734/memory
Source: workspace/project-map
Archived-Source: history-projects/memory/retired-workspace-memory-20260513-043734/project-map
Migrated: 2026-05-13T12:18:03Z
Action: retire-legacy-workspace-sources
Status: RETIRED/ARCHIVED

This section registers the following legacy sources as retired, archived references. These sources are NOT granted active-legal status.

1. workspace/memory/** - Legacy memory workspace content
   - Status: RETIRED/ARCHIVED
   - Not active-legal; preserved for historical reference only
   - Active KB content has been merged to memory/kb/** with source markers

2. workspace/project-map/** - Legacy project-map workspace content
   - Status: RETIRED/ARCHIVED
   - Not active-legal; preserved for historical reference only
   - Current legal project-map is at project-map/** (this directory)

These registrations ensure legacy sources are tracked without granting
active-legal status that would conflict with the new memory-core directory rules.

LEGACY_SOURCE_REGISTRATION_END -->

---

<!-- WORKSPACE_ROOT_RETIREMENT_BEGIN
Source: workspace/**
Archived-Source: history-projects/workspace/retired-workspace-20260513-051059
Migrated: 2026-05-13T05:11:00.307267+00:00
Action: retire-workspace-root
Status: RETIRED/ARCHIVED

The root workspace directory is retired under latest memory-core rules. It is NOT an active entrypoint.
Current legal entrypoints remain `.memory/`, `memory/`, `project-map/`, `artifacts/`, and `history-projects/`.
WORKSPACE_ROOT_RETIREMENT_END -->

---

<!-- LEGACY_MEMORY_INGESTION_BEGIN
Source: history-projects/workspace/retired-workspace-20260513-051059/frontstage/memory-legacy-quarantine-2026-04-12/memory
Migrated: 2026-05-13T05:17:11.456485+00:00
Action: ingest-legacy-memory-into-current-memory
Status: ABSORBED/CURRENT
Files-Handled: 54

Legacy memory content was copied into the current legal `memory/` tree. Conflicting files were preserved with `.legacy-<sha>` suffix instead of overwriting active content.
LEGACY_MEMORY_INGESTION_END -->

---

<!-- LEGACY_KB_INGESTION_BEGIN
Source: history-projects/workspace/retired-workspace-20260513-051059/frontstage/memory-legacy-quarantine-2026-04-12/kb
Migrated: 2026-05-13T05:26:22.505344+00:00
Action: ingest-legacy-kb-into-current-memory
Status: ABSORBED/CURRENT
Files-Handled: 14

Legacy KB content was copied into the current legal `memory/` tree. Global KB candidates went to `memory/kb/global/`, project KB to `memory/kb/projects/`, and legacy index/version/conflict records to `memory/docs/legacy-kb/`. Conflicting files were preserved with `.legacy-<sha>` suffix instead of overwriting active content.
LEGACY_KB_INGESTION_END -->

---

<!-- RETIRED_WORKSPACE_FULL_INGESTION_BEGIN
Source: history-projects/workspace/retired-workspace-20260513-051059
Migrated: 2026-05-13T05:30:01.207619+00:00
Action: ingest-retired-workspace-remaining-content
Status: ABSORBED/CURRENT-OR-ARTIFACT
Files-Handled: 3965
Files-Skipped-Cache: 37

Remaining retired workspace content was copied into legal current locations without recreating `workspace/`: root state went to `memory/docs/legacy-workspace-root/`, runtime logs to `artifacts/runtime/legacy-workspace-log/`, frontstage/source material to `artifacts/workspace-ingested/frontstage/`, tools to `tools/`, and project assets to `projects/`. Conflicting files were preserved with `.legacy-<sha>` suffix instead of overwriting active content.
RETIRED_WORKSPACE_FULL_INGESTION_END -->

---

<!-- LEGACY_CONFLICT_CONSOLIDATION_BEGIN
Migrated: 2026-05-13T05:50:41.179122+00:00
Action: consolidate-legacy-conflict-files
Status: ABSORBED/REGISTERED
Registry: memory/docs/legacy-conflicts/registry.md
Originals: memory/docs/legacy-conflicts/originals/
Files-Handled: 9

Legacy conflict sidecar files were registered and moved out of active paths. Non-conflicting docs index rules were extracted into `memory/docs/INDEX.md`; superseded project stubs and old state files remain preserved as traceable originals, not active truth.
LEGACY_CONFLICT_CONSOLIDATION_END -->

---

<!-- LEGACY_CONFLICT_ORIGINALS_RETIREMENT_BEGIN
Migrated: 2026-05-13T05:54:12.842826+00:00
Action: move-legacy-conflict-originals-to-history
Status: RETIRED/ARCHIVED
Source: memory/docs/legacy-conflicts/originals
Archived-Source: history-projects/legacy-conflicts/originals-20260513-055650
Files-Handled: 9

Legacy conflict original sidecar files were moved out of active `memory/` into `history-projects/`; active memory keeps only the registry and absorbed summaries.
LEGACY_CONFLICT_ORIGINALS_RETIREMENT_END -->

---

<!-- ACTIVE_MEMORY_DRIFT_CLEANUP_BEGIN
Migrated: 2026-05-13T06:11:00.014821+00:00
Action: clean-active-memory-drift
Status: CLEANED/CURRENT
Files-Moved: 16
Files-Rewritten: 17

Historical legacy registries, legacy KB copies, old workspace root state, old corrections, old inventory, and historical markdown logs were moved out of active `memory/` into `history-projects/`. Remaining active memory files had retired workspace path references rewritten to current legal paths where safe.
ACTIVE_MEMORY_DRIFT_CLEANUP_END -->

---

<!-- ACTIVE_MEMORY_DRIFT_REFERENCE_CLEANUP_BEGIN
Migrated: 2026-05-13T06:11:50.156721+00:00
Action: final-active-memory-drift-reference-cleanup
Status: CLEANED/CURRENT
Files-Rewritten: 2

Final active memory drift references were removed or redirected to current/history paths.
ACTIVE_MEMORY_DRIFT_REFERENCE_CLEANUP_END -->

---

<!-- ROOT_DOCS_INGESTION_BEGIN
Source: docs/**
Archived-Source: history-projects/root-docs/retired-root-docs-20260513-063519
Migrated: 2026-05-13T06:35:19.169277+00:00
Action: ingest-and-retire-root-docs
Status: ABSORBED/CURRENT
Target: memory/docs/root-docs-ingested/
Files-Handled: 84
Symlinks-Recorded: 4
Files-Skipped-Cache: 1

Root-level `docs/` was retired as an active document entrypoint. Regular files were copied into current `memory/docs/root-docs-ingested/`; legacy symlinks were recorded but not recreated; the original directory was archived under `history-projects/`.
ROOT_DOCS_INGESTION_END -->

---

<!-- DOCUMENT_ENTRYPOINT_GOVERNANCE_BEGIN
Migrated: 2026-05-13T06:36:37.045733+00:00
Action: govern-remaining-doc-entrypoints
Status: CLEANED/CURRENT
Files-Handled: 4

Remaining document-like entrypoints were classified: script audit reports moved to `artifacts/reports/`, tool/package README documentation moved into `memory/docs/`, and cache README moved to `history-projects/cache/`. Root `AGENTS.md`, `CLAUDE.md`, `INDEX.md`, project-owned AEdu docs, and skill/package source-owned files remain governed by their owning entrypoint surfaces.
DOCUMENT_ENTRYPOINT_GOVERNANCE_END -->

---

<!-- ROOT_DOCS_DRIFT_REFERENCE_CLEANUP_BEGIN
Migrated: 2026-05-13T06:37:20.385064+00:00
Action: rewrite-memory-docs-workspace-drift-after-root-docs-ingestion
Status: CLEANED/CURRENT
Files-Rewritten: 46

Workspace path references introduced via root docs ingestion were rewritten to current legal paths where safe.
ROOT_DOCS_DRIFT_REFERENCE_CLEANUP_END -->
---

<!-- ARTIFACT_ROOT_DOC_GOVERNANCE_BEGIN
Migrated: 2026-05-13T09:20:00+00:00
Action: govern-artifacts-root-markdown-entrypoints
Status: CLEANED/CURRENT
Files-Handled: 5

Artifact-root markdown reports/runbooks/plans were moved under typed `artifacts/reports/` subdirectories. The `artifacts/` root remains an allowed artifact entrypoint, but markdown report-like files should live below governed report buckets rather than as loose root artifact documents.
ARTIFACT_ROOT_DOC_GOVERNANCE_END -->

