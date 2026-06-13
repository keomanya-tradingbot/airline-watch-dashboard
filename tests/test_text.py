from airline_watch.text import canonical_url, visible_text


def test_canonical_url_removes_tracking_and_fragment():
    assert canonical_url(
        "HTTPS://Example.COM/news/?utm_source=x&id=2#section"
    ) == "https://example.com/news?id=2"


def test_visible_text_ignores_scripts():
    assert visible_text("<h1>Fleet update</h1><script>ignore()</script>") == (
        "Fleet update"
    )

