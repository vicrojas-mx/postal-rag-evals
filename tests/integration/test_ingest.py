import os
import pytest
from ingest.ingest import build_sections

@pytest.fixture(scope="module")
def sections():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(current_dir, "../../data", "po-209_-_2023.pdf")
    return build_sections(pdf_path)

def test_pipeline_returns_319_sections(sections):
    assert len(sections) == 319, "Expected 319 sections after cleaning sections and filtering front matter"

def test_transmittal_is_kept(sections):
    assert sections[0]["title"] == "Transmittal Letter", "Transmittal Letter should be kept"

def test_content_starts_with_section_title(sections):
    errors = []
    for section in sections:
        try:
            assert section["content"].startswith(section["title"]), f"content '{section['content']}' doesn't starts with its title '{section['title']}'"
        except AssertionError as e:
            errors.append(e)
    if errors:
        raise ExceptionGroup("Validation errors", errors)

def test_content_starts_without_section_title(sections):
    errors = []
    for index, section in enumerate(sections):
        try:
            if index < len(sections) -1:
                assert sections[index + 1]["title"] not in section["content"], f"Next section title '{sections[index + 1]["title"]}' in current content of section '{section['title']}'"
        except AssertionError as e:
            errors.append(e)

    if errors:
        raise ExceptionGroup("Validation errors", errors)


def test_marker_do_not_exists_in_line(sections):
    errors = []
    for section in sections[1:]:
        try:
            assert "August 2023" not in section["content"] or "Handbook PO-209" not in section["content"], f"'August 2023 and 'Handbook PO-209' shouldn't be in content of section {section['title']} -"
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
    for index, section in enumerate(sections):
        try:
            if index < len(sections)-1:
                separators = section["breadcrumbs"].split(" > ")
                assert section["depth"]  == len(separators), f"Breadcrumbs must have separators equal to dept: {section['depth']} -1"
        except AssertionError as e:
            errors.append(e)

    if errors:
        raise ExceptionGroup("Validation errors", errors)

