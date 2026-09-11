from backup_db import backup_sqlite, rotate_backups
from html_fetcher import extract_main_text
from pipeline.run import _want_demo_seed


def test_demo_seed_off_by_default(monkeypatch):
    monkeypatch.delenv("TNB_DEMO_SEED", raising=False)
    assert _want_demo_seed(False) is False
    monkeypatch.setenv("TNB_DEMO_SEED", "1")
    assert _want_demo_seed(False) is True
    monkeypatch.setenv("TNB_DEMO_SEED", "0")
    assert _want_demo_seed(True) is True


def test_backup_sqlite_keeps_last_seven(tmp_path):
    db = tmp_path / "tnb.db"
    import sqlite3

    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE t (x INTEGER)")
    conn.execute("INSERT INTO t VALUES (1)")
    conn.commit()
    conn.close()
    dest = tmp_path / "backups"
    first = backup_sqlite(db, dest_dir=dest, keep=7)
    assert first is not None and first.is_file()
    for i in range(8):
        backup_sqlite(db, dest_dir=dest, keep=7)
        # stamps are minute-resolution; force unique names
        stamped = dest / f"tnb-20260101-000{i}.db"
        stamped.write_bytes(first.read_bytes())
    rotate_backups(dest, keep=7)
    left = list(dest.glob("tnb-*.db"))
    assert len(left) <= 8


def test_extract_main_text_from_article_html():
    html = """
    <html><head><title>H5N1 update</title></head>
    <body>
      <nav>menu</nav>
      <article>
        <h1>Avian influenza</h1>
        <p>WOAH reports highly pathogenic avian influenza H5N1 in poultry farms with biosecurity measures.</p>
        <img src="https://www.woah.org/img/a.jpg" alt="poultry" />
      </article>
      <footer>cookies</footer>
    </body></html>
    """
    out = extract_main_text(html, base_url="https://www.woah.org/")
    assert "H5N1" in out["text"]
    assert "cookies" not in out["text"].lower() or "poultry" in out["text"].lower()
    assert any("woah.org/img" in u for u in out["images"])
