from wikiwall.history import History


def test_history_keeps_last_n_without_duplicates(tmp_path):
    history = History(tmp_path / "history.json", limit=3)
    for title in ["A", "B", "C", "A", "D"]:
        history.add(title)
    assert history.recent() == ["C", "A", "D"]


def test_history_limit(tmp_path):
    history = History(tmp_path / "history.json", limit=2)
    for title in ["A", "B", "C"]:
        history.add(title)
    assert history.recent() == ["B", "C"]


def test_history_clear(tmp_path):
    history = History(tmp_path / "history.json", limit=3)
    history.add("A")
    history.clear()
    assert history.recent() == []
