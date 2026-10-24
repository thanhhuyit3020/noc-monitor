import asyncio
import time

from noc.db import Database
from noc.engine.alert_engine import AlertEngine


class SocketStub:
    async def broadcast(self, event):
        pass


class NotifierStub:
    def __init__(self):
        self.websocket_manager = SocketStub()
        self.sent = []

    async def incident(self, event):
        self.sent.append(event)


def test_alert_engine_hysteresis_no_data_and_auto_resolve(tmp_path):
    async def run():
        db = Database(tmp_path / "noc.db")
        await db.open()
        host = (await db.query("SELECT * FROM hosts WHERE id='local'"))[0]
        notifier = NotifierStub()
        engine = AlertEngine(db, notifier)
        rule = (await db.query("SELECT * FROM alert_rules WHERE id='cpu-high'"))[0]
        sample = {"key": "cpu.total_pct", "value": 97, "unit": "%", "resource_key": ""}
        await engine.evaluate(host, {"metrics": [sample]})
        assert not await db.query("SELECT id FROM incidents WHERE rule_id=? AND state='OPEN'", (rule["id"],))
        await engine.evaluate(host, {"metrics": [{"key": "cpu.total_pct", "value": 40, "unit": "%", "resource_key": ""}]})
        await engine.evaluate(host, {"metrics": [sample]})
        assert not await db.query("SELECT id FROM incidents WHERE rule_id=? AND state='OPEN'", (rule["id"],))
        await engine.evaluate(host, {"metrics": [sample]})
        opened = await db.query("SELECT * FROM incidents WHERE rule_id=? AND state='OPEN'", (rule["id"],))
        assert len(opened) == 1
        await engine.evaluate(host, {"metrics": []})
        assert (await db.query("SELECT state FROM incidents WHERE id=?", (opened[0]["id"],)))[0]["state"] == "OPEN"
        await engine.evaluate(host, {"metrics": [{"key": "cpu.total_pct", "value": 40, "unit": "%", "resource_key": ""}]})
        assert (await db.query("SELECT state FROM incidents WHERE id=?", (opened[0]["id"],)))[0]["state"] == "RESOLVED"
        assert notifier.sent
        await db.close()

    asyncio.run(run())
