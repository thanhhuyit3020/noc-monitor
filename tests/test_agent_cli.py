from agent.run_agent import build_parser


def test_agent_cli_reads_service_settings_from_environment(monkeypatch):
    monkeypatch.setenv("NOC_AGENT_TOKEN", "test-token")
    monkeypatch.setenv("NOC_PUSH_URL", "https://noc.example/api/agent/push")
    monkeypatch.setenv("NOC_AGENT_INTERVAL_SEC", "30")

    args = build_parser().parse_args([])

    assert (args.token, args.push_url, args.interval) == (
        "test-token", "https://noc.example/api/agent/push", 30
    )
