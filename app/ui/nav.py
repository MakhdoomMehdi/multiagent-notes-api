"""One sidebar for every notes page."""


def sidebar() -> str:
    return """<nav id="app-nav" aria-label="Application">
  <a href="/pages">Index</a>
  <a href="/pages/new">Create</a>
  <a href="/pages/find">Find</a>
  <a href="/pages/help">Help</a>
  <a href="/board">Board</a>
  <a href="/docs">API docs</a>
</nav>
<style>
  body { display: flex; align-items: flex-start; }
  #app-nav {
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
    min-width: 9rem;
    padding: 1.25rem 1rem;
    background: #1c1915;
    color: #f6f4ef;
  }
  #app-nav a { color: #f6f4ef; }
  main { padding: 1.5rem; }
</style>
"""


def with_sidebar(page: str) -> str:
    return page.replace("<body>", "<body>\n" + sidebar(), 1)
