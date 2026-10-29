# doctordemographics.com preview

Static preview of the Doctor Demographics site, built from the live copy for review.
Preview: https://kinggavint.github.io/doctor-demographics-preview/

- Branch `preview` only. Not for go live.
- Every page has noindex, nofollow, and robots.txt blocks crawling. Canonicals point to doctordemographics.com.
- Forms and calendars embed the live GoHighLevel widgets by ID. Order and training buttons link to the live GHL pages.
  ORDER_BASE in build/gen.py switches to https://order.doctordemographics.com at cutover.
- Build: `python3 build/gen.py` then `build/verify.sh docs`
- Published folder: `docs/` (Pages source: branch `preview`, path `/docs`). build/, TODO.md, CHANGES.md, REDIRECTS.csv and this README are not published.
- Open items: TODO.md. Copy changes: CHANGES.md. Redirect plan: REDIRECTS.csv.
- Pages: 75 generated. Podcast episodes listed: 62.
