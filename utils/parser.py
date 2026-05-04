import re
from typing import Dict, Any, Optional, Pattern as RegexPattern


class TemplateParser:
    def __init__(self, template: str, types: Dict[str, type] = None, delimiter: str = '|'):
        self.template = template
        self.types = types or {}
        self.delimiter = delimiter

        self.placeholders = self._extract_placeholders(template)

        self._validate_no_delimiter_in_placeholders()

        self.pattern = self._build_pattern()

    @staticmethod
    def _extract_placeholders(template: str) -> list:
        return re.findall(r"\{([^}]+)\}", template)

    def _validate_no_delimiter_in_placeholders(self):
        for match in re.finditer(r"\{([^}]+)\}", self.template):
            if self.delimiter in match.group(1):
                raise ValueError(
                    f"Delimiter '{self.delimiter}' found inside placeholder '{match.group(0)}'. "
                    f"Placeholders cannot contain the delimiter character."
                )

    def _get_regex_for_placeholder(self, placeholder: str) -> str:
        ph_type = self.types.get(placeholder)

        if ph_type == int:
            return r"(\d+)"
        elif ph_type == float:
            return r"(\d+(?:\.\d+)?)"
        elif ph_type == bool:
            return r"(true|false|True|False|1|0|yes|no)"
        else:
            return f"([^{re.escape(self.delimiter)}]+)"

    def _build_pattern(self) -> RegexPattern:
        tokens = []
        last_end = 0

        for match in re.finditer(r"\{([^}]+)\}", self.template):
            start, end = match.span()
            if last_end < start:
                tokens.append(re.escape(self.template[last_end:start]))

            placeholder = match.group(1)
            tokens.append(self._get_regex_for_placeholder(placeholder))

            last_end = end

        if last_end < len(self.template):
            tokens.append(re.escape(self.template[last_end:]))

        pattern_str = ''.join(tokens)
        return re.compile(f"^{pattern_str}$")

    def parse(self, text: str) -> Optional[Dict[str, Any]]:
        match = self.pattern.match(text)
        if not match:
            return None

        result = {}
        group_index = 1

        for placeholder in self.placeholders:
            value = match.group(group_index)
            group_index += 1

            if placeholder in self.types:
                ph_type = self.types[placeholder]
                if ph_type == int:
                    value = int(value)
                elif ph_type == float:
                    value = float(value)
                elif ph_type == bool:
                    value = value.lower() in ('true', '1', 'yes')

            result[placeholder] = value

        return result
