# MAZU Competition App Design System

## Product intent

The primary users are competition judges and the presenter operating the local
application. A judge should understand within 10–20 seconds that the product:

1. runs a historical warning exercise from a city, date and hazard;
2. produces a model result with rule and uncertainty checks;
3. exposes its evidence and scientific boundaries; and
4. exports submission-ready artifacts.

The interface must never resemble an operational warning console. Historical
data, proxy-label validation and `Exercise` status remain visible.

## Information architecture

| Page | Primary question | First-screen output |
|---|---|---|
| Historical warning exercise | What should I run? | Compact task form and current risk bulletin |
| Event diagnostics | Why did the run produce this result? | Event summary and probability field |
| Evidence network | Where does the explanation come from? | Relationship graph and in-canvas node feedback |
| Decision brief | What should a reviewer conclude? | Finding, probability, drivers and cross-check |
| Submission artifacts | What can I export or submit? | Report, evidence package and CAP Exercise actions |

The current exercise is a global context object. Its city, hazard and date stay
visible in the top bar across all five routes.

## Design tokens

The implementation keeps hue tokens for compatibility and adds semantic roles:

- `--page`: application background.
- `--surface-raised`: primary working surface.
- `--brand`: navigation and identity.
- `--action`: interactive confirmation and links.
- `--risk-high`: elevated-risk state only.
- `--info`: model and analytical information.
- `--success`: ready, consistent or verified state.
- `--focus`: keyboard focus indication.

Risk colour is never used as decoration. Teal represents analysis or available
capability; amber represents review; red represents elevated risk.

## Layout and responsive behaviour

- Above 900 px, the application uses the full sidebar workspace.
- At 900 px and below, navigation becomes a 70 px bottom bar so a competition
  window does not lose content width to a collapsed sidebar.
- At 620 px and below, forms and artifact cards become single-column.
- Page titles name the task directly. Explanatory claims remain subtitles.
- Core outputs precede supporting detail; long audit registers use progressive
  disclosure below the main visual.

## Accessibility

- Body copy targets 14–15 px; compact metadata is not smaller than 9–10 px.
- All interactive elements have a visible `focus-visible` outline.
- Mobile interactive targets must be at least 24 px in both dimensions; primary
  controls and bottom navigation target larger touch areas.
- Colour is supported by text labels and status words.
- Network nodes are native buttons and the selected node is announced through
  an `aria-live` feedback card.
- Chinese and English use the same hierarchy without fixed text-height clipping.

## Validation contract

Before competition handoff:

- all five routes must have no document-level horizontal overflow at 390 px;
- the 656 px competition window must use bottom navigation;
- the console must show input and current risk bulletin in the first viewport;
- diagnostics must show model, rule, spread and consistency before the map;
- node selection must provide visible feedback inside the graph;
- reports, evidence and CAP Exercise must be visually distinct artifacts; and
- the browser console must contain no warnings or errors.
