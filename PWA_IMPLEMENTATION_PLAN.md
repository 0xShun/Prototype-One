# StudentSense PWA Implementation Plan

## Goal
Turn the existing Django web app into a mobile-friendly Progressive Web App (PWA) so it can be installed on phones and work better in low-connectivity situations.

## Recommended Architecture
- Keep Django as the backend and business logic layer.
- Use Django templates and static assets for the initial PWA rollout.
- Add a web app manifest and service worker for installability and offline support.
- Optionally expose API endpoints later through Django REST Framework if the app needs more mobile-specific functionality.

## Phase 1 - Foundation and Mobile UX
### Objectives
- Make the app feel usable on phones and tablets.
- Improve the most important user flows for mobile use.

### Tasks
- Refactor the main layout to be responsive.
- Improve navigation for small screens.
- Increase tap target sizes and reduce clutter.
- Prioritize these flows:
  - login
  - intake form
  - counselor dashboard
  - history and results pages
- Add a clean mobile-first visual structure using the existing Django templates.

### Deliverables
- Responsive templates
- Improved mobile layout
- Better mobile navigation

## Phase 2 - Installability
### Objectives
- Make the app installable on a phone home screen.

### Tasks
- Create a web app manifest with:
  - app name
  - short name
  - icons
  - theme color
  - background color
  - display mode
- Add the manifest link to the base template.
- Ensure the app is served over HTTPS.
- Register a service worker in the frontend.

### Deliverables
- Web app manifest
- Installable app experience on supported browsers

## Phase 3 - Offline Support
### Objectives
- Improve reliability for users with weak or intermittent internet access.

### Tasks
- Implement a service worker for caching static assets.
- Cache the app shell (CSS, JS, icons, key pages).
- Add offline fallback behavior for core screens.
- For forms, consider local draft storage if feasible.
- Use a simple caching strategy first:
  - cache static assets aggressively
  - use network-first or stale-while-revalidate for dynamic content

### Deliverables
- Faster repeat visits
- Basic offline support
- Better reliability on mobile networks

## Phase 4 - Performance and Polish
### Objectives
- Make the PWA feel fast and smooth on mobile devices.

### Tasks
- Optimize images and CSS.
- Reduce unnecessary page weight.
- Improve loading speed for key pages.
- Add loading states and better empty/error states.
- Test on common mobile devices and browsers.

### Deliverables
- Faster experience
- Cleaner mobile interaction patterns

## Phase 5 - Advanced Features (Optional)
### Objectives
- Expand the app beyond a basic PWA if the client wants more.

### Tasks
- Add push notifications for reminders or alerts.
- Add background sync for offline submissions.
- Consider a future move to a React Native app if the product grows significantly.

### Deliverables
- Optional engagement features
- Future-ready mobile architecture

## Implementation Order
1. Responsive mobile layout
2. Web app manifest
3. Service worker
4. Offline caching
5. Installability testing
6. Performance improvements
7. Optional notifications and advanced enhancements

## Acceptance Criteria
The PWA is considered successful when:
- the app works well on a phone screen
- users can install it to the home screen
- core pages load quickly and remain usable offline or with poor connectivity
- the experience feels close to a native mobile app without requiring a full rewrite

## Notes for Future AI Sessions
When continuing this work, prioritize the following:
- preserve the Django backend structure
- keep changes small and incremental
- focus first on mobile usability and installability
- avoid overengineering before the MVP is verified
