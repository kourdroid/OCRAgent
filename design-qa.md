# Design QA — Light-first Ironclad redesign

## Comparison target

- Source visual truth: `C:\Users\Mehdi\AppData\Local\Temp\codex-clipboard-28c10ffd-df04-413d-a658-7c26d5c66bad.png`
- Source pixels: 1200 × 1800.
- Intended implementation viewport: desktop application shell; no density normalization applied because this is an intentional adaptation of the reference's light, clear data hierarchy, not a faithful dashboard clone.
- Implementation route inspected: `http://localhost:3000/dossiers`.
- State inspected: unauthenticated configuration guard.

## Evidence

The browser-rendered implementation reached the new light configuration guard with the text: “La connexion sécurisée doit être configurée avant l’accès à cet espace.” The authenticated `/dossiers` route could not be captured because the local environment did not provide a usable Supabase session.

## Review

- Fonts and typography: implemented with the existing Inter / JetBrains Mono pairing; visible login and guard copy is legible and uses a simple hierarchy.
- Spacing and layout rhythm: the accessible light guard state is centered with generous whitespace; authenticated route layout was not browser-verifiable.
- Colors and visual tokens: global light tokens, white surfaces, blue primary actions, and restrained semantic status colors were implemented.
- Image quality and assets: the source reference's retail illustration/avatar/decorative gradients were intentionally not copied because they do not represent Ironclad content. Existing Lucide icons remain used for standard interface actions.
- Copy and content: sign-in, navigation, dossier intake, and dossier review copy were simplified and translated to French.

## Findings

- [P1] Authenticated workflow visual capture is blocked.
  Location: `/dossiers`, `/dossiers/[id]`, `/admin`, and `/notifications`.
  Evidence: local browser is stopped at the Supabase configuration guard before those screens render.
  Impact: the new authenticated layouts cannot be judged against the reference at their actual desktop state.
  Fix: configure the local public Supabase URL/key and use a non-production pilot account, then capture dossier-list, upload, review, notification, and admin states at the same desktop viewport.

## Implementation checklist

1. Configure safe local Supabase credentials and a pilot session.
2. Capture the main authenticated screens and compare their spacing, tokens, navigation, table density, and interactions.
3. Translate remaining administration, notifications, and legacy validation strings.
4. Resolve any P0/P1/P2 issues found in the browser capture.

## Comparison history

- Iteration 1: source reference reviewed; implementation browser capture blocked before authentication. No visual fix can be responsibly assessed beyond the visible guard state.

final result: blocked
