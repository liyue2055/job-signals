CREATE TABLE IF NOT EXISTS postings(
  id INTEGER PRIMARY KEY,
  source TEXT NOT NULL,
  source_id TEXT NOT NULL,
  company TEXT,
  title TEXT NOT NULL,
  location TEXT,
  category TEXT,
  description TEXT,
  skills TEXT,
  url TEXT,
  posted_at TEXT,
  collected_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(source, source_id)
);
CREATE TABLE IF NOT EXISTS runs(
  id INTEGER PRIMARY KEY,
  run_at TEXT NOT NULL DEFAULT (datetime('now')),
  source TEXT,
  fetched INTEGER,
  inserted INTEGER,
  note TEXT
);
CREATE INDEX IF NOT EXISTS idx_postings_category ON postings(category);
CREATE INDEX IF NOT EXISTS idx_postings_collected ON postings(collected_at);
