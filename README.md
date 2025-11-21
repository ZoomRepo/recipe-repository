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

### Provisioning Elasticsearch

The scraper and Flask app can push documents to Elasticsearch for downstream
search, analytics, or monitoring. A single-node cluster is defined in
`docker-compose.elasticsearch.yml` and can be launched locally with Docker:

```bash
docker compose -f docker-compose.elasticsearch.yml up -d
```

The compose file provisions a secured node that listens on port `9200` and
generates the `elastic` superuser. Provide a strong password via the
`ELASTICSEARCH_PASSWORD` environment variable before starting the container so
the secret is never written to disk in plain text.

If you set only the password, the application defaults to the `elastic`
superuser for you. Override `ELASTICSEARCH_USERNAME` if you prefer a different
role with scoped privileges.

Configure both the scraper and web application with matching credentials.
Environment variables are the preferred mechanism so secrets remain outside of
version control. The repository includes a `.env.example` template covering the
required values:

```bash
cp .env.example .env
# edit .env to suit your environment
```

At minimum you should define the cluster URL and the indices used to store
recipes and scraper metadata:

```bash
export ELASTICSEARCH_URL=http://localhost:9200
export ELASTICSEARCH_USERNAME=elastic
export ELASTICSEARCH_PASSWORD=super-secret
export ELASTICSEARCH_RECIPE_INDEX=recipes
export ELASTICSEARCH_SCRAPER_INDEX=scraper-events
```

Verify connectivity from the application container or your workstation using the
health check script:

```bash
python -m webapp.scripts.es_healthcheck --check-indices
```

The command pings the cluster, waits for at least the `yellow` health status,
and optionally ensures the configured indices exist.

### Temporary email login gate (Next.js app)

The modern `findmyrecipe-web-app` front-end can require visitors to request a
six-digit code before browsing any protected route. The feature is fully
optional and guarded by environment variables so you can toggle it for staging
or promotion.

Enable the gate by setting the following variables for the Next.js app:

| Variable | Purpose |
| --- | --- |
| `TEMP_LOGIN_ENABLED` | Enables the temporary login flow on the server. |
| `NEXT_PUBLIC_TEMP_LOGIN_ENABLED` | Mirrors the flag for client bundles so the UI can react accordingly. |
| `LOGIN_SESSION_SECRET` (or `AUTH_SECRET`) | Secret used to sign the session cookie issued after a successful code verification. |

You can fine tune the timings and email content with these optional variables:

| Variable | Purpose | Default |
| --- | --- | --- |
| `LOGIN_CODE_EXPIRY_MINUTES` | Minutes before a one-time code expires. | `15` |
| `LOGIN_SESSION_DURATION_DAYS` | Days before the signed cookie expires. | `30` |
| `LOGIN_EMAIL_SUBJECT` | Subject line for the message sent to recipients. | `Your findmyflavour login code` |
| `LOGIN_EMAIL_SENDER` | From address used for the email. | _required_ |

The app delivers codes via SMTP. Provide credentials for a mail relay that can
send the messages:

| Variable | Purpose |
| --- | --- |
| `SMTP_HOST` | Host name of your SMTP server. |
| `SMTP_PORT` | Port exposed by the server. |
| `SMTP_USERNAME` | Username used to authenticate. |
| `SMTP_PASSWORD` | Password or app token. |
| `SMTP_SECURE` | Set to `false` for STARTTLS on port 587, keep `true` for implicit TLS. |

#### Managing the access whitelist

Codes are only sent to addresses stored in the `login_whitelist` table. The
Next.js UI exposes a **Whitelist** page (linked from the homepage header and the
login screen) where you can review, add, and remove entries when you are signed
in. Seed at least one administrator email before enabling the feature so someone
can request the initial code.

The temporary login flow also persists pending codes in the `login_codes` table
so each request can be validated once. Successful verifications mint a
longer-lived session code that is stored in the browser's `localStorage` and in
the `login_sessions` table. When the same device revisits the site the login
page exchanges that stored session code for a fresh signed cookie without
sending another email. Create the supporting schema if it does not exist:

```sql
CREATE TABLE login_whitelist (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(320) NOT NULL UNIQUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE login_codes (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(320) NOT NULL UNIQUE,
  code_hash CHAR(64) NOT NULL,
  expires_at DATETIME NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_login_codes_expires_at (expires_at)
);

CREATE TABLE login_sessions (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(320) NOT NULL UNIQUE,
  session_code_hash CHAR(64) NOT NULL UNIQUE,
  expires_at DATETIME NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_login_sessions_expires_at (expires_at)
);
```

All tables normalise emails to lowercase before storage, ensuring consistent
comparisons for future requests.

For a production-style deployment, use the `run_app_production` make target
which launches the app with the Waitress WSGI server:

```bash
make run_app_production
```

Waitress will honour the `PORT` environment variable (defaulting to `8000`)
while loading the configuration from the same environment variables listed
above. This avoids Flask's development server warning and provides a WSGI
server suitable for running behind a reverse proxy.
