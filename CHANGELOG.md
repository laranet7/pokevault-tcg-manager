# Changelog

This file records the functional evolution of PokeVault TCG starting from the current MVP.

Suggested format:

- `Added`: new functionality
- `Changed`: behavior or UX changes
- `Fixed`: bug fixes
- `Removed`: removed elements

## [Unreleased]

### Changed

- Heavy dialogs in card search, dashboard and collection detail are mounted on demand to reduce the initial frontend load without changing the main workflows.

### Fixed

- Expired authenticated sessions now clear the local session and redirect users to the login screen while preserving the intended destination route when possible.
- Login requests remain public even after a previous session has expired, preventing the login flow from being blocked by stale auth headers.
- Card search mode options are visible again from the main search view, including general search, code search, name search, promos and inventory.
- Add-to-collection and manual-card dialogs now load collections correctly the first time they are opened after lazy mounting.
- The price history modal now keeps the correct preset visually selected when it opens from dashboard movers, including the default `30D` state.
- Reverted a fragile frontend chunk-splitting strategy that interfered with PrimeVue interactive controls such as selects, mode pickers and form fields inside dialogs.

## [0.1.0-mvp] - 2026-06-25

### Added

- JWT authentication with login, own profile and forced password change.
- User management panel with access creation and editing.
- Per-user persistence of theme, dark/light mode, preset and colors in the browser.
- Card search by name, code, promo and general mode.
- Local inventory search without depending on a collection.
- Search fallback to TCGdex when Pokemon TCG API does not return results.
- Collection table view with modal-based creation and modal-based configuration.
- Collection deletion with confirmation.
- Per-collection toggle to sort by Pokedex number.
- Collection detail with card table, multi-select and movement between collections.
- Collection export to PDF and Excel.
- Manual card creation with custom image upload.
- Persistent local download and storage of card images.
- Enlarged card preview inside collections and inventory.
- Dashboard with collection valuation.
- Snapshot history and variation between valuations.

### Changed

- `My Profile` and `Users` were separated into distinct views.
- Top and side navigation were simplified to better align with PokeVault TCG.
- Login was adjusted to avoid preloading example credentials.
- The add-card dialog now remembers the last used collection and add preferences.
- Card loading now attempts to suggest finish and base price using available metadata.
- Dashboard collections are shown only when they contain cards.
- Collection valuation in the dashboard is sorted from highest to lowest value.
- The topbar now uses PokeVault TCG visual identity.

### Fixed

- Prevents price refresh from overwriting a valid previous manual value with `0` or an empty price.
- Fixes for code search with normalization of formats such as `001/165`.
- Fixes for promo results and special subsets.
- More robust handling of missing images from external APIs.
- Improvements to messaging and flow when moving cards between collections.
