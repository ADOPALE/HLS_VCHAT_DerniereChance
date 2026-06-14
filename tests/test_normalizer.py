from optiflux.data.normalizer import normalize_text, normalize_bool, normalize_sanitary, normalize_exclusions


def test_normalize_text_strips_spaces():
    assert normalize_text(" Oui  ") == "Oui"
    assert normalize_text("OSCAR   ") == "OSCAR"


def test_bool_and_sanitary():
    assert normalize_bool("Oui ") is True
    assert normalize_bool(" non ") is False
    assert normalize_sanitary(" sale ") == "Sale"
    assert normalize_exclusions("Propre; Sale") == {"Propre", "Sale"}
