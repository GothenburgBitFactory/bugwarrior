import logging
import re
import typing

from ini2toml.types import IntermediateRepr, Translator
from pydantic import BaseModel

from .schema import ConfigList
from ..services.activecollab2 import ActiveCollabProjects

log = logging.getLogger(__name__)

BOOLS = {
    'general': ['interactive', 'shorten', 'inline_links', 'annotation_links',
                'annotation_comments', 'annotation_newlines',
                'merge_annotations', 'merge_tags', 'replace_tags'],
    'bitbucket': ['filter_merge_requests', 'include_merge_requests',
                  'project_owner_prefix'],
    'bts': ['udd', 'ignore_pending', 'udd_ignore_sponsor'],
    'bugzilla': ['ignore_cc', 'include_needinfos', 'force_rest', 'advanced'],
    'deck': ['import_labels_as_tags'],
    'gitbug': ['import_labels_as_tags'],
    'github': ['include_user_repos', 'import_labels_as_tags',
               'filter_pull_requests', 'exclude_pull_requests',
               'include_user_issues', 'involved_issues', 'project_owner_prefix'
               ],
    'gitlab': ['filter_merge_requests', 'membership', 'owned',
               'import_labels_as_tags', 'include_merge_requests',
               'include_issues', 'include_todos', 'include_all_todos',
               'use_https', 'verify_ssl', 'project_owner_prefix'],
    'jira': ['import_labels_as_tags', 'import_sprints_as_tags', 'use_cookies',
             'verify_ssl'],
    'pagure': ['import_tags'],
    'phabricator': ['ignore_cc', 'ignore_author', 'ignore_owner',
                    'ignore_reviewers', 'only_if_assigned'],
    'pivotaltracker': ['import_blockers', 'import_labels_as_tags',
                       'only_if_author', 'only_if_assigned'],
    'redmine': ['verify_ssl'],
    'taiga': ['include_tasks'],
    'track': ['no_xmlrpc'],
    'trello': ['import_labels_as_tags'],
    'youtrack': ['anonymous', 'use_https', 'verify_ssl', 'incloud_instance',
                 'import_tags'],
}

INTEGERS = {
    'general': ['annotation_length', 'description_length'],
    'activecollab': ['user_id'],
    'activecollab2': ['user_id'],
    'gitbug': ['port'],
    'github': ['body_length'],
    'jira': ['body_length', 'version'],
    'pivotaltracker': ['user_id'],
    'redmine': ['issue_limit'],
    'youtrack': ['port', 'query_limit'],
}

CONFIGLIST = {
    'general': ['targets', 'static_tags', 'static_fields'],
    'github': ['include_repos', 'exclude_repos', 'issue_urls'],
    'pivotaltracker': ['account_ids', 'exclude_projects', 'exclude_stories', 'exclude_tags'],
    'gitlab': ['include_repos', 'exclude_repos'],
    'bitbucket': ['include_repos', 'exclude_repos'],
    'phabricator': ['user_phids', 'project_phids'],
    'trello': ['include_boards', 'include_lists', 'exclude_lists'],
    'bts': ['packages', 'ignore_pkg', 'ignore_src'],
    'deck': ['include_board_ids', 'exclude_board_ids'],
    'bugzilla': ['open_statuses'],
    'pagure': ['include_repos', 'exclude_repos'],
}


def to_type(section: IntermediateRepr, key: str, converter: typing.Callable):
    try:
        val = section[key]
    except KeyError:
        pass
    else:
        section[key] = converter(val)


class BooleanModel(BaseModel):
    """
    Use Pydantic to convert various strings to booleans.

    "True", "False", "yes", "no", etc.
    Adapted from https://docs.pydantic.dev/usage/types/#booleans
    """
    bool_value: bool


def to_bool(section: IntermediateRepr, key: str):
    to_type(section, key, lambda val: BooleanModel(bool_value=val).bool_value)


def to_int(section: IntermediateRepr, key: str):
    to_type(section, key, int)


def to_list(section: IntermediateRepr, key: str):
    to_type(section, key, ConfigList.validate)


def process_values(doc: IntermediateRepr) -> IntermediateRepr:
    for name, section in doc.items():
        if isinstance(name, str):
            if name == 'general' or re.match(r'^flavor\.', name):
                for k in INTEGERS['general']:
                    to_int(section, k)
                for k in CONFIGLIST['general']:
                    to_list(section, k)
                for k in BOOLS['general']:
                    to_bool(section, k)
                for k in ['log.level', 'log.file']:
                    if k in section:
                        section.rename(k, k.replace('.', '_'))
            elif name == 'hooks':
                to_list(section, 'pre_import')
            elif name == 'notifications':
                to_bool(section, 'notifications')
                to_bool(section, 'only_on_new_tasks')
            else:  # services
                service = section['service']

                # Validate and strip prefixes.
                for key in section.keys():
                    prefix = 'ado' if service == 'azuredevops' else service
                    if isinstance(key, str) and key != 'service':
                        newkey, subs = re.subn(f'^{prefix}\\.', '', key)
                        if subs != 1:
                            option = key.split('.').pop()
                            log.warning(
                                f"[{name}]\n{key} <-expected prefix "
                                f"'{prefix}': did you mean "
                                f"'{prefix}.{option}'?")
                        section.rename(key, newkey)

                to_bool(section, 'also_unassigned')
                to_list(section, 'add_tags')
                for k in INTEGERS.get(service, []):
                    to_int(section, k)
                for k in CONFIGLIST.get(service, []):
                    to_list(section, k)
                for k in BOOLS.get(service, []):
                    to_bool(section, k)

            if name == 'activecollab2' and 'projects' in section:
                section['projects'] = ActiveCollabProjects.validate(
                    section['projects'])

    return doc


def activate(translator: Translator):
    profile = translator["bugwarriorrc"]
    profile.description = "Convert 'bugwarriorrc' files to 'bugwarrior.toml'"
    profile.intermediate_processors.append(process_values)
