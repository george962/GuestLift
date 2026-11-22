from app import database


def test_auto_create_can_be_disabled(monkeypatch):
    called = []
    monkeypatch.setenv('GUESTLIFT_AUTO_CREATE_SCHEMA', '0')
    monkeypatch.setattr(database.Base.metadata, 'create_all', lambda *a, **k: called.append(1))
    database.init_db()
    assert called == []
