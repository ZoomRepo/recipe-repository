# Recipe Repository

This repository now includes two major components:

1. A configurable recipe scraper capable of harvesting recipes from the
   approved domains defined in `config/scraper_templates.json`. The scraper
   normalises the extracted data and persists it into the provided MySQL
   database.
2. A Flask web application that reads the persisted recipes, allows you to
   search across titles, descriptions, ingredients, and instructions, and view
   complete recipe pages.

## Prerequisites

Install the Python dependencies (re-run this whenever `requirements.txt`
changes to refresh the virtual environment):

```bash
make setup
```

## Flagging non-food recipe images

The repository bundles a command line helper that downloads each recipe's
primary photo and flags anything that does not appear to depict food. To use it:

1. Export the recipes you want to analyse as a JSON array of the normalised
   records produced by the scraper (each entry should include fields such as
   `title`, `source_url`, and `image_url`).
2. Install the Python dependencies listed in `requirements.txt` (for example via
   `make setup` as shown above).
3. Run the classifier from the repository root, pointing it at your recipes
   file. Optionally provide an output path to capture the flagged entries.

```bash
python -m scraper.scripts.find_non_food_images path/to/recipes.json \
    --output flagged_non_food.json
```

The script prints any recipes whose images are likely non-food, along with the
predicted ImageNet label and probability. Use `--limit` to process only the
first *n* recipes, `--food-threshold` to adjust the sensitivity, or `--log-level
DEBUG` for verbose tracing while troubleshooting.

## Running the scraper

The scraper exposes a command line interface:

```bash
python -m scraper.cli --config config/scraper_templates.json
```

To replay stored failures without launching a full scrape, add
`--rerun-failures`. You can optionally cap the number of retries using
`--max-failures`:

```bash
python -m scraper.cli --rerun-failures --max-failures 50
```

Run migrations (table creation or schema updates) at any time with
`--migrate-only`:

```bash
python -m scraper.cli --migrate-only
```

### Configuring scraper templates

Scraper behaviour is defined through the JSON templates stored in
`config/scraper_templates.json`. The file contains a list of template objects,
one per supported site. Each template controls how recipes are discovered and
extracted:

```json
[
  {
    "name": "Example Site",
    "url": "https://www.example.com",
    "type": "cooking",
    "recipes": {
      "listing": [
        {
          "url": "https://www.example.com/recipes",
          "link_selector": "article h2 a",
          "pagination_selector": ".pagination a.next"
        }
      ]
    },
    "article": {
      "title": ["h1.entry-title"],
      "description": [".recipe-summary"],
      "ingredients": [".ingredients li"],
      "instructions": [".instructions li"],
      "image": ["meta[property='og:image']::attr(content)"]
    },
    "structured_data": {
      "enabled": true,
      "json_ld_selector": "script[type='application/ld+json']",
      "json_ld_path": "@graph[?(@['@type']=='Recipe')]"
    }
  }
]
```

Key fields:

* `name` and `url` identify the source website. `type` is optional metadata.
* `recipes.listing` describes how to discover article URLs. Each entry supplies
  a `url` to crawl, a CSS `link_selector` for recipe links, and an optional
  `pagination_selector` used to follow next-page links.
* `article` maps recipe fields (title, ingredients, etc.) to CSS selectors that
  should be evaluated against the article HTML.
* `structured_data` enables JSON-LD extraction when available. Set `enabled` to
  `true` and provide the selector and JSON path used to locate the recipe node.

When a template completes a scrape run the CLI automatically annotates the
corresponding JSON object with `"scraper": true`. Future runs skip templates
marked this way, keeping the focus on outstanding sources. You can rerun a
completed site by specifying it explicitly via `--sites` or by clearing the flag
in the configuration file.

By default it will connect to the production database at `217.43.43.202`
using the credentials provided by the user. You can override the connection or
limit the run to specific sites:

```bash
python -m scraper.cli \
    --db-host 127.0.0.1 \
    --db-user [USER] \
    --db-password [PASS] \
    --db-name reciperepository \
    --sites "BBC Good Food" "simplyrecipes.com"
```

Use `--max-pages` to constrain how many listing pages are crawled per site.

Convenience make targets are provided:

```bash
make migrate          # ensure database tables exist
make run_scraper      # run the scraper normally
make rerun_failures   # retry only the stored failures
```

Logs are emitted to stdout and can be controlled with `--log-level` (e.g.
`--log-level DEBUG`).

If a site's configured listing pages fail or return no results the scraper now
falls back to crawling the domain's XML sitemaps (including WordPress specific
maps). This greatly improves coverage for JavaScript-driven or paginated
catalogues at the cost of additional HTTP requests. The fallback respects the
`--max-pages` option for HTML listings and caps sitemap discovery to protect the
target sites.

## Running the web application

The web application is backed by the same MySQL database. Environment
variables can be used to override the defaults shown below.

```bash
export DB_HOST=[EXTERNAL_IP]
export DB_USER=[USER]
export DB_PASSWORD=[PASS]
export DB_NAME=reciperepository

python -m webapp
```

The server listens on `http://127.0.0.1:8000/` by default. Adjust the `PORT`
environment variable if you need to use a different port.

For a production-style deployment, use the `run_app_production` make target
which launches the app with the Waitress WSGI server:

```bash
make run_app_production
```

Waitress will honour the `PORT` environment variable (defaulting to `8000`)
while loading the configuration from the same environment variables listed
above. This avoids Flask's development server warning and provides a WSGI
server suitable for running behind a reverse proxy.
