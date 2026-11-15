import os
import pytest
import re
from ingest.ingest import build_sections, find_title

@pytest.fixture(scope="module")
def sections():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(current_dir, "../../data", "po-209_-_2023.pdf")
    return build_sections(pdf_path)

def test_pipeline_returns_319_sections(sections):
    assert len(sections) == 319, "Expected 319 sections after cleaning sections and filtering front matter"

def test_transmittal_is_kept(sections):
    assert any(section.get("title") == "Transmittal Letter" for section in sections), "Transmittal Letter should be kept"


def test_content_starts_with_section_title(sections):
    errors = []
    for section in sections:
        try:
            # There are some sections have the content starting with the section title, but
            # there's a missing space following the title in the content.  So to maintain the
            # integrity on the document, we used the function find_title that validates the cases
            # where the title is searched normally with a space (that happens in almost all sections)
            # and the case where the document contents has no space after the title.
            content_starts_with_section_title = find_title(section["content"], section["title"]) == 0
            assert content_starts_with_section_title, f"content '{section['content'][:70]}' doesn't start with its title '{section['title']}'"
        except AssertionError as e:
            errors.append(e)
    if errors:
        raise ExceptionGroup("Validation errors", errors)

def test_content_does_not_contains_next_section_title(sections):
    errors = []
    for index, section in enumerate(sections):
        try:
            if index < len(sections) -1:
                assert find_title(section["content"], sections[index + 1]["title"]) == -1, f"Next section title '{sections[index + 1]["title"]}' in current content of section '{section['title']}'"
        except AssertionError as e:
            errors.append(e)

    if errors:
        raise ExceptionGroup("Validation errors", errors)


def test_marker_do_not_exists_in_content(sections):
    errors = []
    for section in sections[1:]:
        try:
            marker_found = re.search(r"August 2023 \d+|\d+ Handbook PO-209", section["content"])
            assert not marker_found, f"'August 2023' and 'Handbook PO-209' shouldn't be in content of section {section['title']} -"
        except AssertionError as e:
            errors.append(e)
    if errors:
        raise ExceptionGroup("Validation errors", errors)

def test_content_not_empty(sections):
    errors = []
    for section in (sections):
        try:
            assert section["content"], f"Content shouldn't be empty in section '{section['title']}' "
        except AssertionError as e:
            errors.append(e)
    if errors:
        raise ExceptionGroup("Validation errors", errors)


def test_breadcrumbs_end_with_title(sections):
    errors = []
    for section in (sections):
        try:
            assert section["breadcrumbs"].endswith(section["title"]), f"Breadcrumbs section should end with title '{section['title']}'"
        except AssertionError as e:
            errors.append(e)
    if errors:
        raise ExceptionGroup("Validation errors", errors)


def test_breadcrumbs_have_right_depth(sections):
    errors = []
    for section in sections:
        try:
            separators = section["breadcrumbs"].split(" > ")
            assert section["depth"] == len(
                separators), f"Breadcrumbs must have separators equal to dept: {section['depth']} "
        except AssertionError as e:
            errors.append(e)

    if errors:
        raise ExceptionGroup("Validation errors", errors)

def test_front_matter_is_removed(sections:list[dict]):
    errors = []

    # Checks the front matter is removed, except Transmittal Letter
    roman_pages =  [section for section in sections if not section["page_label"].isdigit()]
    for roman_page in roman_pages:
        try:
            assert roman_page["title"] == "Transmittal Letter", f"Page title: '{roman_page['title']}' should be 'Transmittal Letter'"
        except AssertionError as e:
            errors.append(e)

    if errors:
        raise ExceptionGroup("Validation errors", errors)

