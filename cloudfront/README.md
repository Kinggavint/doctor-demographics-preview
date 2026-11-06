# CloudFront redirect function (doctordemographics.com)

Source for the viewer-request function `apex-site-doctor-demographics-redirects` on distribution `EYM38RXLJ0S2M`.
Until now it lived only on the ops box (generated from REDIRECTS.csv by `gen_fn.py`); it is checked in here so the
redirect map is reviewable.

| File | What |
|---|---|
| `old-wp-404-redirects.csv` | 423 old WordPress URLs that 404 today (broken-link audit, Nov 4 2026) mapped to a live page. `type`: `exact` (same page/product, or a newer edition of the same article), `closest-article` (1, same as PR #3), `section-fallback` (closest section). |
| `gen_fn.py` | Builds the function from `REDIRECTS.csv` + `old-wp-404-redirects.csv` + the 16 GHL order paths. |
| `apex-site-doctor-demographics-redirects.js` | Generated function (must stay under 10 KB). |
| `redirect-map.json` | Generated full map, old path -> target, for review. |
| `test_fn.js` | Local test: every old URL, every target, every live page, GHL paths, regression against the old function. |

```
python3 cloudfront/gen_fn.py
DD_PROD=1 python3 build/gen.py
node cloudfront/test_fn.js [path/to/currently-live-function.js]
```

Rules: one hop only (every target is a live page that the function serves without another redirect), exact rows win
over prefix rules, and no prefix rule may cover a path that has live pages (that is why old `/blog/b/` posts are listed
one by one). Unknown URLs still get the normal 404. order.doctordemographics.com (GHL) is a different host and is not
affected.

Deploy (only after Gavin says yes): update the function with the generated .js, test it in the CloudFront console
(`aws cloudfront test-function`), publish, then curl a sample of old URLs.
