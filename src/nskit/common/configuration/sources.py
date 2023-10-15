"""Add settings sources."""
from pathlib import Path
from typing import Any, Dict, Tuple

from pydantic.fields import FieldInfo
from pydantic_settings import PydanticBaseSettingsSource

from nskit.common.io import json, toml, yaml


class FileConfigSettingsSource(PydanticBaseSettingsSource):
    """A simple settings source class that loads variables from a parsed file.

    This can parse JSON, TOML, and YAML files based on the extensions.
    """

    def __init__(self, *args, **kwargs):
        """Initialise the Settings Source."""
        super().__init__(*args, **kwargs)
        self.__parsed_contents = None

    def get_field_value(
        self, field: FieldInfo, field_name: str  # noqa: U100
    ) -> Tuple[Any, str, bool]:
        """Get a field value."""
        if self.__parsed_contents is None:
            try:
                encoding = self.config.get('env_file_encoding', 'utf-8')
                file_path = Path(self.config.get('config_file_path'))
                file_type = self.config.get('config_file_type', None)
                file_contents = file_path.read_text(encoding)
                if file_path.suffix.lower() in ['.jsn', '.json'] or (file_type is not None and file_type.lower() == 'json'):
                    self.__parsed_contents = json.loads(file_contents)
                elif file_path.suffix.lower() in ['.tml', '.toml'] or (file_type is not None and file_type.lower() == 'toml'):
                    self.__parsed_contents = toml.loads(file_contents)
                elif file_path.suffix.lower() in ['.yml', '.yaml'] or (file_type is not None and file_type.lower() == 'yaml'):
                    self.__parsed_contents = yaml.loads(file_contents)
            except Exception:
                pass  # nosec B110
        if self.__parsed_contents is not None:
            field_value = self.__parsed_contents.get(field_name)
        else:
            field_value = None
        return field_value, field_name, False

    def prepare_field_value(
        self, field_name: str, field: FieldInfo, value: Any, value_is_complex: bool  # noqa: U100
    ) -> Any:
        """Prepare the field value."""
        return value

    def __call__(self) -> Dict[str, Any]:
        """Call the source."""
        d: Dict[str, Any] = {}

        for field_name, field in self.settings_cls.model_fields.items():
            field_value, field_key, value_is_complex = self.get_field_value(
                field, field_name
            )
            field_value = self.prepare_field_value(
                field_name, field, field_value, value_is_complex
            )
            if field_value is not None:
                d[field_key] = field_value

        return d

    def _load_file(self, file_path: Path, encoding: str) -> Dict[str, Any]:  # noqa: U100
        file_path = Path(file_path)
