# my-scholastic-book-fair 📚

A small curated reading feed.

- `feeds.opml`: the source list. Add a source by adding one `<outline type="rss" ... xmlUrl="..."/>` line. Pushing a change re-runs the fetch.
- `.github/workflows/fetch-feeds.yml`: runs daily and pulls every feed.
- `items.json`: posts from the last 28 days (title, link, source, date, short summary).
- `feed_status.json`: which feeds worked on the last run.

Every Sunday a scheduled Claude task reads `items.json` and picks the 3–5 best posts. It sends them to Instapaper and emails a short digest. It uses the Gmail sent folder to track what it has already sent, so nothing is sent twice.
