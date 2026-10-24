import asyncio

from noc.collectors import tcp_http_collector
from noc.metrics_catalog import CATALOG


def test_http_body_match_is_reported_as_a_metric(monkeypatch):
    class Response:
        status_code = 200
        text = "service ready"

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url):
            return Response()

    monkeypatch.setattr(tcp_http_collector.httpx, "AsyncClient", lambda **kwargs: Client())

    async def run():
        result = await tcp_http_collector.collect_probes(
            "127.0.0.1",
            {"icmp": False, "http_urls": ["http://service.local"], "body_match": "healthy", "ssl_check": False},
            "ping_http",
        )
        http = result["details"]["http"][0]
        assert http["status_code"] == 200
        assert http["body_match"] is False
        assert http["ok"] is False
        check = next(metric for metric in result["metrics"] if metric["key"] == "http.check_ok")
        assert check["value"] == 0
        assert check["key"] in CATALOG

    asyncio.run(run())
