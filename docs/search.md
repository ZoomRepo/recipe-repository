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

Understanding these columns ensures the Elasticsearch mapping faithfully represents the relational source and highlights which fields should be indexed for full-text search versus keyword filtering.

## Mapping highlights

The recipe index mapping (`config/elasticsearch/recipe_index.json`) encodes several key design decisions:

- **Custom analyzers** – `recipe_text` combines the standard tokenizer with lowercase, stop-word removal, and stemming to support full-text queries across titles, descriptions, instructions, and ingredient text. A companion `recipe_shingle` analyzer produces bi/tri-grams for better phrase matching and autocomplete contexts.
- **Keyword normalisation** – Many metadata fields (`source_name`, `author`, `categories`, `tags`) are exposed both as exact-match keywords (normalised via the `lowercase_keyword` normalizer) and as analyzed text sub-fields. This enables case-insensitive filtering while retaining free-text relevance scoring when needed.
- **Nested ingredients** – Ingredients are modelled as a `nested` array with structured fields (`name`, `quantity`, `unit`, `raw`). This allows precise filtering (e.g. recipes containing “chopped basil”) and aggregation by ingredient tokens without flattening unrelated ingredient entries into the same document.
- **Structured nutrients** – The `nutrients` object remains dynamic to accommodate varying keys (calories, fat, etc.) extracted from upstream data while avoiding strict schema coupling.
- **Safeguards** – The `raw` payload is disabled (`enabled: false`) to prevent Elasticsearch from indexing the unbounded scraper payload while still allowing it to be stored for diagnostics. Asset URLs (`image`) skip indexing entirely.
- **Autocomplete support** – A `suggest` completion field enables future search-as-you-type experiences powered by the same analyzer configuration.

## Initialisation workflow

Run `webapp/scripts/setup_elasticsearch.py` to bootstrap the index:

```bash
python -m webapp.scripts.setup_elasticsearch
```

Key behaviour:

1. Loads application configuration (`AppConfig`) to resolve Elasticsearch connection settings and the default index name.
2. Reads the mapping JSON (override with `--mapping` if needed) and creates an Elasticsearch client with optional basic authentication.
3. Checks whether the target index exists. Pass `--force` to drop and recreate it safely; otherwise the script exits without modifying the cluster.
4. Creates the index with the configured settings, mappings, and aliases. Use `--index` to override the target index name for experimental environments.

This script should be executed after provisioning the Elasticsearch cluster or whenever the mapping evolves.
