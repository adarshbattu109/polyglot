"""The app's routes: the UI is served and the MCP mount survived."""


def test_index_serves_the_ui(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<title>Polyglot" in response.text


def test_ui_has_no_external_dependencies(client):
    """Offline-first: a CDN reference would break the app on an air-gapped machine.

    Only fetching attributes are checked. The favicon is an inline SVG data URI, and SVG
    requires an xmlns of `http://www.w3.org/2000/svg` — a namespace identifier the browser
    never resolves, so it is not a dependency.
    """
    page = client.get("/").text

    for attribute in ("src=", "href=", "url("):
        for quote in ('"', "'", ""):
            assert f"{attribute}{quote}http" not in page

    # and no webfont either: the type stacks have to resolve locally
    assert "@import" not in page
    assert "@font-face" not in page


def test_mcp_is_still_mounted(app_routes):
    assert "/mcp" in app_routes
