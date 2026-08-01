import json
from pathlib import Path

from generic_parser.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


def test_location_id_command(capsys) -> None:
    result = main(["location-id", "https://www.kleinanzeigen.de/s-nrw/test/k0l928r50"])
    assert result == 0
    assert capsys.readouterr().out.strip() == "928"


def test_parse_fixture_as_json(capsys) -> None:
    result = main(
        [
            "parse-fixture",
            str(FIXTURES / "kleinanzeigen_results.html"),
            "--json",
        ]
    )
    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert [item["id"] for item in payload] == ["10001", "10002"]
