# Search Index Design

## Recipes table audit

The scraper populates a MySQL `recipes` table with the following columns:

- `id` (`BIGINT UNSIGNED`) – primary key and document identifier.
- `source_name` (`VARCHAR(255)`) – human readable source label.
- `source_url` (`VARCHAR(2048)`) – canonical URL (unique, indexed for de-duplication).
- `title` (`TEXT`) – headline of the recipe.
- `description` (`TEXT`) – summary or teaser text.
- `ingredients` (`LONGTEXT`) – JSON payload holding ingredient entries.
- `instructions` (`LONGTEXT`) – JSON array of instruction strings.
- `prep_time`, `cook_time`, `total_time`, `servings` (`VARCHAR(255)`) – formatted duration/yield strings.
- `image` (`VARCHAR(1024)`) – URL to the hero image.
- `author` (`VARCHAR(255)`) – attributed author information.
- `categories`, `tags` (`LONGTEXT`) – JSON arrays describing taxonomy metadata.
- `raw` (`LONGTEXT`) – original parser payload that also carries nutrition data.
- `created_at`, `updated_at` (`TIMESTAMP`) – lifecycle timestamps managed by MySQL.

Understanding these columns ensures the Elasticsearch mapping faithfully represents the relational source and
highlights which fields should be indexed for full-text search versus keyword filtering.

## Mapping highlights

The recipe index mapping (`config/elasticsearch/recipe_index.json`) encodes several key design decisions:

- **Custom analyzers** – three analyzers power the text fields:
  - `recipe_text` tokenizes with the standard tokenizer and applies lowercase, ASCII folding, English stop word
    removal, and stemming to give broad, typo-tolerant matching.
  - `recipe_shingle` builds on the same pipeline and appends a shingle filter to supply bi/tri-grams for phrase
    relevance and "sounds like" matching across titles, descriptions, and instructions.
  - `recipe_autocomplete` feeds text through lowercase + ASCII folding and an edge n-gram filter to provide fast
    prefix suggestions for names, titles, and ingredients without impacting the primary analyzer.
- **Keyword normalisation** – Many metadata fields (`source_name`, `author`, `categories`, `tags`, ingredient units)
  expose both exact-match keyword sub-fields (normalized by `lowercase_keyword`) and analyzed text sub-fields.
  This allows case-insensitive filtering while still enabling the analyzed `recipe_text` view for scoring.
- **Nested ingredients** – Ingredients remain a `nested` array with structured fields (`name`, `quantity`, `unit`,
  `raw`). Autocomplete-friendly sub-fields on `name` make it possible to drive ingredient pickers while keyword
  sub-fields enable deterministic filtering and aggregations.
- **Structured nutrients** – The `nutrients` object uses the `flattened` data type so arbitrary nutrition keys
  (calories, fat, fibre, etc.) can be indexed without declaring them upfront, while still allowing term queries or
  aggregations on any key/value pair.
- **Safeguards** – The verbose `raw` payload is disabled (`enabled: false`) to prevent Elasticsearch from indexing
  unbounded scraper data while still keeping it retrievable for diagnostics. Asset URLs (`image`) skip indexing
  entirely.
- **Autocomplete support** – Title and ingredient fields expose `autocomplete` sub-fields that rely on the edge
  n-gram analyzer, and a `suggest` completion field is available for search-as-you-type UI components.
- **Operational flexibility** – A write alias (`recipes-search`) is created alongside the concrete index so future
  zero-downtime re-indexing can simply repoint the alias.

## Initialisation workflow

Run `webapp/scripts/setup_elasticsearch.py` to bootstrap the index:

```bash
python -m webapp.scripts.setup_elasticsearch
```

Key behaviour:

1. Loads application configuration (`AppConfig`) to resolve Elasticsearch connection settings and the default index
   name. When only a password is supplied the script automatically authenticates as the built-in `elastic` user,
   matching the Docker Compose defaults.
2. Reads the mapping JSON (override with `--mapping` if needed) and creates an Elasticsearch client with optional
   basic authentication.
3. Checks whether the target index exists. Pass `--force` to drop and recreate it safely; otherwise the script exits
   without modifying the cluster.
4. Creates the index with the configured settings, mappings, and aliases (including `recipes-search`). Use `--index`
   to override the target index name for experimental environments.

This script should be executed after provisioning the Elasticsearch cluster or whenever the mapping evolves.
