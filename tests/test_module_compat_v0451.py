from pathlib import Path

from generic_parser.integrations import evercade_profile, snes_pal_profile
from generic_parser.module_api import MODULE_CONTRACT, ModuleSearchProfile, run_contract_self_tests

ROOT = Path(__file__).resolve().parents[1]


def test_module_contract_and_project_adapters_remain_compatible() -> None:
    assert MODULE_CONTRACT == 'generic-parser-module-v1'
    evercade = evercade_profile('Interplay Collection 1', market_value=30)
    assert evercade.query == 'Evercade Interplay Collection 1'
    assert 'Blaze' in evercade.brands
    snes = snes_pal_profile('Super Metroid', market_value=70)
    assert 'PAL' in snes.required_terms
    assert 'NTSC' in snes.excluded_terms


def test_empty_optional_fields_still_do_not_reach_reference_request() -> None:
    profile = ModuleSearchProfile(query='Evercade', required_terms=[], excluded_terms=[], brands=None)
    payload = profile.to_legacy_payload(page=0, source='auto')
    assert 'required_terms' not in payload
    assert 'excluded_terms' not in payload
    assert 'brands' not in payload


def test_contract_self_test_remains_network_free() -> None:
    result = run_contract_self_tests()
    assert result['ok'] is True
    assert result['network_used'] is False


def test_0451_does_not_modify_search_service_implementation() -> None:
    identity = (ROOT / 'src/generic_parser/build_identity_v0451.py').read_text(encoding='utf-8')
    service = (ROOT / 'src/generic_parser/search_service_v0450.py').read_text(encoding='utf-8')
    bootstrap = (ROOT / 'src/generic_parser/cloudflare_v0451.py').read_text(encoding='utf-8')
    assert 'SEARCH_MODULE = "generic_parser.search_service_v0450"' in identity
    assert 'from . import search_service_v0444 as reference' in service
    assert 'result = await reference.search_page(payload, request)' in service
    assert 'search_behavior_changed": False' in bootstrap
    assert '@app.post("/api/search")' in bootstrap
    assert '@app.post("/api/module/search")' in bootstrap
    assert '@app.post("/api/module/v1/search")' in bootstrap
