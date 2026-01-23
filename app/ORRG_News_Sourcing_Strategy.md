# News Events Sourcing Strategy

## Purpose

This document defines the sourcing strategy for **news-driven world events** displayed in the Open Range Ring Generator (ORRG).  
The goal is to provide **situational awareness**, not ground truth, by aggregating, labeling, and contextualizing global reporting on missile launches, tests, and strategic events.

This strategy explicitly separates **reporting**, **analysis**, and **user-driven interpretation**.

---

## Core Principles

1. **Plurality over authority**  
   No single source is treated as definitive. Events are contextualized through multiple perspectives.

2. **Attribution over assertion**  
   All events retain their original source attribution and confidence framing.

3. **Metadata over narrative**  
   The system normalizes metadata, not political or strategic conclusions.

4. **User-driven analysis**  
   News events inform analysis; they do not drive analytical outputs automatically.

5. **Transparency by design**  
   Every event carries source type and confidence labeling.

---

## Source Tiers

### Tier 1 – Global Event Backbone

These sources provide high-volume, location-aware event detection.

**Characteristics**
- Machine-ingestible
- Frequent updates
- Broad global coverage

**Use**
- Primary discovery of relevant geopolitical and military-related events
- Geographic anchoring for the world map

---

### Tier 2 – International News Agencies

These sources provide timely, relatively neutral reporting.

**Characteristics**
- Rapid publication
- Professional editorial standards
- Text-centric content

**Use**
- News feed cards
- Article detail popups
- Contextual summaries

---

### Tier 3 – Foreign Government & Military Sources

These sources provide official self-reported statements.

**Characteristics**
- Primary-source declarations
- Politically framed
- Variable transparency

**Use**
- Source-of-record for a country’s own claims
- Clearly labeled as self-reported
- Never treated as verification

---

### Tier 4 – Multilateral & Research Organizations

These sources provide slower, analytical context.

**Characteristics**
- High credibility
- Low frequency
- Often retrospective

**Use**
- Validation markers
- Analyst reference material
- Weapon system and range classification context

---

### Tier 5 – OSINT & Community Sources (Optional)

These sources provide early signals but carry uncertainty.

**Characteristics**
- Fast but noisy
- Unverified
- Non-uniform structure

**Use**
- Analyst-only awareness
- Clearly labeled as unverified
- Never auto-linked to analysis

---

## Confidence and Labeling Model

Every news event ingested into the system must include:

- **Source Type**
  - International News
  - Government (Self-Reported)
  - Government (Third-Party)
  - Multilateral Organization
  - OSINT / Community

- **Confidence Language**
  - Reported
  - Official Statement
  - Multiple Independent Reports
  - Unverified Claim

The system does **not** label events as confirmed or factual.

---

## Article-to-Metadata Summarization

When a user selects an article, an LLM may be used to extract **structured metadata**, not conclusions.

Extracted metadata may include:
- Event type (launch, test, exercise, statement)
- Reporting country
- Mentioned locations
- Mentioned weapon names (if explicit)
- Range descriptors (e.g., short-range, intercontinental)
- Ambiguity notes

If an article lacks technical detail, the system must state this explicitly.

---

## Integration with Analytical Tools

- News events **never auto-generate** analytical outputs.
- Extracted metadata may pre-fill **optional** fields.
- Users must explicitly choose:
  - Tool type
  - Weapon system (if any)
  - Range values

This ensures analytical intent remains user-controlled.

---

## Ethical and Operational Safeguards

- No event is treated as verification.
- Simulated or analytical outputs are always labeled as independent of reporting.
- Foreign government claims are clearly identified as self-reported.
- Analyst-only features expose uncertainty rather than hide it.

---

## Intended Outcome

This sourcing strategy ensures ORRG provides:
- Global situational awareness
- Transparent attribution
- Analyst-grade context
- Responsible use of automated summarization

without overstating certainty or conflating reporting with analysis.

---

## Status

This document represents the finalized baseline for **news event sourcing and integration** within ORRG.
