import pytest

from utils.parser import TemplateParser


@pytest.fixture
def template():
    return "test string with {integer} {boolean} {string} {point}"


def test_types(template):
    parser = TemplateParser(template, types={"integer": int, "boolean": bool})
    input_string = template.format(integer=20, boolean=True, string="string", point=2.5)
    values = parser.parse(input_string)
    assert values
    assert values["integer"] == 20
    assert values["boolean"] == True
    assert values["string"] == "string"
    assert values["point"] == "2.5"
    assert values

    parser = TemplateParser(template, types={"integer": int, "point": float})
    input_string = template.format(
        integer=42, boolean=False, string="string", point=3.14
    )
    values = parser.parse(input_string)
    assert values
    assert values["integer"] == 42
    assert values["boolean"] == "False"
    assert values["string"] == "string"
    assert values["point"] == 3.14

    parser = TemplateParser(template, types={"boolean": bool})
    input_string = template.format(
        integer=61, boolean="yes", string="string", point=2.78
    )
    values = parser.parse(input_string)
    assert values
    assert values["integer"] == "61"
    assert values["boolean"] == 1
    assert values["string"] == "string"
    assert values["point"] == "2.78"

    new_template = template + " random text"
    parser = TemplateParser(new_template, types={"boolean": bool}, delimiter=" ")
    input_string = new_template.format(
        integer=17, boolean="1", string="string", point=2.78
    )
    values = parser.parse(input_string)
    assert values
    assert values["integer"] == "17"
    assert values["boolean"] == 1
    assert values["string"] == "string"
    assert values["point"] == "2.78"


def test_invalid_input(template):
    parser = TemplateParser(template, delimiter=" ")
    new_template = template + " {bug}"
    input_string = new_template.format(
        integer=73, boolean=False, string="string", point=1.0, bug="oh"
    )
    values = parser.parse(input_string)
    assert values is None

    parser = TemplateParser(template, types={"boolean": int}, delimiter=" ")
    input_string = template.format(integer=1, boolean=True, string="string", point=0.5)
    values = parser.parse(input_string)
    assert values is None


def test_invalid_template():
    template_string = "text {param|other}|{value}"
    with pytest.raises(ValueError):
        _ = TemplateParser(template_string, delimiter="|")
