"""ADR reader: list, filter, and rendered decision pages."""

import pytest

SAMPLE = """# ADR-0007: Sample decision

- Status: Accepted
- Date: 2026-11-23

## Decision
See ADR-0004 and ADR-0010 before editing.

- Keep the integer converter
- Escape markup first

```python
print("ADR-0004")
```

<script>alert(1)</script>
"""

ACCEPTED = """# ADR-0003: Folders

- Status: Accepted
- Date: 2026-11-20

## Decision
unique-needle lives here.
"""

SUPERSEDED = """# ADR-0008: Old chrome

- Status: Superseded by ADR-0009
- Date: 2026-11-21

## Decision
unique-needle used to live here.
"""

OTHER = """# ADR-0006: Unrelated

- Status: Accepted
- Date: 2026-11-22

## Decision
Nothing to find in this body.
"""


@pytest.fixture(autouse=True)
def seed_console(monkeypatch):
    monkeypatch.setenv("CONSOLE_SOURCE", "seed")


def _write(directory, name, text):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(text, encoding="utf-8")


def _row(html: str, number: int) -> str:
    href = f'href="/console/adrs/{number}"'
    start = html.index(href)
    open_li = html.rindex("<li", 0, start)
    close_li = html.index("</li>", start)
    return html[open_li:close_li]


def _reader(html: str) -> str:
    start = html.index('id="adr-reader"')
    return html[start:]


def test_list_highlights_key_adrs_and_skips_the_template(client, monkeypatch):
    monkeypatch.delenv("CONSOLE_ADR_DIR", raising=False)
    response = client.get("/console/adrs")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    html = response.text
    assert "<title>ADRs · Harness Console</title>" in html
    assert 'href="/console/adrs" aria-current="page"' in html
    assert 'id="source-badge" data-mode="seed" href="/console/adrs"' in html
    assert 'method="get"' in html
    assert 'name="q"' in html
    assert 'name="status"' in html
    assert 'id="adr-list"' in html
    for number in (3, 4, 9):
        row = _row(html, number)
        assert 'class="adr-key"' in row
        assert f">ADR-{number:04d}<" in row
        assert "Accepted" in row
        assert "2026-11-" in row
    assert "One folder per feature" in _row(html, 3)
    for number in (1, 2, 8, 10):
        assert 'class="adr-key"' not in _row(html, number)
    assert 'href="/console/adrs/0"' not in html
    assert 'href="/console/adrs/5"' not in html
    assert "Traceback" not in html


def test_status_filter_keeps_accepted(client, monkeypatch):
    monkeypatch.delenv("CONSOLE_ADR_DIR", raising=False)
    accepted = client.get("/console/adrs", params={"status": "Accepted"})
    assert accepted.status_code == 200
    assert 'href="/console/adrs/3"' in accepted.text
    assert 'href="/console/adrs/9"' in accepted.text
    assert 'value="Accepted"' in accepted.text

    rejected = client.get("/console/adrs", params={"status": "Rejected"})
    assert rejected.status_code == 200
    assert 'id="empty-state"' in rejected.text
    assert 'id="adr-list"' not in rejected.text


def test_superseded_prefix_and_combined_filters(tmp_path, monkeypatch, client):
    monkeypatch.setenv("CONSOLE_ADR_DIR", str(tmp_path))
    _write(tmp_path, "0003-folders.md", ACCEPTED)
    _write(tmp_path, "0006-other.md", OTHER)
    _write(tmp_path, "0008-old-chrome.md", SUPERSEDED)

    superseded = client.get("/console/adrs", params={"status": "Superseded"})
    assert superseded.status_code == 200
    assert 'href="/console/adrs/8"' in superseded.text
    assert 'href="/console/adrs/3"' not in superseded.text

    both = client.get("/console/adrs", params={"q": "UNIQUE-NEEDLE", "status": "Accepted"})
    assert both.status_code == 200
    assert 'href="/console/adrs/3"' in both.text
    assert 'href="/console/adrs/8"' not in both.text
    assert 'href="/console/adrs/6"' not in both.text


def test_query_matches_body_and_empty_query_shows_empty_state(client, monkeypatch):
    monkeypatch.delenv("CONSOLE_ADR_DIR", raising=False)
    matched = client.get("/console/adrs", params={"q": "AlPhAbEtIcAl"})
    assert matched.status_code == 200
    assert 'href="/console/adrs/3"' in matched.text
    assert 'href="/console/adrs/9"' not in matched.text

    nothing = client.get("/console/adrs", params={"q": "zzzz-no-adr-match"})
    assert nothing.status_code == 200
    assert 'id="empty-state"' in nothing.text
    assert 'id="adr-list"' not in nothing.text


def test_adr_0005_is_key_only_for_its_named_file(tmp_path, monkeypatch, client):
    monkeypatch.setenv("CONSOLE_ADR_DIR", str(tmp_path))
    _write(
        tmp_path,
        "0005-specialized-builder-roles.md",
        "# ADR-0005: Roles\n\n- Status: Accepted\n- Date: 2026-11-23\n",
    )
    _write(
        tmp_path,
        "0006-other.md",
        "# ADR-0006: Other\n\n- Status: Accepted\n- Date: 2026-11-23\n",
    )
    html = client.get("/console/adrs").text
    assert 'class="adr-key"' in _row(html, 5)
    assert 'class="adr-key"' not in _row(html, 6)

    other = tmp_path / "0005-other-name.md"
    other.write_text(
        "# ADR-0005: Other name\n\n- Status: Accepted\n- Date: 2026-11-23\n",
        encoding="utf-8",
    )
    (tmp_path / "0005-specialized-builder-roles.md").unlink()
    renamed = client.get("/console/adrs").text
    assert 'class="adr-key"' not in _row(renamed, 5)


def test_adr_three_renders_sections_as_html(client, monkeypatch):
    monkeypatch.delenv("CONSOLE_ADR_DIR", raising=False)
    response = client.get("/console/adrs/3")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    reader = _reader(response.text)
    assert "<h2>Decision</h2>" in reader
    assert "## Decision" not in reader
    assert "<li>" in reader
    assert 'href="/console/adrs/3"' in reader
    assert 'href="/console/adrs/0003"' not in response.text


def test_reader_links_fenced_code_and_escapes_markup(tmp_path, monkeypatch, client):
    monkeypatch.setenv("CONSOLE_ADR_DIR", str(tmp_path))
    _write(tmp_path, "0007-sample.md", SAMPLE)
    response = client.get("/console/adrs/7")
    assert response.status_code == 200
    reader = _reader(response.text)
    assert 'href="/console/adrs/4"' in reader
    assert ">ADR-0004</a>" in reader
    assert 'href="/console/adrs/10"' in reader
    assert ">ADR-0010</a>" in reader
    assert 'href="/console/adrs/0004"' not in response.text
    assert 'href="/console/adrs/0010"' not in response.text
    assert "<pre><code>" in reader
    code = reader[reader.index("<pre><code>") : reader.index("</code></pre>")]
    assert 'print("ADR-0004")' in code
    assert "<a " not in code
    assert "&lt;script&gt;" in reader
    assert "<script>" not in response.text


def test_unknown_adr_returns_404_html(client, monkeypatch):
    monkeypatch.delenv("CONSOLE_ADR_DIR", raising=False)
    response = client.get("/console/adrs/9999")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/html")
    assert 'id="error-state"' in response.text
    assert 'id="adr-reader"' not in response.text
    assert 'id="adr-list"' not in response.text
    assert "Traceback" not in response.text


def test_loading_and_error_states_omit_the_list(client):
    loading = client.get("/console/adrs", params={"state": "loading"})
    assert loading.status_code == 200
    assert 'id="loading-state"' in loading.text
    assert 'id="adr-list"' not in loading.text
    assert 'id="error-state"' not in loading.text

    error = client.get("/console/adrs", params={"state": "error"})
    assert error.status_code == 200
    assert 'id="error-state"' in error.text
    assert 'id="adr-list"' not in error.text
    assert 'id="loading-state"' not in error.text


def test_missing_directory_is_error_state(tmp_path, monkeypatch, client):
    monkeypatch.setenv("CONSOLE_ADR_DIR", str(tmp_path / "missing"))
    response = client.get("/console/adrs")
    assert response.status_code == 200
    assert 'id="error-state"' in response.text
    assert 'id="adr-list"' not in response.text
    assert "Traceback" not in response.text


def test_source_seed_still_reads_adr_files(client, monkeypatch):
    monkeypatch.delenv("CONSOLE_SOURCE", raising=False)
    monkeypatch.delenv("CONSOLE_ADR_DIR", raising=False)
    response = client.get("/console/adrs", params={"source": "seed"})
    assert response.status_code == 200
    assert 'href="/console/adrs/3"' in response.text
    assert 'data-mode="seed"' in response.text


def test_non_integer_adr_path_is_not_the_reader(client):
    response = client.get("/console/adrs/nope")
    assert response.status_code == 404
    assert 'id="adr-reader"' not in response.text
