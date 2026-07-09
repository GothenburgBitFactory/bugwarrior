from bugwarrior.collect import TaskConstructor
from bugwarrior.config import schema
from bugwarrior.services.pagure import PagureIssue, PagureService


class TestPagureIssue:
    arbitrary_issue = {
        'html_url': 'https://pagure.io/repo/issue/1',
        'repo': 'repo',
        'title': 'Hello World',
        'id': 1,
        'date_created': '0',
        'tags': ['Bug', 'Needs Work'],
    }
    arbitrary_extra = {'type': 'issue', 'project': 'repo'}

    def get_issue(self):
        service_config = PagureService.CONFIG_SCHEMA(
            service='pagure',
            target='pagure',
            base_url='https://pagure.io',
            repo='repo',
            import_tags=True,
            tag_template='pg_{{label}}',
        )
        main_config = schema.MainSectionConfig(
            targets=['pagure'], annotation_length=100, description_length=100
        )
        return PagureIssue(
            self.arbitrary_issue, service_config, main_config, self.arbitrary_extra
        )

    def test_get_tags_from_labels_uses_legacy_tag_options(self, caplog):
        issue = self.get_issue()

        assert issue.get_tags() == ['pg_Bug', 'pg_Needs_Work']
        assert (
            'import_tags is deprecated in favor of import_labels_as_tags' in caplog.text
        )
        assert 'tag_template is deprecated in favor of label_template' in caplog.text

    def test_refine_record_does_not_apply_legacy_tag_template_as_field_template(self):
        issue = self.get_issue()

        assert issue.config.templates == {}
        assert TaskConstructor(issue).get_taskwarrior_record()['tags'] == [
            'pg_Bug',
            'pg_Needs_Work',
        ]
