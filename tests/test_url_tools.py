from app.core.url_tools import is_youtube_url, clean_url


def test_watch_url_with_parameters():
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=XYZ&t=30s&index=2"
    assert is_youtube_url(url) is True
    assert clean_url(url) == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_short_youtu_be_url():
    url = "https://youtu.be/dQw4w9WgXcQ?si=abc_123"
    assert is_youtube_url(url) is True
    assert clean_url(url) == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_shorts_url():
    url = "https://www.youtube.com/shorts/dQw4w9WgXcQ"
    assert is_youtube_url(url) is True
    assert clean_url(url) == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_mobile_and_schemeless():
    url = "m.youtube.com/watch?v=dQw4w9WgXcQ"
    assert is_youtube_url(url) is True
    assert clean_url(url) == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_invalid_urls():
    for invalid in ["hello", "", "   ", "https://vimeo.com/123456", "https://google.com"]:
        assert is_youtube_url(invalid) is False
        assert clean_url(invalid) is None
