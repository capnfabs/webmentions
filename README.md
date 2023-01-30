# webmentions

Ensure [poetry is installed](https://python-poetry.org/docs/#installation)

```
poetry install --with dev
```

Dev scripts are under `/tasks`, the main entry-point right now is `tasks/cli`.


Some basic testing:
```sh
rm local.db
tasks/cli --register https://grand-phoenix-d50fd5.netlify.app/
tasks/cli  # should find two articles
tasks/cli  # should find zero new articles
```
