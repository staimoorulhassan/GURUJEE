# ADR-002: Memory Retrieval Strategy

- **Status:** Accepted
- **Date:** 2026-04-11
- **Feature:** 001-gurujee-foundation
- **Context:** GURUJEE's Memory Agent stores all conversations and user facts in a local
  SQLite database. When the user speaks, the agent injects relevant memories into the LLM
  system prompt. The strategy must run entirely on-device with no external embedding API,
  stay under 50 MB RAM at idle (constitution P1), return results within 100 ms, and work
  with SQLite only — no vector databases. Sentence-transformers and any other embedding
  model are explicitly excluded from v1.

## Decision

**Use a Hybrid retrieval strategy (Option 4): recency-based retrieval for recent context
+ keyword/tag search for long-term facts.**

Implementation:

- **Short-term layer (recency)**: The last 10 conversation turns are always included in
  the injected context. Stored as a Python `deque(maxlen=10)` in RAM; serialised to
  `data/memory_short.json` on session end for continuity across restarts.

- **Long-term layer (keyword/tag search)**:
  - At write time, the Memory Agent extracts a small set of tags from each memory using a
    simple heuristic: proper nouns (capitalised words), explicit "remember" triggers, and
    a fixed category taxonomy (`person`, `place`, `preference`, `fact`, `task`).
  - Tags are stored in a `tags` column in the SQLite `memories` table (comma-separated
    string for simple `LIKE` queries without FTS extension).
  - At retrieval time, keywords are extracted from the user's current message using the
    same heuristic and matched against stored tags with a `WHERE tags LIKE ?` query.
  - Results are ranked by a composite score: `tag_match_count * 2 + recency_weight`,
    where `recency_weight` decays as `1 / (days_since_created + 1)`.
  - The top 5 long-term memories (by score) are injected alongside the short-term layer.

- **Total injected context per turn**: 10 recent turns + up to 5 long-term memories. This
  fits comfortably within the context window of the smallest supported model and stays
  well under the 50 MB idle RAM budget.

- **v2 upgrade path**: The `memories` table schema includes an `embedding BLOB` column
  (nullable) reserved for a future lightweight embedding model. When upgraded, the keyword
  search is replaced by cosine similarity over stored embeddings with no schema migration.

## Consequences

### Positive

- Zero dependency on any ML model at runtime; pure Python + SQLite.
- SQLite `LIKE` queries on a tag column complete in < 5 ms for up to 100 k rows on
  low-end ARM64 hardware.
- RAM footprint at idle: the `deque` holds ~10 short strings (< 1 KB); SQLite WAL is
  < 1 MB; net memory contribution is negligible against the 50 MB P1 ceiling.
- Explicit "remember" commands are reliably surfaced because they always receive the
  `fact` tag and a high importance score (written at the time of the command).
- The embedding upgrade path is non-breaking; the schema is forward-compatible.

### Negative

- Keyword/tag matching is lexical, not semantic. "I love hiking" will not surface when
  the user asks "what are my hobbies?" unless "hiking" or "hobbies" appears literally in
  the stored tags. **Mitigation**: the category taxonomy (`preference`) partially covers
  this; improve tagging heuristics iteratively before committing to embeddings.
- The recency layer always injects the last 10 turns regardless of relevance. In a very
  long session this may include low-value filler turns. **Mitigation**: a minimum
  message-length filter (> 20 chars) prunes trivial turns from the short-term store.
- Tag extraction is heuristic and will miss some facts (e.g., "my sister's wedding is
  in June" — no capitalised noun). **Mitigation**: explicit "remember" commands bypass
  heuristics; users can always force persistence.

## Alternatives Considered

**Option 1 — Recency-only (last N turns)**
- Pros: Simplest implementation; zero query overhead.
- Cons: Misses facts from sessions months ago. A user who said "I'm allergic to penicillin"
  six months ago would not have that fact injected into today's medical advice conversation.
  Rejected for a companion that promises to "remember everything."

**Option 2 — Keyword/tag search only**
- Pros: Lightweight; reliable for explicitly-tagged facts.
- Cons: Has no awareness of the immediate conversation flow. Without the last few turns,
  GURUJEE loses pronoun resolution and conversational coherence ("it", "that", "the one
  I mentioned"). Rejected on its own.

**Option 3 — TF-IDF on SQLite at query time**
- Pros: No tagging required; retrieval is based on term frequency across all stored
  memories.
- Cons: TF-IDF requires computing inverse document frequency across the entire corpus
  at query time (or maintaining a term index). For a growing personal memory store this
  becomes progressively heavier. Without SQLite FTS5, pure Python TF-IDF over thousands
  of rows could exceed 100 ms. Rejected for v1; viable as an Option 3.5 if the hybrid
  proves insufficient.

**Option 4 (chosen) — Hybrid recency + keyword/tag**
- Provides the best coverage within the on-device, no-ML, sub-50 MB constraints.

## References

- Feature Spec: specs/001-gurujee-foundation/spec.md (FR-006–FR-009)
- Related ADRs: ADR-001 (Skill Sandboxing Strategy)
- Constitution: P1 (memory footprint), P6 (Python-first)
- Evaluator Evidence: history/prompts/001-gurujee-core/001-gurujee-core-spec.spec.prompt.md
