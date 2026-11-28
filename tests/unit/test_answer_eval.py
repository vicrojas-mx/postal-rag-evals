import pytest
from tests.evals.answer_eval import grade_cites_section, grade_abstains, grade_same_language

@pytest.mark.parametrize("text, expected, result", [
    pytest.param("1-4.2 Name Tags All employees...", ["8-1.1", "1-4.2", "7.1"], True ,id="Cites"),
    pytest.param("Me gustan los tacos", [None, "10Product"], False, id="does_not_cite"),
    pytest.param("Me gustan los tacos", [], None, id="None_expected"),
])
def test_grade_cites_section(text, expected, result):
    assert grade_cites_section(text, expected) == result

@pytest.mark.parametrize("text, is_oos, result", [
    pytest.param("I don't know.", True, True, id="I_dont_know"),
    pytest.param("I don't know.", False, False, id="I_dont_know_negative"),
    pytest.param("Stamps: ... Cash drawer: I don't know.", False, True, id="I_dont_know_in_text"),
])
def test_grade_abstains(text, is_oos, result):
    assert grade_abstains(text, is_oos) == result


@pytest.mark.parametrize("text, lang, result", [
    pytest.param("I don't know, the house is red and has a cat", "en", True, id="lang_is_english"),
    pytest.param("I don't know, the house is red and has a cat", "es",  False, id="lang_is_english_es"),
    pytest.param("Me gustan los frijoles en casa de mama", "es", True, id="lang_is_spanish"),
    pytest.param("Que transa, yo my brother from thousand battles and many wars and parties", "spanglish", True, id="lang_is_spanglish"),
    pytest.param("I don't know.", "es", None, id="I_dont_know_es_None"),
    pytest.param("Si.", "es", None, id="Si_es_None"),
])
def test_grade_same_language(text, lang, result):
    assert grade_same_language(text, lang) == result