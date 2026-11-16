import pytest
from ingest.ingest import find_title, clean_text, clean_text_from_unicode, add_end_pages, add_breadcrumbs

@pytest.mark.parametrize("text, title, start, expected", [
    pytest.param("1-4.2 Name Tags All employees...", "1-4.2 Name Tags", 0, 0, id="exact"),
    pytest.param("10Product Offerings ...", "10 Product Offerings", 0, 0, id="glued"),
    pytest.param("nothing to see here", "1-4.2 Name Tags",0, -1, id="not_found"),
    pytest.param("1-4.2 Name Tags ... 1-4.2 Name Tags", "1-4.2 Name Tags", 5, 20, id="start_skips_first"),
])
def test_find_title(text, title, start, expected):
    assert find_title(text, title, start) == expected

@pytest.mark.parametrize("text, expected", [
    pytest.param("...intentionally left blank...",  "", id="intentionally left blank"),
    pytest.param("Kimo's sneaker mutant 2 killed \nHandbook PO-209 \n2 \u0000\u0007Rules of \n Conduct \n2-1 Postal Service Regulations",  "2 Rules of \n Conduct \n2-1 Postal Service Regulations", id="normal_page_title"),
    pytest.param("August 2023\n2 Rules of Conduct \n 2-1 Postal Service Regulations",  "2 Rules of Conduct \n 2-1 Postal Service Regulations", id="chapter_page_title"),
    pytest.param("August 2023 5",  "", id="one_line_page_title"),
    pytest.param("Handbook PO-209 \nHandbook PO-209, Retail Operations Handbook, covers the duties and responsibilities of Post Office",  "Handbook PO-209, Retail Operations Handbook, covers the duties and responsibilities of Post Office", id="legit_prose")
])
def test_clean_text(text, expected):
    assert clean_text(text) == expected

@pytest.mark.parametrize("text, expected", [
    pytest.param("Go to\uf06e site",  "Go to site", id="remove_unicode"),
    pytest.param("a\u0000b\u0007c",  "abc", id="remove_control_characters"),
    pytest.param("line1\nline2\tTab",  "line1\nline2\tTab", id="newline_and_tab_preserved"),
    pytest.param("“quotes” — dash ®",  "“quotes” — dash ®", id="normal_typography_preserved")
])
def test_clean_text_from_unicode(text, expected):
    assert clean_text_from_unicode(text) == expected

@pytest.mark.parametrize("sections, total_pages, expected", [
    pytest.param([
        {'title': '2-1 Postal Service Regulations', 'depth': 2, 'page_index': 1, 'page_label': '0'},
        {'title': '2-2 Misuse of Postal Service Funds', 'depth': 2, 'page_index': 5, 'page_label': '5'},
        {'title': '2-3 Political Activities', 'depth': 2, 'page_index': 5, 'page_label': '5'}
    ],  10, [
        {'title': '2-1 Postal Service Regulations', 'depth': 2, 'page_index': 1, 'page_label': '0', 'end_page_index':5},
        {'title': '2-2 Misuse of Postal Service Funds', 'depth': 2, 'page_index': 5, 'page_label': '5', 'end_page_index':5},
        {'title': '2-3 Political Activities', 'depth': 2, 'page_index': 5, 'page_label': '5', 'end_page_index':9}
    ], id="add_end_pages")
])
def test_add_end_pages(sections, total_pages, expected):
    add_end_pages(sections, total_pages)
    assert sections == expected

@pytest.mark.parametrize("sections, expected", [
    pytest.param([
        {'title': '7 Seven', 'depth': 1, 'page_index': 1, 'page_label': '0'},
        {'title': '7-1 Seven One', 'depth': 2, 'page_index': 5, 'page_label': '5'},
        {'title': '7-1.2 Seven One Two', 'depth': 3, 'page_index': 5, 'page_label': '5'},
        {'title': '7-2 Seven Two', 'depth': 2, 'page_index': 5, 'page_label': '5'},
        {'title': '8 Eight', 'depth': 1, 'page_index': 9, 'page_label': '9'}
    ], [
        {'title': '7 Seven', 'depth': 1, 'page_index': 1, 'page_label': '0', 'breadcrumbs': '7 Seven'},
        {'title': '7-1 Seven One', 'depth': 2, 'page_index': 5, 'page_label': '5', 'breadcrumbs': '7 Seven > 7-1 Seven One'},
        {'title': '7-1.2 Seven One Two', 'depth': 3, 'page_index': 5, 'page_label': '5', 'breadcrumbs': '7 Seven > 7-1 Seven One > 7-1.2 Seven One Two'},
        {'title': '7-2 Seven Two', 'depth': 2, 'page_index': 5, 'page_label': '5', 'breadcrumbs': '7 Seven > 7-2 Seven Two'},
        {'title': '8 Eight', 'depth': 1, 'page_index': 9, 'page_label': '9', 'breadcrumbs': '8 Eight'}
    ], id="add_breadcrumbs")
])
def test_add_breadcrumbs(sections, expected):
    add_breadcrumbs(sections)
    assert sections == expected