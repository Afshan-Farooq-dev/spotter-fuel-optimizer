# Frontend design direction

Research completed before implementation, 14 October 2026.

- [ElifTech Routes Management Dashboard](https://dribbble.com/shots/26768725-Routes-Management-Dashboard): map-led logistics hierarchy and compact route controls. Inspiration only; no proprietary assets or template code copied.
- [Tailwind Plus application layouts](https://tailwindcss.com/plus/ui-blocks/application-ui): clear application shells, restrained cards, consistent spacing. No paid components copied.
- [shadcn/ui sidebar](https://ui.shadcn.com/docs/components/base/sidebar) and [Vite setup](https://ui.shadcn.com/docs/installation/vite): accessible composable controls and source-owned components.
- [Google Maps](https://www.google.com/maps): familiar origin/destination flow, interactive route overview and contextual map markers.

Selected direction: a calm logistics workspace with an ink navy navigation rail, ivory surfaces, forest green route accents, small uppercase labels, and a large map beside a focused trip planner. Results sit above the map; a numbered fuel itinerary connects cards to map markers. Typography prioritizes legibility; no speculative fleet statistics, savings claims or fake charts.

All calculations come from Django. The verified example sets endpoint coordinates only. Empty states show no calculated metrics. Coverage failures have an explicit recovery path. Forms submit place text to backend geocoding; no unsupported autocomplete is implied.

Desktop uses a narrow rail, a fixed-width planner and a flexible map. Mobile stacks planner/results/map, preserving map controls and readable itinerary cards. Respect reduced motion and use keyboard-accessible components.

Map tiles use standard OpenStreetMap tiles with visible attribution, ordinary browser caching and no prefetch/offline downloads. See [tile policy](https://operations.osmfoundation.org/policies/tiles/). Production deployments must select a provider appropriate to their traffic. ORS keys stay on the backend. Vite proxies /api during development; production uses a same-origin reverse proxy.
