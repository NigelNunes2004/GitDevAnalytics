from app.services import vuln_rules


def test_path_dotenv_is_critical():
    hits = vuln_rules.scan_path(".env")
    assert len(hits) == 1
    assert hits[0].severity == "critical"
    assert hits[0].rule_id == "path_dotenv"


def test_env_example_not_path_risky_alone():
    assert vuln_rules.scan_path(".env.example") == []


def test_content_github_pat_redacted():
    content = "export TOKEN=ghp_abcdefghijklmnopqrstuvwxyz0123456789"
    hits = vuln_rules.scan_content("config.sh", content)
    assert any(h.rule_id == "content_github_pat" for h in hits)
    detail = next(h for h in hits if h.rule_id == "content_github_pat").detail
    assert "ghp_abcdefghijklmnopqrstuvwxyz0123456789" not in detail
    assert "…" in detail


def test_content_aws_key():
    hits = vuln_rules.scan_content("creds.txt", "key=AKIAIOSFODNN7EXAMPLE")
    assert any(h.rule_id == "content_aws_access_key" for h in hits)


def test_private_key_header():
    hits = vuln_rules.scan_content("id_rsa", "-----BEGIN RSA PRIVATE KEY-----\nMIIE")
    assert any(h.rule_id == "content_private_key" for h in hits)
