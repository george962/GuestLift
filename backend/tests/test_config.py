from app import config


def test_defaults_match_local_preview(monkeypatch):
    monkeypatch.delenv('GUESTLIFT_ALLOWED_ORIGINS', raising=False)
    monkeypatch.delenv('GUESTLIFT_APP_URL', raising=False)
    assert config.allowed_origins() == ['http://localhost:3000', 'http://127.0.0.1:3000']
    assert config.app_url() == 'http://localhost:3000'


def test_origins_and_app_url_come_from_environment(monkeypatch):
    monkeypatch.setenv('GUESTLIFT_ALLOWED_ORIGINS', ' https://app.example.com/ ,https://www.example.com ,')
    monkeypatch.setenv('GUESTLIFT_APP_URL', 'https://app.example.com/')
    assert config.allowed_origins() == ['https://app.example.com', 'https://www.example.com']
    assert config.app_url() == 'https://app.example.com'


def test_blank_origins_fall_back_to_defaults(monkeypatch):
    monkeypatch.setenv('GUESTLIFT_ALLOWED_ORIGINS', ' , ')
    assert config.allowed_origins() == ['http://localhost:3000', 'http://127.0.0.1:3000']
