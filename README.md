# Recipe Repository

This repository now includes a configurable recipe scraper capable of harvesting
recipes from the approved domains defined in
`config/scraper_templates.json`. The scraper normalises the extracted data and
persists it into the provided MySQL database.

## Prerequisites

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

## Running the scraper

The scraper exposes a command line interface:

```bash
python -m scraper.cli --config config/scraper_templates.json
```

By default it will connect to the production database at `217.43.43.202`
using the credentials provided by the user. You can override the connection or
limit the run to specific sites:

```bash
python -m scraper.cli \
    --db-host 127.0.0.1 \
    --db-user reciperepository \
    --db-password Xenomorph123 \
    --db-name reciperepository \
    --sites "BBC Good Food" "simplyrecipes.com"
```

Use `--max-pages` to constrain how many listing pages are crawled per site.

Logs are emitted to stdout and can be controlled with `--log-level` (e.g.
`--log-level DEBUG`).
