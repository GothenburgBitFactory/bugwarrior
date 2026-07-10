from bugwarrior.config import schema


def get_mock_service(
    service_class, service_config=None, *, section='unspecified', general_overrides=None
):
    options = {
        'general': {'targets': [section]},
        section: {**(service_config or {}), 'target': section},
    }
    if general_overrides:
        options['general'].update(general_overrides)

    validated_config = service_class.CONFIG_SCHEMA(**options[section])
    main_config = schema.MainSectionConfig(**options['general'])

    return service_class(validated_config, main_config)
