from pathlib import Path

from database.store import Store
from database.thumbs import (
    is_generic_visual,
    is_pil_content_card,
    is_real_photo_file,
    parse_preview_image_urls,
    render_content_card,
    source_display_name,
    youtube_thumb_url,
    ensure_article_thumb,
    list_real_photo_samples,
    resolve_real_sample,
)


def test_youtube_hqdefault():
    assert youtube_thumb_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == (
        "https://img.youtube.com/vi/dQw4w9WgXcQ/hqdefault.jpg"
    )
    assert youtube_thumb_url("https://youtu.be/abcdefghijk") == (
        "https://img.youtube.com/vi/abcdefghijk/hqdefault.jpg"
    )


def test_parse_og_and_skip_tiny_icons():
    html = """
    <html><head>
      <meta property="og:image" content="https://cdn.example.org/story.jpg">
      <meta name="twitter:image" content="https://cdn.example.org/tw.jpg">
    </head><body>
      <img src="/logo.png" width="16" height="16">
      <img src="https://cdn.example.org/photo.jpg" width="640" height="360">
    </body></html>
    """
    urls = parse_preview_image_urls(html, "https://cdn.example.org/a")
    assert urls[0] == "https://cdn.example.org/story.jpg"
    assert "https://cdn.example.org/tw.jpg" in urls
    assert "https://cdn.example.org/photo.jpg" in urls
    assert not any(u.endswith("logo.png") for u in urls)


def test_skip_generic_placeholders():
    assert is_generic_visual("storage/images/ph_CNT-abc.svg", "image/svg+xml")
    assert is_generic_visual("models/cnn/dataset/train/fb_001.png")
    assert is_generic_visual("storage/images/demo_seed_01.png")
    assert is_generic_visual("C:/tmp/fb_face.png")
    assert not is_generic_visual("storage/images/thumbs/CNT-abc.jpg", "image/jpeg")


def test_content_card_is_jpeg_with_title(tmp_path):
    dest = tmp_path / "card.jpg"
    render_content_card(
        dest,
        title="Brotes de influenza aviar en granjas",
        source="PubMed",
        snippet="Estudio sobre H5N1 en aves de corral y medidas de bioseguridad en 2024.",
        page_url="",
    )
    data = dest.read_bytes()
    assert data[:3] == b"\xff\xd8\xff"
    assert dest.stat().st_size > 1000


def test_ensure_thumb_for_blocked_social(tmp_path, monkeypatch):
    monkeypatch.setattr("database.thumbs.THUMBS_DIR", tmp_path / "thumbs")
    monkeypatch.setenv("TNB_FAST", "1")
    db = tmp_path / "tnb.db"
    monkeypatch.setattr("database.store.DB_PATH", db)
    store = Store(db)
    store.insert_article(
        {
            "content_id": "CNT-thumbtest01",
            "source_id": "SRC-LI",
            "url": "https://www.linkedin.com/posts/woah-avian",
            "url_sha256": "thumbtest01",
            "title": "WOAH alerta sobre influenza aviar en la región",
            "text": "Publicación de LinkedIn resumiendo el aviso oficial de WOAH sobre H5N1 en aves.",
            "source_type": "LinkedIn",
            "raw_format": "social",
        }
    )
    row = store.get_article("CNT-thumbtest01")
    path = ensure_article_thumb(store, row, fetch_html=False)
    assert path is not None and path.is_file()
    assert path.suffix.lower() == ".jpg"
    assert path.read_bytes()[:3] == b"\xff\xd8\xff"
    fresh = store.get_article("CNT-thumbtest01")
    assert str(fresh.get("thumb_path") or "").endswith(".jpg")
    assert source_display_name(row, store) == "LinkedIn"
    store.close()


def test_content_card_is_not_real_photo(tmp_path):
    dest = tmp_path / "card.jpg"
    render_content_card(
        dest,
        title="Brotes de influenza aviar en granjas",
        source="PubMed",
        snippet="Estudio sobre H5N1 en aves de corral.",
        page_url="",
    )
    assert is_pil_content_card(dest)
    assert not is_real_photo_file(dest)


def test_list_real_samples_skips_cnn_drawings_and_cards(tmp_path, monkeypatch):
    monkeypatch.setattr("database.thumbs.THUMBS_DIR", tmp_path / "thumbs")
    monkeypatch.setenv("TNB_FAST", "1")
    db = tmp_path / "tnb.db"
    monkeypatch.setattr("database.store.DB_PATH", db)
    store = Store(db)
    store.insert_article(
        {
            "content_id": "CNT-cardonly01",
            "source_id": "SRC-LI",
            "url": "https://www.linkedin.com/posts/woah-avian",
            "url_sha256": "cardonly01",
            "title": "WOAH alerta sobre influenza aviar en la región",
            "text": "Aviso oficial de WOAH sobre H5N1 en aves.",
            "source_type": "LinkedIn",
            "raw_format": "social",
        }
    )
    row = store.get_article("CNT-cardonly01")
    path = ensure_article_thumb(store, row, fetch_html=False)
    assert path is not None
    samples = list_real_photo_samples(store, limit=12)
    assert samples == []
    resolved, _url, _art = resolve_real_sample(store, "meme_unseen_0.png")
    assert resolved is None
    store.close()
