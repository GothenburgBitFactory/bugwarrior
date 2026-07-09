from bugwarrior.config import schema

GENERAL_CONFIG = {'annotation_length': 100, 'description_length': 100}


def get_mock_service(
    service_class, service_config=None, *, section='unspecified', general_overrides=None
):
    options = {
        'general': {**GENERAL_CONFIG, 'targets': [section]},
        section: {**(service_config or {}), 'target': section},
    }
    if general_overrides:
        options['general'].update(general_overrides)

    validated_config = service_class.CONFIG_SCHEMA(**options[section])
    main_config = schema.MainSectionConfig(**options['general'])

    return service_class(validated_config, main_config)
