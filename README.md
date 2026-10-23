# Museum of Museums

An artwork exploring what counts as a museum, made for Extreme Presence.

Live site: https://museumofmuseums.org

A project by [Analogue Group](https://analoguegroup.org/) in collaboration with [Extreme Presence](https://www.hartwigartfoundation.nl/en/programmes/extreme-presence/), [Hartwig Proxy](https://www.hartwigproxy.nl/) / [Hartwig Art Foundation](https://www.hartwigartfoundation.nl/).

## Start editing

This is plain HTML, CSS and JavaScript. There is no build step or Node dependency.

From this folder, run:

```sh
python3 -m http.server 8000 --directory dist
```

Open http://localhost:8000. Serve over HTTP; opening index.html directly will prevent data fetching in some browsers.

## File guide

- `dist/index.html`: page structure, editorial text, footer and social metadata.
- `dist/style.css`: typography, colour, columns, responsive layout.
- `dist/app.js`: navigation, filters, cards, dialogs and atlas search.
- `dist/illustrations.js`: original SVG illustrations.
- `dist/data/curated.json`: 19 curated entries, including explicitly hypothetical cases.
- `dist/data/atlas.json` and `atlas.csv`: imported museum directory.
- `dist/data/sources.json`: source manifest and retrieval information.
- `dist/assets/`: gallery artwork, attribution and social share image.
- `scripts/scrape_museums.py`: rebuilds the directory from Wikipedia lists.

## Design brief for Karol

Explore what actually counts as a museum. The current visual reference is Hartwig's Extreme Presence programme: strong typography, editorial white space and turquoise accents. Retain the full Museum of Museums name; avoid MoM branding because the Seattle institution uses it. The five parallel columns are Cultivation, Devotion, Memory, Being and Interrelation. Memory and the column layout are deliberate choices.

Keep the exact linked credit sentence above, including its final period. The social share image is `dist/assets/share-museum-v1.jpg`; changing its filename also requires updating the absolute Open Graph and Twitter URLs in index.html.

## Review before publishing

Check desktop and mobile layouts, horizontal column scrolling, atlas search and pagination, country/type filters, card dialogs and Escape dismissal, definition switches, contrast toggle and footer links. The visitor's book is stored only in the visitor's browser localStorage; it is not a shared submission system.

Use a design branch and pull request so changes can be reviewed. This repository does not automatically deploy to museumofmuseums.org. Publishing currently happens separately through the existing Sites project. Coordinate publication with Aishwarya; uploading or merging code here alone does not update the live site.

## Data and attribution

The atlas contains 35,478 imported candidates from English Wikipedia country and regional museum lists. 388 lists were attempted and 376 contributed records. Source coverage is uneven, and these records are not independently verified as operating museums. Preserve per-record source links and the source manifest when editing or redistributing the data.

Wikipedia-derived material is attributed to its contributors under CC BY-SA 4.0: https://creativecommons.org/licenses/by-sa/4.0/. See `dist/data/sources.json` and each record's `sources` links for provenance.

The gallery painting is by David Teniers the Younger and is public domain; full credit and source URL are in `dist/assets/gallery-credit.txt`. The social share card is AI-generated fictional gallery imagery. No general open-source licence has been selected for the original code, editorial content or illustrations; public repository visibility does not itself grant a reuse licence.

## Optional data rebuild

The committed data is ready to use. Rebuilding is unnecessary for design work.

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install lxml
python scripts/scrape_museums.py
```

This accesses Wikipedia and replaces the atlas exports and source manifest. Cache files default to `/tmp/museum-scrape`; set `MUSEUM_CACHE` to use another location. Review changes and provenance before committing a rebuilt dataset.
