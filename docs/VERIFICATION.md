# Verification - 8 October 2026

27 pytest cases passed: archive counts, source match values, terminal probabilities, invalid state ranges/types, unknown match, CSRF, cross-origin rejection, notebook session isolation, ownership deletion, player search, four aggregate endpoints, CSV and exclusion checks.

Chromium visited all 12 routes at 1440px desktop and 390px mobile widths: 24 page visits, no JavaScript console/page errors, no document-level horizontal overflow. Tables and long navigation deliberately scroll within their own containers. Screenshots of all routes were inspected in desktop/mobile contact sheets; explorer mobile and what-if desktop were also inspected individually. The charts are actual database/model outputs.

Browser interactions passed: live custom-state inference, save to notebook, reopen notebook and delete, player name search, replay next delivery, play/pause and reduced-motion. Reduced motion produced zero running animations. Source metadata, model curve, scorecards and metrics were checked through real backend requests. A real 25fps browser recording was captured showing replay, what-if calculation, player search and iris navigation to evaluation.

Limitations: no internet deployment, concurrency load test, account authentication, production penetration test, cross-browser Safari/iOS test or real-time provider integration was performed. This is a local research application with deployment instructions. No claim of production-grade win-probability calibration is made. Anonymous notebooks rely on the signed session and persistent disk.
