import json
import urllib.request


def test_voice_can_be_started_again_after_an_error(monkeypatch):
    from factopia_voice import server
    started = []
    monkeypatch.setattr(server, "begin", lambda: started.append(True))
    monkeypatch.setattr(server.studio, "status", {"phase": "error", "percent": 0, "detail": "download stopped"})
    httpd = server.make_server(0)
    import threading
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        port = httpd.server_address[1]
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/voice/retry", data=b"{}",
                                     headers={"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{port}"})
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=10) as r:
            assert json.loads(r.read()) == {"ok": True}
        assert started == [True] and server.studio.status["phase"] == "starting"
    finally:
        httpd.shutdown()
