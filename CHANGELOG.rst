1.2.0 ----- Lots of updates from various contributors: - Enable setuptools test command `d38fad025 <https://github.com/ralphbean/bugwarrior/commit/d38fad0256ff76129630cf0c636690e6654c153a>`_ - Merge pull request #222 from koobs/patch-2 `7f9cdce9c <https://github.com/ralphbean/bugwarrior/commit/7f9cdce9cf893bb14bbc917d775010ffb575d7dd>`_ - Added only_if_assigned to gitlab `0f6fea7fc <https://github.com/ralphbean/bugwarrior/commit/0f6fea7fc7d57af6faf7193fc30f36be020f3f3b>`_ - Merge pull request #224 from qwertos/feature-gitlab_only_assigned `156b5a908 <https://github.com/ralphbean/bugwarrior/commit/156b5a908f2a2d16b514a6f5c0bcb3bb812d34b4>`_ - Add a taskwarrior UDA for bugzilla status `2be150f6a <https://github.com/ralphbean/bugwarrior/commit/2be150f6a9e72f7ce9765158eb90b92cba811338>`_ - Make BZ bug statuses configurable `ac30a2241 <https://github.com/ralphbean/bugwarrior/commit/ac30a2241af5fedc4b4c7e382f82511fe1535d2d>`_ - Ooops, add status field to tests `6411e4803 <https://github.com/ralphbean/bugwarrior/commit/6411e48038d25369b9494e36d121d1472265133c>`_ - Merge pull request #226 from ryansb/feature/moarBugzillaStatus `90c81db1b <https://github.com/ralphbean/bugwarrior/commit/90c81db1b12d1adf22b0d7545ca63734103e9375>`_ - [notifications] only_on_new_tasks option `b4a67ebfd <https://github.com/ralphbean/bugwarrior/commit/b4a67ebfd7e1c31ccc51bdd01cf76ef95c765df0>`_ - Merge pull request #228 from devenv/only_on_new_tasks `89ef3d746 <https://github.com/ralphbean/bugwarrior/commit/89ef3d746ed354338486f2bc865cb25a5f9da2fe>`_ - jira estimate UDA `2317a0516 <https://github.com/ralphbean/bugwarrior/commit/2317a0516d3d680291d205b7badaeb78e5ec1799>`_ - Merge pull request #227 from devenv/jira_est `06adc5b16 <https://github.com/ralphbean/bugwarrior/commit/06adc5b166be618641283dff2b85e07cd6d91bb0>`_ - Include an option to disable HTTPS for GitLab. `616a389d7 <https://github.com/ralphbean/bugwarrior/commit/616a389d75900b407ad813739c8ba0eb27e07fff>`_ - Support needinfo bugs where you are not CC/assignee/reporter `8ef53be9f <https://github.com/ralphbean/bugwarrior/commit/8ef53be9f4edc8ba0f9c06135fb98886d049a852>`_ - gitlab: work around gitlab pagination bug `4caaa28ed <https://github.com/ralphbean/bugwarrior/commit/4caaa28edccb5ae1c8f4f83d83594afa3c6d8cb6>`_ - gitlab: add uda for work-in-progress flag `fe940c268 <https://github.com/ralphbean/bugwarrior/commit/fe940c2686632e79acef382fd72b721b2bf5659f>`_ - githubutils: allow getting a key from the result `28e37218c <https://github.com/ralphbean/bugwarrior/commit/28e37218cbccc45c00b77694ab6e4ffb94330013>`_ - github: add involved_issues option `67b93eb6e <https://github.com/ralphbean/bugwarrior/commit/67b93eb6e34d404574ea0c7a91601bbe45d4cb1e>`_ - gitlab: bail on empty or False results `62008a22d <https://github.com/ralphbean/bugwarrior/commit/62008a22d9d9528d5642aa00e7f8c969967c833c>`_ - Only import active Gitlab issues and merge requests `5890fe9ad <https://github.com/ralphbean/bugwarrior/commit/5890fe9ad3dc6a373e4e1ad097219de2d25534f8>`_ - Merge pull request #231 from ryansb/feature/needinfos `6722d2b96 <https://github.com/ralphbean/bugwarrior/commit/6722d2b96be217db035e7ecad9ebef104deee164>`_ - Merge pull request #233 from mathstuf/gitlab-work-in-progress-flag `c4bbd955d <https://github.com/ralphbean/bugwarrior/commit/c4bbd955d9ffcc0026985c88242ce178b3b0df1b>`_ - Merge pull request #234 from mathstuf/github-involved-issues `6ff7cfc7d <https://github.com/ralphbean/bugwarrior/commit/6ff7cfc7d0792583cca8dd093cfe996fc11b4f14>`_ - Merge pull request #235 from LordGaav/feature/close-gitlab-issues `0664bd02c <https://github.com/ralphbean/bugwarrior/commit/0664bd02cc9754f308a39f0fbcc938161fb6f134>`_ - Merge pull request #232 from mathstuf/handle-broken-gitlab-pagination `1677807bf <https://github.com/ralphbean/bugwarrior/commit/1677807bffb182d0654f61d84d0548507fbb47e5>`_ - Add Gitlab's assignee and author field to tasks `b7dd5c3e2 <https://github.com/ralphbean/bugwarrior/commit/b7dd5c3e2b2f775870a33b8ccacf1c0ef66ba413>`_ - Add documentation on UDA fields `c88209063 <https://github.com/ralphbean/bugwarrior/commit/c88209063475d236123a4f95533a0ef7d169606d>`_ - Add config option `8c2c8c0c9 <https://github.com/ralphbean/bugwarrior/commit/8c2c8c0c9f5866b6629d6be0bb14fdbc2767e69b>`_ - ewwwww, trailing whitespace `c48348fbb <https://github.com/ralphbean/bugwarrior/commit/c48348fbb0f7baf378a04ff2a7bd5c49d6fca576>`_ - Make comment annotation configurable `1667619bf <https://github.com/ralphbean/bugwarrior/commit/1667619bf8d099efbf4b8f509544ade28417254b>`_ - Clarify annotating by inverting conditional for `annotation_comments` `31c3ecdd3 <https://github.com/ralphbean/bugwarrior/commit/31c3ecdd3162714d6675a5d22a09dda6bc745a88>`_ - Merge pull request #237 from ryansb/feature/noAnnotations `1887d7095 <https://github.com/ralphbean/bugwarrior/commit/1887d7095187ba2100706830ae2f9a9fa9b58555>`_ - Merge pull request #236 from LordGaav/feature/gitlab-author-assignee-field `f84eca72f <https://github.com/ralphbean/bugwarrior/commit/f84eca72f6bdde9c480d56c72bf7c47a335a9e57>`_ - Document use_https for gitlab. `5d95424f6 <https://github.com/ralphbean/bugwarrior/commit/5d95424f6f0c09bf0e54683ac1fa0c52ca2a3d11>`_ - Merge branch 'https-or-http' into develop `f3b63baf1 <https://github.com/ralphbean/bugwarrior/commit/f3b63baf1298f64d95d6f39656520b4261150edd>`_
Changelog
=========

1.1.4
-----

- Alter default JIRA query to handle situations in which instances do not use the column names we are expecting. `34d99341e <https://github.com/ralphbean/bugwarrior/commit/34d99341e463cbdedd2ed12493c885c3ec771eec>`_
- Merge pull request #213 from coddingtonbear/generalize_jira_query `9ef8f17e3 <https://github.com/ralphbean/bugwarrior/commit/9ef8f17e37105cbc10bb79fc9191b5a3da25de19>`_
- It's a gerund! `5189ef81d <https://github.com/ralphbean/bugwarrior/commit/5189ef81db1d389ecf32e464e13c9fa53c440b9f>`_
- gitlab: handle pagination `3067b32bc <https://github.com/ralphbean/bugwarrior/commit/3067b32bc341008f8a4fab553cb2a115ae2cec01>`_
- gitlab: fix documentation typo `a2f1e87c9 <https://github.com/ralphbean/bugwarrior/commit/a2f1e87c96ac40b8237bc630aeb3d445ec69b437>`_
- gitlab: add a state entry `7790450a3 <https://github.com/ralphbean/bugwarrior/commit/7790450a3cc2eb042325b21f8f3e30eaa2e4a6f0>`_
- gitlab: fill in milestone and update/create time `a37eff259 <https://github.com/ralphbean/bugwarrior/commit/a37eff2596804e0028a1510468e22e7938b5c08f>`_
- Merge pull request #214 from mathstuf/gitlab-pagination `befe0ed46 <https://github.com/ralphbean/bugwarrior/commit/befe0ed4666934c4cbdf97e2910c2fee514f36aa>`_
- Phabricator service is not called phabricator, but phab `df96e346b <https://github.com/ralphbean/bugwarrior/commit/df96e346b70dbc38e65aec68b687da181583d3b6>`_
- Phabricator service: Adding option to filter on users and projects `584b28fc3 <https://github.com/ralphbean/bugwarrior/commit/584b28fc3f8fafa6ec2ade3680ee7602dd9b50d1>`_
- Unified filtering handling `29714c432 <https://github.com/ralphbean/bugwarrior/commit/29714c432e7600b8708a89830acb40870ac534c4>`_
- Fixing a slightly-out-of-date gitlab test. `7174361ab <https://github.com/ralphbean/bugwarrior/commit/7174361ab3bd51ba5e4959dc7d7209cabfa9d1c7>`_
- Adding the documentation for phabricator filtering options. `15a6a43a0 <https://github.com/ralphbean/bugwarrior/commit/15a6a43a0249dc3441e18a7f8aae401839f1478d>`_
- Fix link to remove the browser warning of invalid certificate `77f84855b <https://github.com/ralphbean/bugwarrior/commit/77f84855b09da5af213c1ae7638d61a4d9ba34c2>`_
- Merge pull request #218 from jonan/develop `07ef02dbd <https://github.com/ralphbean/bugwarrior/commit/07ef02dbd7c15026e59780dc743a554b5abf8d59>`_
- Merge pull request #216 from ivan-cukic/develop `1f1f4f00e <https://github.com/ralphbean/bugwarrior/commit/1f1f4f00e72af4bc734690737d4ef0c9a0ebfd5c>`_
- Add tests to MANIFEST.in `a4d643234 <https://github.com/ralphbean/bugwarrior/commit/a4d6432343cdcf1862b87a6d5ea381c8fa9e45c8>`_
- Merge pull request #221 from koobs/patch-1 `42d320a05 <https://github.com/ralphbean/bugwarrior/commit/42d320a0581fe6d7f6cd79cab5460433fac70c1b>`_

1.1.3
-----

- Bugfix for legacy_matching. `b973e925b <https://github.com/ralphbean/bugwarrior/commit/b973e925bdda8da35b5090ff82212ba4a3a8190c>`_

1.1.2
-----

- Make merging in annotations to the task db optional. `52468ac5c <https://github.com/ralphbean/bugwarrior/commit/52468ac5ca2a18aca23fc5fb7733cc9caa6dadfe>`_
- Merge pull request #207 from ralphbean/feature/optional-annotations `9b65f6cf4 <https://github.com/ralphbean/bugwarrior/commit/9b65f6cf47b23852647c0963875c3c7f949d11d9>`_
- Fixup notification error with bad encoding `2348b8ac5 <https://github.com/ralphbean/bugwarrior/commit/2348b8ac5001f1deb83d6400f5dfba2587ed55a0>`_
- Merge pull request #208 from metal3d/develop `e7928d343 <https://github.com/ralphbean/bugwarrior/commit/e7928d343f3d954152f1eb18d79c13335d4b7da5>`_

1.1.1
-----

- Fixes a couple minor typos in service classpaths listed in DeferredImportingDict. `7844a0beb <https://github.com/ralphbean/bugwarrior/commit/7844a0beb0bce92009338327fe3a7c8cc4c78196>`_
- Merge pull request #206 from coddingtonbear/fix_service_classpath `d50486ee6 <https://github.com/ralphbean/bugwarrior/commit/d50486ee6cb7cf2abc68a92bf0fc5247fb58ee51>`_

1.1.0
-----

- Rudimentary support for VersionOne. `c774952e9 <https://github.com/ralphbean/bugwarrior/commit/c774952e9cb189f37ca29629604ec5a150d6b7c5>`_
- Adding working VersionOne implementation.  Fixes #149. `1ee7a01e7 <https://github.com/ralphbean/bugwarrior/commit/1ee7a01e7e30bdb907da28a7c7ff839dab2f1d90>`_
- Collect the OID, too, just in case it might be needed for future API operations. `c0e7c88d3 <https://github.com/ralphbean/bugwarrior/commit/c0e7c88d37c1e3be063d13fb3de21f81b2dcc6d9>`_
- Add story number and priority fields. `a98fb97bf <https://github.com/ralphbean/bugwarrior/commit/a98fb97bf232d6e2e558382534e624a9243ea3b1>`_
- Follow the same pattern as the redmine importer for what to name the project name configuration option. `f5f9ef067 <https://github.com/ralphbean/bugwarrior/commit/f5f9ef067de332ffc1e27339bc4922039ef79016>`_
- Adding documentation for new VersionOnes service. `894bfec02 <https://github.com/ralphbean/bugwarrior/commit/894bfec022ecfe65e73f1745965564832373151d>`_
- Assemble keyring URL in get_keyring_service method; allow blank passwords to be entered. `709bd7036 <https://github.com/ralphbean/bugwarrior/commit/709bd7036cc57ef5fc0567048f0b0f901585b0c2>`_
- There's no reason for this to be a set rather than just a normal tuple. `a43c28386 <https://github.com/ralphbean/bugwarrior/commit/a43c283865cb4935fdedf55ab5c671ee0f95f750>`_
- Merge pull request #150 from coddingtonbear/add_version_one `8297f18d7 <https://github.com/ralphbean/bugwarrior/commit/8297f18d75a039b2fd3254a2430460975c8f2694>`_
- Further limit which tasks are returned to only actionable items. `6e8333e0a <https://github.com/ralphbean/bugwarrior/commit/6e8333e0ac410fa183fa5d1d40b6f826afab07ef>`_
- Merge pull request #152 from coddingtonbear/versionone_tweaks `4da7f2208 <https://github.com/ralphbean/bugwarrior/commit/4da7f2208f481e5e9a6d35c8be810ac141af67e8>`_
- Adding VersionOne link to readme. `4a0ad1779 <https://github.com/ralphbean/bugwarrior/commit/4a0ad1779b947c94fada45b632c7986798581eca>`_
- Merge pull request #153 from coddingtonbear/versionone_in_readme `b4f757f2c <https://github.com/ralphbean/bugwarrior/commit/b4f757f2c3928abc99c507752d0e2ce8fd4b2ab2>`_
- Handle debugging in odd case where uuid doesn't return a task. `b987c9859 <https://github.com/ralphbean/bugwarrior/commit/b987c985994f7daac3849b5b55b717a234b31c7b>`_
- Messy... `0f11061e4 <https://github.com/ralphbean/bugwarrior/commit/0f11061e4c26298137bd66a4a5eb980397cbbfec>`_
- Extract priorities from redmine responses appropriately. `6dccc13c7 <https://github.com/ralphbean/bugwarrior/commit/6dccc13c780dfbdae536a3d35795e70e0073dc43>`_
- Use priority Name instead of id. `89b0195fc <https://github.com/ralphbean/bugwarrior/commit/89b0195fcbd164139e3344728a448c749202041b>`_
- Add a test for new redmine behavior and fix another bug. `4a3960256 <https://github.com/ralphbean/bugwarrior/commit/4a39602563285d7d1a37e6126c5279df3e303ba7>`_
- Merge pull request #155 from ralphbean/feature/redmine-priorities `2a8c1d889 <https://github.com/ralphbean/bugwarrior/commit/2a8c1d889401290e769f691a7c80d3c9023c41cc>`_
- Add a github repo UDA. `d136b9894 <https://github.com/ralphbean/bugwarrior/commit/d136b98945071b2e42f9d5bb3187916be34352b8>`_
- Allow trac scheme to be configurable. `e932b20d6 <https://github.com/ralphbean/bugwarrior/commit/e932b20d661c43c92b64095e5c91e81d9b72cf6a>`_
- Mention the new githubrepo UDA in the docs. `51ac27931 <https://github.com/ralphbean/bugwarrior/commit/51ac27931fc8a139004b49772fe25a19e42221b6>`_
- Add bugzilla bug id as a UDA. `a3dc9aebc <https://github.com/ralphbean/bugwarrior/commit/a3dc9aebc122a691ef3a0772a99e10ef96c10a15>`_
- Document the ignore_cc option. `d74788b50 <https://github.com/ralphbean/bugwarrior/commit/d74788b50153f66a771d3c74286339714067ad52>`_
- Merge pull request #164 from ralphbean/feature/bz-filter `d0e608394 <https://github.com/ralphbean/bugwarrior/commit/d0e608394749d7d514b546e9d8e14eec9e89486b>`_
- Numeric, for sure. `ea50d7107 <https://github.com/ralphbean/bugwarrior/commit/ea50d710787cc75225187db03dc3b5b07d820bc0>`_
- Merge pull request #163 from ralphbean/feature/bz-id-uda `c56ae0bbd <https://github.com/ralphbean/bugwarrior/commit/c56ae0bbdee9fee3e09e0c936ba454d559b8aa19>`_
- Merge pull request #162 from ralphbean/feature/trac-scheme `0e65c59c6 <https://github.com/ralphbean/bugwarrior/commit/0e65c59c608275acd48626c278692a67e56a8793>`_
- Merge pull request #161 from ralphbean/feature/github-updates `7dc3a69e4 <https://github.com/ralphbean/bugwarrior/commit/7dc3a69e43ab1fba32f1e098992b472f8cb14fb4>`_
- Normalize github labels to fit tag syntax `bc04158c1 <https://github.com/ralphbean/bugwarrior/commit/bc04158c1919ccb82041959c2410b7aa410f1a58>`_
- add test `177d69be6 <https://github.com/ralphbean/bugwarrior/commit/177d69be6ec19023422bf167f2c1835c56d184fb>`_
- trac: use CSV downloads if TracXmlRpc is not available `5bc5a768f <https://github.com/ralphbean/bugwarrior/commit/5bc5a768f57e4aac9f0adf4cd8e2715c393a5c08>`_
- Clarify that filtering doesn't work for Bugzilla `f3f800118 <https://github.com/ralphbean/bugwarrior/commit/f3f800118aed84774c40806fec8b536636fce0ff>`_
- Merge pull request #168 from djmitche/bz-docs-fix `c3627304f <https://github.com/ralphbean/bugwarrior/commit/c3627304f1942685d6f389258e20897a16f01efe>`_
- Merge pull request #166 from djmitche/normalize-github-tags `84a084550 <https://github.com/ralphbean/bugwarrior/commit/84a084550ec5933e01c8c6b610b950ca34fa87f1>`_
- Merge pull request #167 from djmitche/trac-csv `8a696a8a2 <https://github.com/ralphbean/bugwarrior/commit/8a696a8a294011c6f8802cd19c88b1176efe9bca>`_
- Only use github issues `821a864dc <https://github.com/ralphbean/bugwarrior/commit/821a864dcdd2ff35fc5383cb41690ece5f0aefc6>`_
- add test `b5b76d5db <https://github.com/ralphbean/bugwarrior/commit/b5b76d5db4fed7ffb43ad70b6ccdf0b8ec9164d1>`_
- remove non-functional optparse usage `51f06c89f <https://github.com/ralphbean/bugwarrior/commit/51f06c89f5a104371e3b95d661b25721ebc6cab6>`_
- VersionOne: Adds support for timebox data and due dates. `2b0609bed <https://github.com/ralphbean/bugwarrior/commit/2b0609bedf9e4b70e1add171c8952e8e28f33433>`_
- Add a --dry-run option `ae66d6ae8 <https://github.com/ralphbean/bugwarrior/commit/ae66d6ae806b12f2b4ddb6fa3a9f68ac4e2e3d73>`_
- Merge pull request #170 from djmitche/issue148 `fe1e1557e <https://github.com/ralphbean/bugwarrior/commit/fe1e1557e954fb951a676736c7bb876077968349>`_
- Allow users to specify a Bugzilla query URL `014f5b60a <https://github.com/ralphbean/bugwarrior/commit/014f5b60a4669b420147f4374f1dfd96e59c4b44>`_
- Merge pull request #172 from djmitche/issue160 `c050b6553 <https://github.com/ralphbean/bugwarrior/commit/c050b6553177dc4cd6ce160bfc4052b73bf74fd0>`_
- Merge pull request #169 from coddingtonbear/add_versionone_timebox_and_due_date `c328c2503 <https://github.com/ralphbean/bugwarrior/commit/c328c2503d2bfc0f493abbc0b845fe797bb067e4>`_
- Better handling for due dates for VersionOne tasks. `cafd926f2 <https://github.com/ralphbean/bugwarrior/commit/cafd926f22268580493efbe19dfb47b631ee9eeb>`_
- Merge pull request #173 from coddingtonbear/add_timezone_support_to_versionone `fb0c8f832 <https://github.com/ralphbean/bugwarrior/commit/fb0c8f8322987ad9e4b30a7d1e30f82c8cfa9de5>`_
- Adding minimal documentation regarding what external packages are required for each service. `0cb81a124 <https://github.com/ralphbean/bugwarrior/commit/0cb81a1240ae67f55e53b9b616513167d29b54bf>`_
- Merge branch 'normalize-github-tags' of git://github.com/djmitche/bugwarrior into develop `634601f7d <https://github.com/ralphbean/bugwarrior/commit/634601f7d42aa8376f00a0ff14f56203cdb7e160>`_
- Fix labels-as-tags test. `85d9a6822 <https://github.com/ralphbean/bugwarrior/commit/85d9a6822b0641b7c36666a7dbd7a2e8550090dd>`_
- Merge pull request #175 from coddingtonbear/add_external_requirements `28c27d006 <https://github.com/ralphbean/bugwarrior/commit/28c27d006cae300283db2fba3026d7b24ea11ff4>`_
- Use os.makedirs for directory creation. `15e537c28 <https://github.com/ralphbean/bugwarrior/commit/15e537c28bb6b180be94991611813265f2b214a6>`_
- Add an option to disable SSL verification for Jira `37354467e <https://github.com/ralphbean/bugwarrior/commit/37354467efc897a09aadf0367ffb29177126856c>`_
- Add doc about jira.verify_ssl `ec8b773a6 <https://github.com/ralphbean/bugwarrior/commit/ec8b773a65c1e6090b2a6b51865a75f73a45cebe>`_
- Merge pull request #179 from mavant/feature/ssl-verify-flag `df19eda63 <https://github.com/ralphbean/bugwarrior/commit/df19eda6329d0a50de9cd5d9eb4edf991426ca50>`_
- Merge pull request #178 from mavant/develop `dbef39509 <https://github.com/ralphbean/bugwarrior/commit/dbef395092f44061687a5b51cdf413a1b5bc96df>`_
- Adding handling for NoneDeref instances returned by VersionOne. `0d0d9bc4d <https://github.com/ralphbean/bugwarrior/commit/0d0d9bc4d1fb29a9fdee3c21f27891ea7e2a9291>`_
- Merge pull request #180 from coddingtonbear/handle_v1_nonederef `e3a959988 <https://github.com/ralphbean/bugwarrior/commit/e3a959988891092b097a9a1b488beafc2e706e84>`_
- Fix 'not empty' filter for string-type UDAs, #181 `e7f2328fc <https://github.com/ralphbean/bugwarrior/commit/e7f2328fc5bee574b6fc51120e1e5026042f5e54>`_
- Merge pull request #182 from bmbove/empty-filter-fix `765b90759 <https://github.com/ralphbean/bugwarrior/commit/765b907595e4f8ffea4185a2a5da04acea5bcb3a>`_
- Show a message to the user in the event that we were unable to perform the operation. `4b0184b6f <https://github.com/ralphbean/bugwarrior/commit/4b0184b6fc6158792c045a3c5750e277e7e1283e>`_
- Merge pull request #183 from coddingtonbear/show_errors_when_unable_to_add `e407d6e85 <https://github.com/ralphbean/bugwarrior/commit/e407d6e8546c77027d947ea2937763af1115bc3f>`_
- Adding a new 'bugwarrior-uda' command that will print a list of UDAs to the console directly. `054e5045c <https://github.com/ralphbean/bugwarrior/commit/054e5045cc58e642731c9a7eefe9a7542eef370c>`_
- Adding a note about how to export UDAs. `64ad46544 <https://github.com/ralphbean/bugwarrior/commit/64ad465449fdd37066cad465c68f85bbcf3e270f>`_
- Also add markers so users will find it easier to know which UDAs were generated by Bugwarrior. `c5f97314c <https://github.com/ralphbean/bugwarrior/commit/c5f97314cdf9ba327a1160f8706541acdfe384a2>`_
- Merge pull request #184 from coddingtonbear/add_uda_export_command `462794241 <https://github.com/ralphbean/bugwarrior/commit/462794241c9ce85a28a1f25fd364d20099dd03bb>`_
- Hack to let task-2.4.x search for url UDAs. `ae3db7d94 <https://github.com/ralphbean/bugwarrior/commit/ae3db7d941d338f9f49b68db57a50af384106768>`_
- Merge pull request #185 from ralphbean/feature/url-hack `a59743514 <https://github.com/ralphbean/bugwarrior/commit/a597435147ad9b0616afc135de3d8e09bb16bf5d>`_
- Typofix. `a9d273637 <https://github.com/ralphbean/bugwarrior/commit/a9d273637c23ff2d0fe23713b1b9e0411e49fae6>`_
- Merge branch 'feature/url-hack' into develop `c01f68359 <https://github.com/ralphbean/bugwarrior/commit/c01f683590d790d60d872138a9919c884d2ff802>`_
- fixed docs for Jira, requirements `7664e1264 <https://github.com/ralphbean/bugwarrior/commit/7664e12645e70b9392b666f36e9ac074c74d0898>`_
- config: add support for XDG paths `feda0993d <https://github.com/ralphbean/bugwarrior/commit/feda0993d852ccb450c4d59312159bb6bf2a311b>`_
- docs: update references to .bugwarriorrc `07148bce5 <https://github.com/ralphbean/bugwarrior/commit/07148bce5cafdf6d69225e71eb14c7c8ce86f16a>`_
- Mention nosetests in the contributing docs. `c1d54e908 <https://github.com/ralphbean/bugwarrior/commit/c1d54e908f82bfe3e719cabfa778252f13e1f645>`_
- README: use https where possible `2f8d2b26c <https://github.com/ralphbean/bugwarrior/commit/2f8d2b26c321ccbe4cfe5840b67c447a2738cedd>`_
- docs: fix a typo `4e94081f0 <https://github.com/ralphbean/bugwarrior/commit/4e94081f04dbbb417cbe30781f9cf285a048fd73>`_
- gitlab: add initial gitlab support `23c1d2491 <https://github.com/ralphbean/bugwarrior/commit/23c1d2491b6441c57c4aea9231089da2db1dfbfb>`_
- gitlab: add docs `4d2dedf5b <https://github.com/ralphbean/bugwarrior/commit/4d2dedf5b43693c085b16f67538f6b536fa98fb8>`_
- gitlab: add tests `8215127cf <https://github.com/ralphbean/bugwarrior/commit/8215127cf626c598889984551461219d866ec6d9>`_
- config: add --flavor option `6af8b6f0f <https://github.com/ralphbean/bugwarrior/commit/6af8b6f0f2c75b720693bfc018d530032506b49f>`_
- Merge pull request #192 from mathstuf/configuration-option `063d03d27 <https://github.com/ralphbean/bugwarrior/commit/063d03d276c027d19137e4f0d45d89dd905578ce>`_
- Merge pull request #190 from mathstuf/xdg-support `ce5b8ffda <https://github.com/ralphbean/bugwarrior/commit/ce5b8ffdaa33ecfee782b71f4f9a3d6cf6bcf23d>`_
- Merge pull request #191 from mathstuf/gitlab-support `ed9af7ff5 <https://github.com/ralphbean/bugwarrior/commit/ed9af7ff599c7a2e5e95846d962d8d52cb094b9a>`_
- config: give a meaningful error message for empty targets `7d910ff29 <https://github.com/ralphbean/bugwarrior/commit/7d910ff2983b81d605a34292275248165571dd47>`_
- gitlab: remove 'username' configuration `060e9da15 <https://github.com/ralphbean/bugwarrior/commit/060e9da15480ba32a0cc6236b114a3815df310c2>`_
- removed requirements, fixed typo `62520981d <https://github.com/ralphbean/bugwarrior/commit/62520981d1bb25b06eb1326ba0179722b8d9fde9>`_
- gitlab: verify SSL certs `52473d6e5 <https://github.com/ralphbean/bugwarrior/commit/52473d6e55adbed613624fc38a54f2e627e4ed3b>`_
- Merge pull request #194 from mathstuf/gitlab-username `b5275da70 <https://github.com/ralphbean/bugwarrior/commit/b5275da70a0c3b82ac5e9c366a6cd355181e4157>`_
- Merge pull request #195 from mathstuf/gitlab-verify-ssl `0e5fd2ff8 <https://github.com/ralphbean/bugwarrior/commit/0e5fd2ff80891748b9d4163f42c3d96eb1222849>`_
- Merge pull request #187 from fradeve/FDV_fix_jira_docs `35ad25fe3 <https://github.com/ralphbean/bugwarrior/commit/35ad25fe35d73ded52280bcf9c6c262d220d7ad2>`_
- Merge pull request #193 from mathstuf/empty-targets `d170615d3 <https://github.com/ralphbean/bugwarrior/commit/d170615d3b26e3e488e0dd36e9e66a3d80e5709c>`_
- targets: ignore notifications section as well `49d95f9eb <https://github.com/ralphbean/bugwarrior/commit/49d95f9eb68a60567811660bf20642aa56d2eda0>`_
- db: fix missing argument `4c7e84e1b <https://github.com/ralphbean/bugwarrior/commit/4c7e84e1bdf79e43cb8402085edb3c8c3d7cc20e>`_
- Merge pull request #196 from mathstuf/ignore-notifications `2ce32161c <https://github.com/ralphbean/bugwarrior/commit/2ce32161cb197ec24386dcb4a1a61281506cca64>`_
- Merge pull request #197 from mathstuf/fix-missing-argument `0e9d0c6a5 <https://github.com/ralphbean/bugwarrior/commit/0e9d0c6a5cba177762073fd7dde8d5c22799222d>`_
- github: add support for OAuth2 authentication `7f96476ca <https://github.com/ralphbean/bugwarrior/commit/7f96476ca72ff84c3ec8650f508b30eea5d9d5f4>`_
- bitbucket: allow filtering repos `74b9ded52 <https://github.com/ralphbean/bugwarrior/commit/74b9ded52ff325cda990d7972a30c29d6610e4b0>`_
- bitbucket: fix url logic `4a327ab3f <https://github.com/ralphbean/bugwarrior/commit/4a327ab3f9eb1697b55e3aae25300a09f505b6fb>`_
- bitbucket: support fetching pull requests `970e20bf7 <https://github.com/ralphbean/bugwarrior/commit/970e20bf75d73a59739ed78615456a6417f022fa>`_
- bitbucket: prefer https `8725635b0 <https://github.com/ralphbean/bugwarrior/commit/8725635b09aefc81b749f5ba4064b99bea384d36>`_
- Merge pull request #199 from mathstuf/github-oauth `3e02be4e3 <https://github.com/ralphbean/bugwarrior/commit/3e02be4e349be14782133182edaf998b8e36da12>`_
- Merge pull request #200 from mathstuf/bitbucket-filter-repo `408421ec2 <https://github.com/ralphbean/bugwarrior/commit/408421ec2c520481bf09c3e3cdb73f12eb549032>`_
- Defer importing services until they are needed. `63d1a8365 <https://github.com/ralphbean/bugwarrior/commit/63d1a8365c50519842c90eb7ecfbb26b95722cc8>`_
- Add some tests for importability. `c07481093 <https://github.com/ralphbean/bugwarrior/commit/c074810932bce68fc1cb98d0df430f61b8c68c9b>`_
- Merge pull request #203 from ralphbean/feature/dynamic-services `09105b029 <https://github.com/ralphbean/bugwarrior/commit/09105b029f503ae2f71c22539c7bd4c2648596a0>`_
- (trac) Fix misquote of "@" character. `bc1d0421b <https://github.com/ralphbean/bugwarrior/commit/bc1d0421b9d6623f9a18ff28077e005d85d3c358>`_
- (trac) support both xmlrpc and the other way. `0365275fd <https://github.com/ralphbean/bugwarrior/commit/0365275fdb437568b563000484ebb9e72018154d>`_
- It's a shame that twiggy doesn't handle encodings gracefully.  Bad choice of a logging lib, @ralphbean. `e3442f517 <https://github.com/ralphbean/bugwarrior/commit/e3442f517cd27679f0caa981915f842557a2808d>`_
- Add uuid for debuggery. `671be26a1 <https://github.com/ralphbean/bugwarrior/commit/671be26a110c4d86c83421ee3cdea5204eded71a>`_

1.0.2
-----

- Fix dep typo. `bd53a4c73 <https://github.com/ralphbean/bugwarrior/commit/bd53a4c738f52cd5b85bbdfff77112db99712610>`_

1.0.1
-----

- Elaborate on github.username and github.login. `06dfee567 <https://github.com/ralphbean/bugwarrior/commit/06dfee567e05b625be8dc9014df00b4b914e0e9e>`_
- This definitely requires taskw.  Fixes 146. `7cf09804b <https://github.com/ralphbean/bugwarrior/commit/7cf09804b43cc16d2bb77dc7419afafb41e9937b>`_
- Setup logging before we check the config. `bce65c0c8 <https://github.com/ralphbean/bugwarrior/commit/bce65c0c806cff9b9c88eed08fd7e8591c23ebb9>`_
- Reorganize the way docs are shipped.. `027f05c63 <https://github.com/ralphbean/bugwarrior/commit/027f05c6349c29ccb0ec06d51a7dd8641e04be7b>`_

1.0.0
-----

- Clock how long each target takes. `4a580b722 <https://github.com/ralphbean/bugwarrior/commit/4a580b722f7d5c9b8970071de038ab50a840c625>`_
- Pull requests should honour include and exclude filters too `129fd40c3 <https://github.com/ralphbean/bugwarrior/commit/129fd40c340f729ebf5ad88ec8c4bb59c9138d84>`_
- Off by one `b67cdccf2 <https://github.com/ralphbean/bugwarrior/commit/b67cdccf2d97cab94bc2ca5af5839215da064b24>`_
- style(github): cleanup `fb3dbb422 <https://github.com/ralphbean/bugwarrior/commit/fb3dbb422616c3af4be83a7d096824fe8e189b5e>`_
- Merge pull request #91 from do3cc/repo_filter_for_prs `ab1a44354 <https://github.com/ralphbean/bugwarrior/commit/ab1a4435498aa478b3b2f4db39f8af29cace144d>`_
- Significant bugwarrior refactor. `182c0ddcd <https://github.com/ralphbean/bugwarrior/commit/182c0ddcd4fc630a242d5cb0d1fc122f3b2ce1a9>`_
- Testing and cleanup of bugwarrior refactor. `cde5c2e4d <https://github.com/ralphbean/bugwarrior/commit/cde5c2e4d07d8d89abbd29a055c397446e514911>`_
- Adding tests. `09685d671 <https://github.com/ralphbean/bugwarrior/commit/09685d6714764e10fff1ed4808ce9b68ab119462>`_
- Re-adding URL shortening via Bit.ly. `179a4c4f5 <https://github.com/ralphbean/bugwarrior/commit/179a4c4f5f8397043374400fcc2fab2af0ce72c7>`_
- Fixing two PEP-8 failures. `2a2f4f858 <https://github.com/ralphbean/bugwarrior/commit/2a2f4f858613e6098976dc408d99b6978e46aa50>`_
- Updating a slightly out-of-date line in the readme. `5d6af8f18 <https://github.com/ralphbean/bugwarrior/commit/5d6af8f18a4cff14f5e547ad11e22c3e5ed1b972>`_
- Don't declare tasks different if the user has modified the priority locally. `0596653b7 <https://github.com/ralphbean/bugwarrior/commit/0596653b7d3706544a6879ce1021d295c96092ab>`_
- Careful for the default locale here... \ó/ `bbf5e29b2 <https://github.com/ralphbean/bugwarrior/commit/bbf5e29b27ad5c49cc20ee8cec3a5939a1b6a381>`_
- Strip links when doing legacy comparisons. `e29f5c612 <https://github.com/ralphbean/bugwarrior/commit/e29f5c612006a936084db1f47e8eb6d617528cab>`_
- Pass along details of the MultipleMatches exception. `b64169bd9 <https://github.com/ralphbean/bugwarrior/commit/b64169bd954843d4a7f532f6acd1ecae0acc2bfb>`_
- Proceed along happily if taskwarrior shellout fails at something. `595b77850 <https://github.com/ralphbean/bugwarrior/commit/595b7785052eba5dec734c8c4d7426f069800ffc>`_
- Misc fixes to the bugzilla service. `48eb4c4ed <https://github.com/ralphbean/bugwarrior/commit/48eb4c4ed8f4767a2eefd140b8341ff74b64c577>`_
- Misc fixes to the trac service. `fd18dd656 <https://github.com/ralphbean/bugwarrior/commit/fd18dd65698cf26c2cbf8093f061e55a4143bb18>`_
- Bugfix. `44ed534a6 <https://github.com/ralphbean/bugwarrior/commit/44ed534a6cad6796b55dc6c4b23957c5a43f0dc8>`_
- Removing EXPERIMENTAL.rst. `d52327f0c <https://github.com/ralphbean/bugwarrior/commit/d52327f0ca27094cf90eed66c0f21a27bf240363>`_
- Adding a couple clarification docstrings. `6df94a864 <https://github.com/ralphbean/bugwarrior/commit/6df94a8643105f02a6755d4f4196c19c206220f4>`_
- Let's actually explain how this works. `0dfd5cdb0 <https://github.com/ralphbean/bugwarrior/commit/0dfd5cdb0967ee4bfbd80a014f95b3b7bc4e5945>`_
- Adding myself to contributors list. `af6585053 <https://github.com/ralphbean/bugwarrior/commit/af6585053ede20bd62453af973d1c97f5d7f5481>`_
- Converting from str to six.text_type. `b442d9691 <https://github.com/ralphbean/bugwarrior/commit/b442d9691d1ab903364ccc5619dd2ff4d4095e4d>`_
- Fixing error handling such that processing is aborted if there is a single failure. `c96ef590e <https://github.com/ralphbean/bugwarrior/commit/c96ef590e398756bd21ad51319bc70db3247200b>`_
- Improve logging during task-db manipulation. `eb53716b0 <https://github.com/ralphbean/bugwarrior/commit/eb53716b03898aa8774597cc209e8188dfddb5ca>`_
- Improve bitbucket error message. `8059b11a4 <https://github.com/ralphbean/bugwarrior/commit/8059b11a4602791a989ae64095cafc66fc9ddfd7>`_
- Typofix. `57462968b <https://github.com/ralphbean/bugwarrior/commit/57462968b8d5ad0cd5f2c22d5ee0122da91037db>`_
- Check specifically for pending and waiting tasks. `324de2944 <https://github.com/ralphbean/bugwarrior/commit/324de2944a41868e3ae5cc157510b92a241a11f0>`_
- Only remove existing uuids if they are found. `2b09d2f35 <https://github.com/ralphbean/bugwarrior/commit/2b09d2f357835e3a89591768a532f2fccb9796fc>`_
- Log a little more here. `371622be1 <https://github.com/ralphbean/bugwarrior/commit/371622be1c6b69c148ddd524700b1e1b10cfc589>`_
- Update UDAS documentation to properly describe the data structure in use. `23882caf3 <https://github.com/ralphbean/bugwarrior/commit/23882caf3228d0158724b061499b703236211076>`_
- Change service-defined UDAs message to not imply necessity. `cf78e6884 <https://github.com/ralphbean/bugwarrior/commit/cf78e6884683f9ea9b9998c44994295b88ea7d16>`_
- Confining myself to 80 chars. `c5408d938 <https://github.com/ralphbean/bugwarrior/commit/c5408d938f85e1fc665cc0cb5b83c461a09e21c7>`_
- Restrict description matches during check for managed tasks to tasks that are not completed; move managed task gathering into a separate function. `a1c17a6a2 <https://github.com/ralphbean/bugwarrior/commit/a1c17a6a29f9336cc70c18f1b159f19c5e85bb59>`_
- Read config file in as unicode to allow one to specify tags containing non-ascii characters. `2b2b6823c <https://github.com/ralphbean/bugwarrior/commit/2b2b6823c5720b6639dce38de59512e2dafb88fc>`_
- Adding option allowing one to specify tags that will be automaically added to all incoming issues of this type. `7e78f7506 <https://github.com/ralphbean/bugwarrior/commit/7e78f7506183770fda9bfb54ed75d97db9b871fe>`_
- Updating and fixing documentation. `79b322036 <https://github.com/ralphbean/bugwarrior/commit/79b322036574ba016b4db61037317b5010f3e1d6>`_
- Adding option allowing one to import github labels as tags. `1f2cbf8f6 <https://github.com/ralphbean/bugwarrior/commit/1f2cbf8f699f2feb30bc80810daa8654f83fc6ce>`_
- Merge pull request #93 from coddingtonbear/refactor_bugwarrior `8d0dd7ac1 <https://github.com/ralphbean/bugwarrior/commit/8d0dd7ac19aa463514a079a3e8a7596412893d28>`_
- Merge pull request #94 from coddingtonbear/add_tags_option `64e6b26fe <https://github.com/ralphbean/bugwarrior/commit/64e6b26fea2fe03d64b74245f7c8e4cff472fc2e>`_
- Merge pull request #95 from coddingtonbear/add_github_labels `b83864c22 <https://github.com/ralphbean/bugwarrior/commit/b83864c228cb670789410faff1c10a43ce132433>`_
- Avoid false positive in tasks_differ. `3b5be9a72 <https://github.com/ralphbean/bugwarrior/commit/3b5be9a727733d00d496f519051a078484ea7ba3>`_
- Include just the description here. `e03fe0b23 <https://github.com/ralphbean/bugwarrior/commit/e03fe0b236f12438ba89f83a823517af6f317583>`_
- Support multiple UNIQUE_KEYs per service. `fdfecbf86 <https://github.com/ralphbean/bugwarrior/commit/fdfecbf8634e4e26ab73fb99a0b97ef33635fce2>`_
- Use the TYPE as a second unique key for github issues. `cccbe7da3 <https://github.com/ralphbean/bugwarrior/commit/cccbe7da3265d76e6a59a62498f9cc9fee560f9e>`_
- Stop duplicating github pull requests. `3abdc9d2a <https://github.com/ralphbean/bugwarrior/commit/3abdc9d2af3f3fc92f61607d8e594104df899070>`_
- Break out and fix "merge_annotations" `466cfa2df <https://github.com/ralphbean/bugwarrior/commit/466cfa2df4d03dfd3af303679fb42f488680ba0f>`_
- Initial refactoring of ActiveCollab3 integration `dc18c30b9 <https://github.com/ralphbean/bugwarrior/commit/dc18c30b9d6b4b7f1c6eadab8610e0d7fe8e1891>`_
- Rename ActiveCollab3 to ActiveCollab `143f68513 <https://github.com/ralphbean/bugwarrior/commit/143f685138b71bc718abed715cad1dd6a6960b52>`_
- Resolve merge `ee02377df <https://github.com/ralphbean/bugwarrior/commit/ee02377dfb7865b8d971597922a0fd3b8ff4621c>`_
- More search and replace `0bb531388 <https://github.com/ralphbean/bugwarrior/commit/0bb531388f79df963735c562fb98993651e1e395>`_
- Clean up due dates, permalinks, misc `aabb28e3c <https://github.com/ralphbean/bugwarrior/commit/aabb28e3c7fc3c81bb96fbd4a593a2e8cc8a6dfb>`_
- Store the parent task id for subtasks `8590e4a82 <https://github.com/ralphbean/bugwarrior/commit/8590e4a82d6816708486740836a492e91f50fa1a>`_
- Merge pull request #96 from kostajh/refactor_bugwarrior_ac3 `833f7c5c4 <https://github.com/ralphbean/bugwarrior/commit/833f7c5c4863a1433ff7a64fb29ca4eb2ffb4e0b>`_
- Start up a new hacking doc. `9a2b8da28 <https://github.com/ralphbean/bugwarrior/commit/9a2b8da28cad39ca9625c0f3e76320f930f7f52d>`_
- Ignore eggs. `0784be364 <https://github.com/ralphbean/bugwarrior/commit/0784be3645cff99db4709de84b0ca43b7c2f56f4>`_
- Add a phabricator service. `74072bda2 <https://github.com/ralphbean/bugwarrior/commit/74072bda24f1fe4ae6055e34ff80ab2417d8c22e>`_
- Initial work on adding a pre_import hook `4a1304a43 <https://github.com/ralphbean/bugwarrior/commit/4a1304a4342c5e0afc173ffa33f23d9eedfa1840>`_
- Merge pull request #99 from kostajh/hooks `17f4f5ff1 <https://github.com/ralphbean/bugwarrior/commit/17f4f5ff1019fdf9eafe028acdef6fb0c5deca6f>`_
- Use FOREIGN_ID for task matching instead of PERMALINK `3ec1e206e <https://github.com/ralphbean/bugwarrior/commit/3ec1e206edfe9af6049f0e266d21fe6de00dbfbd>`_
- Initial work on Travis CI `a5e6f4224 <https://github.com/ralphbean/bugwarrior/commit/a5e6f4224850c8824fb7a2d8c40d063830449edd>`_
- Remove IRC for now `4fa9a503d <https://github.com/ralphbean/bugwarrior/commit/4fa9a503d3470d0d6399b77eed07cebbd78ec9eb>`_
- Install some modules `a1736bf04 <https://github.com/ralphbean/bugwarrior/commit/a1736bf04333c616acb9d82caffae13e07d07469>`_
- Fix jira-python reference `85710f6ea <https://github.com/ralphbean/bugwarrior/commit/85710f6eaae65eb0fa0c43cf64fcf5b133a78cfe>`_
- Merge pull request #101 from kostajh/develop `102fb6073 <https://github.com/ralphbean/bugwarrior/commit/102fb60735d618c06967dc242aa1dc4141208cf1>`_
- Merge pull request #102 from kostajh/travis `dd785d39f <https://github.com/ralphbean/bugwarrior/commit/dd785d39f43b8aea56c768de2d6d550d8e0bccde>`_
- Only use this identifier. `8812b94bb <https://github.com/ralphbean/bugwarrior/commit/8812b94bb0ede6f9b7d35071182f1f3698f2ba86>`_
- Add irc notifications to travis config. `c0073bf62 <https://github.com/ralphbean/bugwarrior/commit/c0073bf62b78c70f556186f74670b84a6e064da5>`_
- Fix failing test for activecollab `41cc4580a <https://github.com/ralphbean/bugwarrior/commit/41cc4580a010a98c6fdfeddcd59fcde31be121ec>`_
- Merge branch 'develop' of https://github.com/ralphbean/bugwarrior into activecollab-test `878a5af3c <https://github.com/ralphbean/bugwarrior/commit/878a5af3c35f6fd0f48315a70d6517a9508f98db>`_
- Merge pull request #103 from kostajh/activecollab-test `ee2b4e2f3 <https://github.com/ralphbean/bugwarrior/commit/ee2b4e2f3840f3716d7b29931b63e502bc05668c>`_
- Fix identification of matching tasks by UDA. `f01159934 <https://github.com/ralphbean/bugwarrior/commit/f011599349f1634714a6b877e3fc5ffacf6c14ff>`_
- PEP-8/style fixes. `307069f5c <https://github.com/ralphbean/bugwarrior/commit/307069f5c619ef514ecfd6ec8363e8d97d660d7f>`_
- Merge pull request #104 from coddingtonbear/fix_local_uuid_matching_keys `968b02747 <https://github.com/ralphbean/bugwarrior/commit/968b027474122746ef9648df7ebb9a5e62c01c65>`_
- Merge pull request #105 from coddingtonbear/fix_pep8_errors `9eb3f6d10 <https://github.com/ralphbean/bugwarrior/commit/9eb3f6d10c77275f5106251bf800f1f1dc56242b>`_
- Gather a couple of additional fields from github while we're up there. `13db46fae <https://github.com/ralphbean/bugwarrior/commit/13db46fae37a698fc5a982bd073dbfa00b1482c7>`_
- Merge pull request #106 from coddingtonbear/github_description `496f881e9 <https://github.com/ralphbean/bugwarrior/commit/496f881e97b9ebd17323ae43e690487f3f92416e>`_
- Handle JIRA priority slightly more gracefully. `277a8850a <https://github.com/ralphbean/bugwarrior/commit/277a8850a3656b170799116aaea241b2f18041d2>`_
- Merge pull request #108 from coddingtonbear/handle_jira_priority_more_gracefully `3008ce157 <https://github.com/ralphbean/bugwarrior/commit/3008ce157b059102ffc19df58606382c7c1123f1>`_
- Adding JIRA's 'description' field to stored task data. `715a7dfc0 <https://github.com/ralphbean/bugwarrior/commit/715a7dfc0726f5e34de78307bebab4ba39b67fa4>`_
- Fixing ability to pull-in annotations; updating readme. `1be6dc037 <https://github.com/ralphbean/bugwarrior/commit/1be6dc03750c80c79f09df00fd72ad5b7330b851>`_
- Merge pull request #109 from coddingtonbear/jira_enhancements `0aa464a50 <https://github.com/ralphbean/bugwarrior/commit/0aa464a5033acaf2b07038277787640f0498cfe3>`_
- Use the pyac library for calling ActiveCollab. Tests need work. `3eda81dc2 <https://github.com/ralphbean/bugwarrior/commit/3eda81dc2eeda46a101cdeb21b9bc43041bf16bb>`_
- Convert body text to markdown `db3f6dff7 <https://github.com/ralphbean/bugwarrior/commit/db3f6dff72345c0a6c760ab6e0e670e5301be22d>`_
- Pull comments from tasks in as annotations. (work in progress) `875bc4ab1 <https://github.com/ralphbean/bugwarrior/commit/875bc4ab1c26852e612b02c07cbc30cd6dcd032d>`_
- Implement get_annotations(). Try to fix tests. `cd95e1da4 <https://github.com/ralphbean/bugwarrior/commit/cd95e1da46c72bb7da66b581afb8274287cb11e0>`_
- Install required python modules `4c2aafea9 <https://github.com/ralphbean/bugwarrior/commit/4c2aafea969e637fab1c38f66c3ab7271da1decf>`_
- Fix test case for pypandoc conversion. Pass annotations to TW for test. `129037c88 <https://github.com/ralphbean/bugwarrior/commit/129037c88b2944780a7178d0ce88c2a14eea0381>`_
- PEP8 `79488f4a8 <https://github.com/ralphbean/bugwarrior/commit/79488f4a8a4d42572852687e6964cf359b25f002>`_
- Kill off dep information if present. `44421dc93 <https://github.com/ralphbean/bugwarrior/commit/44421dc93d851c59fa4a08923d39951a4140e297>`_
- Move from bitly over to da.gd.  It is free software. `383b55cac <https://github.com/ralphbean/bugwarrior/commit/383b55cac63aa44f0c88e278b29e4ed252067191>`_
- Install pandoc `be94dbb89 <https://github.com/ralphbean/bugwarrior/commit/be94dbb89a6a1f64d5c389525e0bfd04b52570ac>`_
- Update jira python module `5fd48177c <https://github.com/ralphbean/bugwarrior/commit/5fd48177c5ec8989d5a7b0b931a1d9695c600f73>`_
- Install latest stable of taskwarrior `689ed3d01 <https://github.com/ralphbean/bugwarrior/commit/689ed3d01e997b5b56ff539d1a96660360b38e4f>`_
- Install libuuid `a3f650ef3 <https://github.com/ralphbean/bugwarrior/commit/a3f650ef38d3391780f21f21d13705d8b052fbbe>`_
- Wrong packagename, try uuid-dev `697d1a1b0 <https://github.com/ralphbean/bugwarrior/commit/697d1a1b0c524357c0b031dfae112e961d2b8ca6>`_
- cd back to build dir. `daaf5d3bd <https://github.com/ralphbean/bugwarrior/commit/daaf5d3bda2cdc86665befc7625dc05efb84dc36>`_
- Add in the Travis CI status images `be19334e6 <https://github.com/ralphbean/bugwarrior/commit/be19334e65b48802e308daafbf7ba3c2e724ace1>`_
- Hmm, let's fix that table. `d46affcff <https://github.com/ralphbean/bugwarrior/commit/d46affcffec9e0c3aab1dafb02f9206e437539ed>`_
- Try to sanitize strings before logging here.  Twiggy freaks out in some cases. `883b3abbf <https://github.com/ralphbean/bugwarrior/commit/883b3abbfdeb882e35a6b3671d95ba70a4ccfaf3>`_
- Github's API sometimes returns a troublesome dict here. `21a08f09b <https://github.com/ralphbean/bugwarrior/commit/21a08f09b3b17af7c1975ec1e851cba0140c9400>`_
- A little more debugging. `945099b9f <https://github.com/ralphbean/bugwarrior/commit/945099b9f9f0fec04605d1a119066bd1308ed299>`_
- Handle some conversion cases to minimize erroneous "diffs" `89a82ebc0 <https://github.com/ralphbean/bugwarrior/commit/89a82ebc0cb075b782504b4b3f1028c49f5b9b4c>`_
- Sometimes, also, this is None. `15f678ea0 <https://github.com/ralphbean/bugwarrior/commit/15f678ea019dc8e66ba09c6da62163d562cc1c63>`_
- Fixing various test failures that are all my fault. `f844a1f3a <https://github.com/ralphbean/bugwarrior/commit/f844a1f3a51c5472889589e8ad5a3145b29f3fe7>`_
- Also gather issues directly-assigned to a user, regardless of whether the originating repository is owned by the user. `c62dbc0e2 <https://github.com/ralphbean/bugwarrior/commit/c62dbc0e27f3eafd3b2ed8c210cb5c42d68f0596>`_
- Add a development mode flag. `8187b5776 <https://github.com/ralphbean/bugwarrior/commit/8187b5776cdb3b09bfba317eee772f95073335b1>`_
- Use a PID lockfile to prevent multiple bugwarrior processes from running simultaneously on the same repository.  Fixes #112. `c4de7f030 <https://github.com/ralphbean/bugwarrior/commit/c4de7f030671932a8a2ab461fbc147e3bbc46005>`_
- Updating an inaccurate docstring. `fe54aa088 <https://github.com/ralphbean/bugwarrior/commit/fe54aa088426803116b7ec74a01f75afe557d274>`_
- Merge pull request #116 from coddingtonbear/issue_112 `a9519a8b8 <https://github.com/ralphbean/bugwarrior/commit/a9519a8b8f6e6ff3382aad7300cb218db0d9a5ac>`_
- Merge pull request #115 from coddingtonbear/add_development_mode_flag `7a4dd8d0e <https://github.com/ralphbean/bugwarrior/commit/7a4dd8d0e798f544f27b1914ce3c0bc2fe92f9cd>`_
- Merge pull request #114 from coddingtonbear/gather_directly_assigned_issues `286e92a46 <https://github.com/ralphbean/bugwarrior/commit/286e92a469d4112c624157c35f5649b5054f0b2c>`_
- Merge pull request #113 from coddingtonbear/fix_tests_apr `4d698561a <https://github.com/ralphbean/bugwarrior/commit/4d698561ad4d33acd28b4d87a72522e21119bbfc>`_
- Merge pull request #111 from kostajh/activecollab-enhancements `26d8380e8 <https://github.com/ralphbean/bugwarrior/commit/26d8380e83b254e6cefbac74422ee14120de5f00>`_
- Older versions of lockfile don't support timeout in the context manager.. unfortunately.  :( `9cbf0e5e4 <https://github.com/ralphbean/bugwarrior/commit/9cbf0e5e433971f8d3d4f398b0fbd5c613596ac0>`_
- Make activecollab optional (mostly due to the pandoc dep). `f3166d378 <https://github.com/ralphbean/bugwarrior/commit/f3166d378f4aa9286838dc7ee182084bccad84d5>`_
- Add new UDA handling; use task object journaling instead of checking for changes manually. `71e0bea70 <https://github.com/ralphbean/bugwarrior/commit/71e0bea705f3a1f83234d36fe14ae0cbc3d05392>`_
- Removing now-unncessary function for finding task changes. `f6d64b66b <https://github.com/ralphbean/bugwarrior/commit/f6d64b66bd0c948a6c238fd0de08f38cbc169410>`_
- Always add timezone information to parsed datetimes; allow one to specify a default timezone. `ba2899335 <https://github.com/ralphbean/bugwarrior/commit/ba2899335cd182c759f800ec865a73b9451f218b>`_
- Do not attempt to use task methods for new tasks. `3817537df <https://github.com/ralphbean/bugwarrior/commit/3817537dfe2850571ba7b28340630fff6d0de716>`_
- Make sure that an array exists always. `4f03bb43c <https://github.com/ralphbean/bugwarrior/commit/4f03bb43c87624ca3a418156768e3db7071334f4>`_
- Adding arbitrary timezone information to test datetimes. `595f4544e <https://github.com/ralphbean/bugwarrior/commit/595f4544ecb2ed6ab3264effc8c3ff4ec1a72517>`_
- Adding timezone information to github test. `5e158c9f7 <https://github.com/ralphbean/bugwarrior/commit/5e158c9f76d087af543c627c1c14ea7cbc7c8a18>`_
- Convert incoming annotations to strings. `a3acc1da4 <https://github.com/ralphbean/bugwarrior/commit/a3acc1da4a6cf36acfe70650aa6883f2c2251c1f>`_
- Merge pull request #119 from coddingtonbear/always_timezones_always `a4a745c38 <https://github.com/ralphbean/bugwarrior/commit/a4a745c383ff37c5b61fd240c68ee2eefb4f7ba7>`_
- Merge remote-tracking branch 'upstream/develop' into bugwarrior_marshalling `367801ea5 <https://github.com/ralphbean/bugwarrior/commit/367801ea50502defebb624fa87a046a7de775d69>`_
- Report which fields have changed when updating a task. `8d19b6edc <https://github.com/ralphbean/bugwarrior/commit/8d19b6edcc7c43803014f41d2bfdd9ee322cb5d6>`_
- Github milestones are integers. `525add3bd <https://github.com/ralphbean/bugwarrior/commit/525add3bdc4fc09985cd2ecde1ce09be2e445c1c>`_
- And so it begins. `841698744 <https://github.com/ralphbean/bugwarrior/commit/84169874484c51a00e321647289d8b5b2a57a825>`_
- Create sphinx (read-the-docs compatible) docs for Bugwarrior. `e981cc2cb <https://github.com/ralphbean/bugwarrior/commit/e981cc2cbea5a33586bd80bf5cd46a4390be5299>`_
- Merge pull request #120 from coddingtonbear/hor_em_akhet `8ce1c0227 <https://github.com/ralphbean/bugwarrior/commit/8ce1c0227f0f9a440eeee498786c3dc7713e667f>`_
- Link to rtfd. `61f9070a2 <https://github.com/ralphbean/bugwarrior/commit/61f9070a2b04900536c00c6404875b3d7bac281f>`_
- Link common configuration options explicitly. `0e13c4bed <https://github.com/ralphbean/bugwarrior/commit/0e13c4bede618e9feaaf70ace2e8098a4d3b9707>`_
- Merge pull request #121 from coddingtonbear/make_common_options_explicit `7047c354b <https://github.com/ralphbean/bugwarrior/commit/7047c354baba6e7db3764c6da9e16e6566d23583>`_
- Merge branch 'develop' into bugwarrior_marshalling `2c811b88c <https://github.com/ralphbean/bugwarrior/commit/2c811b88c1131e5c0dea662f24342b464d27f775>`_
- Generalize field templating logic to allow overriding the generated value of any field. `baf15abd9 <https://github.com/ralphbean/bugwarrior/commit/baf15abd9be1a90bbd5f202ba5f58418a51f5cf6>`_
- Updating documentation to link to field templates rather than description templates. `ffad15b9b <https://github.com/ralphbean/bugwarrior/commit/ffad15b9b9507b3b242fe93fd7104041de4fe587>`_
- ActiveCollab Service: Make dates timezone aware, and default to US/Eastern. If users request a change we can add this as a config option `de34d36e9 <https://github.com/ralphbean/bugwarrior/commit/de34d36e9bff968a9e37dbd83d81639542245221>`_
- Merge pull request #124 from kostajh/develop `572faf9fa <https://github.com/ralphbean/bugwarrior/commit/572faf9fa643e99e1eb0ba1acbdd2c64db665378>`_
- Merge pull request #122 from coddingtonbear/generalize_template_handling `259c75ed4 <https://github.com/ralphbean/bugwarrior/commit/259c75ed4b46e1c96963018959a560be3e5622e6>`_
- Add new UDA handling; use task object journaling instead of checking for changes manually. `5ff726337 <https://github.com/ralphbean/bugwarrior/commit/5ff726337340c79ba1dc3ee3c19eb58d7d6fe3e2>`_
- Removing now-unncessary function for finding task changes. `cf2502559 <https://github.com/ralphbean/bugwarrior/commit/cf25025591a755c2ab0ce43421240bb895de0e09>`_
- Do not attempt to use task methods for new tasks. `f7765ef7c <https://github.com/ralphbean/bugwarrior/commit/f7765ef7cc5faac86d3ce2d25daa60d87e14611e>`_
- Make sure that an array exists always. `fbbaa2661 <https://github.com/ralphbean/bugwarrior/commit/fbbaa26610aca2a5e7207cb632b381fe3fb52d3d>`_
- Convert incoming annotations to strings. `82c36e994 <https://github.com/ralphbean/bugwarrior/commit/82c36e9948beb0ac8e1bf268428dd54e7195b0c1>`_
- Report which fields have changed when updating a task. `f8d3b2599 <https://github.com/ralphbean/bugwarrior/commit/f8d3b259927891901a3149392df6475577b8aa04>`_
- Github milestones are integers. `eb2247af7 <https://github.com/ralphbean/bugwarrior/commit/eb2247af71ee62c742a94e897d737c187374a000>`_
- Nope.  That's numeric... `021e59dac <https://github.com/ralphbean/bugwarrior/commit/021e59dac8c15fd9afe8da742b2640df3014dcc2>`_
- Merge pull request #118 from coddingtonbear/bugwarrior_marshalling `92fdb5de1 <https://github.com/ralphbean/bugwarrior/commit/92fdb5de10bb212fbae3e90ead899c4824866ab2>`_
- Allow one to specify tags using templates, too. `62f3f0581 <https://github.com/ralphbean/bugwarrior/commit/62f3f0581f03db9ee343860ea46ac0675770dab9>`_
- Fixes a broken activecollab test. `cc7ed66ac <https://github.com/ralphbean/bugwarrior/commit/cc7ed66ac548d77c0c31e259b9984e2ead128c59>`_
- Merge pull request #127 from coddingtonbear/fix_activecollab_test `d3c4e7d98 <https://github.com/ralphbean/bugwarrior/commit/d3c4e7d986477d981bd3ddc8da0699732d9cd3d0>`_
- Merge pull request #126 from coddingtonbear/tag_templates `12e37342a <https://github.com/ralphbean/bugwarrior/commit/12e37342a2ea3a9ca3a582d6beca39ecf99578b7>`_
- Add a failing test for db.merge_left. `c50fce5b8 <https://github.com/ralphbean/bugwarrior/commit/c50fce5b85ba4424cf162bd6efdef02e99e50bf8>`_
- Static fields. `14dbcff0e <https://github.com/ralphbean/bugwarrior/commit/14dbcff0e2ee4cd439439d9c0cea8c4ab88f7829>`_
- WIP `502f2789a <https://github.com/ralphbean/bugwarrior/commit/502f2789abbc15fd0efa4cb9660f0ae1ef069055>`_
- Update docs and test `e3a4af4c0 <https://github.com/ralphbean/bugwarrior/commit/e3a4af4c012172a32a9755d08aa0a023fcdb433a>`_
- Project ID is a string `b964e4679 <https://github.com/ralphbean/bugwarrior/commit/b964e46799ba0a41a0dab7a14a2b54d84130a30c>`_
- Use six `b5db5d0bb <https://github.com/ralphbean/bugwarrior/commit/b5db5d0bbdc00897de21e58903371ef088e916ff>`_
- Set issue Label as a UDA rather than a task. Remove unnecessary use of six.text_type(). Set created on as a date, not a string. And fix the tests! `96182a4d9 <https://github.com/ralphbean/bugwarrior/commit/96182a4d97d18fec415d09c94b7bdf2fb1766ce0>`_
- Merge pull request #128 from kostajh/activecollab-refactor `1e5489468 <https://github.com/ralphbean/bugwarrior/commit/1e5489468577d37b757e68d648246e0c6cedfdee>`_
- Make pull requests a top priority. `79b7d3194 <https://github.com/ralphbean/bugwarrior/commit/79b7d31942bd7da3018844956d46f118f9c51ef7>`_
- Suppress stderr. `416f52e24 <https://github.com/ralphbean/bugwarrior/commit/416f52e2428956a6b940e65a1e25f2326b209d03>`_
- Make tasktools.org an example for JIRA.  Fixes #107. `9ca33e0a8 <https://github.com/ralphbean/bugwarrior/commit/9ca33e0a8d2b4a037f9ce64e79fad523ae32385a>`_
- fix issue with missing longdesc `458e9b460 <https://github.com/ralphbean/bugwarrior/commit/458e9b460bdd2802677a363161ca67a024951d29>`_
- Merge pull request #133 from mvcisback/longdesc `c235822be <https://github.com/ralphbean/bugwarrior/commit/c235822be52efcaac01c4ad46cf882f2f5e924ce>`_
- optionally ignore cc'd bugs `95fca9595 <https://github.com/ralphbean/bugwarrior/commit/95fca95953289430206f8d1b2f670355510c8696>`_
- Merge pull request #134 from mvcisback/no_cc `c7fdf2b39 <https://github.com/ralphbean/bugwarrior/commit/c7fdf2b398f02c429d7091a78b6e5c84b8042148>`_
- New inline_links option. `de0071048 <https://github.com/ralphbean/bugwarrior/commit/de00710483d4e616eae3ef452763ff23d2c17e7b>`_
- Sleep so we can take it easy on gpg-agent. `a531f3ae5 <https://github.com/ralphbean/bugwarrior/commit/a531f3ae58c44888708476c7543f9c3308d11fc4>`_
- Include a message indicating how many pull requests were found. `1373df691 <https://github.com/ralphbean/bugwarrior/commit/1373df69173dc3190ac211f6675de76f2b96e51d>`_
- Conditionally filter pull requests, too, if github.filter_pull_requests is true. `469d14dfa <https://github.com/ralphbean/bugwarrior/commit/469d14dfaedcfbfb64e62f30a93da113ab9abe1a>`_
- Adding documentation of the 'github.filter_pull_requests' option. `6b5a03b38 <https://github.com/ralphbean/bugwarrior/commit/6b5a03b3817cccf8d1a00bf2fea479c8ac59e24b>`_
- Cleaning up log messages to be slightly more consistent. `cf5489ad2 <https://github.com/ralphbean/bugwarrior/commit/cf5489ad2e043b64f050fb9846ece654cb250571>`_
- Removing unnecessary whitespace. `4ac7b7fbb <https://github.com/ralphbean/bugwarrior/commit/4ac7b7fbb2e41478cc828ccd7c7f3c73a14f8dfc>`_
- Properly link to the 'Common Configuration Options' reference. `d4e320688 <https://github.com/ralphbean/bugwarrior/commit/d4e3206880f1bcb60071ea8d07f3ba6c6cf8e817>`_
- Merge pull request #137 from coddingtonbear/github_filterable_pull_requests `7c72431f1 <https://github.com/ralphbean/bugwarrior/commit/7c72431f10c17d76794728f6aabbcde376a21eff>`_
- Make trac.py url quote the username/password `f52bf411e <https://github.com/ralphbean/bugwarrior/commit/f52bf411ebd3e5aea818c4b982cb48d1844bfc72>`_
- Merge pull request #138 from puiterwijk/feature/complex-passwords `44201a97a <https://github.com/ralphbean/bugwarrior/commit/44201a97ac2f1c3bfd052e76837888eb20aff9ca>`_
- Allow explicit configuration setting for disabling/enabling Issue URL annotations. `f8358a61d <https://github.com/ralphbean/bugwarrior/commit/f8358a61d9b20c8b515791608f58233ecd717e1b>`_
- Fixing JIRA issue gathering. `d2a4dd346 <https://github.com/ralphbean/bugwarrior/commit/d2a4dd34611807fc07dcee569891e3b493f1a20e>`_
- Shortening one of the lines to satisfy Pep8Bot. `7a5a02c75 <https://github.com/ralphbean/bugwarrior/commit/7a5a02c754d3fb3823d03c12112b916aabed1eff>`_
- Merge pull request #139 from coddingtonbear/inline_annotation_links_fix `1410fff72 <https://github.com/ralphbean/bugwarrior/commit/1410fff72972c2c3c0335a5fc90559960f851c22>`_
- Adding functionality allowing one to update extra post-object-creation. `e91636fd4 <https://github.com/ralphbean/bugwarrior/commit/e91636fd4407ab91f7ee0e3b6c7046a84c318cc8>`_
- Only create JiraIssue instance once. `2a9f1b8fa <https://github.com/ralphbean/bugwarrior/commit/2a9f1b8fae6013e914d951854d46c514dedddc09>`_
- Only create ActivecollabIssue instance once. `3ef7e3f5b <https://github.com/ralphbean/bugwarrior/commit/3ef7e3f5b3dfbe7fc65497b76b5aab1d8fc7f210>`_
- Only create BitbucketIssue instance once. `e63745500 <https://github.com/ralphbean/bugwarrior/commit/e63745500d13b8c50064ec37934d60258c9b456b>`_
- Only create BugzillaIssue instance once. `8c572587c <https://github.com/ralphbean/bugwarrior/commit/8c572587cd2dd0716cdb00bf1ef5bef120eda049>`_
- Only create GithubIssue instance once. `2ca1ec0ed <https://github.com/ralphbean/bugwarrior/commit/2ca1ec0edfb533874e1911c397b35aaf47a4e525>`_
- Only create TracIssue instance once. `61ed88f76 <https://github.com/ralphbean/bugwarrior/commit/61ed88f76e2314631f372256ec80d18b72a48e86>`_
- Merge pull request #140 from coddingtonbear/inline_annotation_links_fix_single_create `e6d78175a <https://github.com/ralphbean/bugwarrior/commit/e6d78175a0b6f19c8314e6f8944446e3b90dfb82>`_
- More prominently document these options. `bfdb3975b <https://github.com/ralphbean/bugwarrior/commit/bfdb3975beda26566ab7fe141d7c6446fb2d6908>`_
- Fix incorrect logic. `93fc03fef <https://github.com/ralphbean/bugwarrior/commit/93fc03fefcbeb793bc6df8f6bb3c1c25d99a8ead>`_
- Fix a typo in the github docs `87c10db6a <https://github.com/ralphbean/bugwarrior/commit/87c10db6acd5984398d2e5a04bd767436ba4e9b7>`_
- Merge pull request #142 from lmacken/develop `2bbc92fd8 <https://github.com/ralphbean/bugwarrior/commit/2bbc92fd82ede52170c6bc06365991741e0e1570>`_
- Add a bugwarrior-vault command. `7f1c31798 <https://github.com/ralphbean/bugwarrior/commit/7f1c3179815750b9ec317a0ae4589db3e22d10ce>`_
- Merge pull request #143 from ralphbean/feature/vault `c97e512c6 <https://github.com/ralphbean/bugwarrior/commit/c97e512c6abc93e20b30ec8962f4ee98d0544b91>`_

0.7.0
-----

- Add some hacking instructions for @teranex. `340a5e2ea <https://github.com/ralphbean/bugwarrior/commit/340a5e2ea3bc87ef99f0afa006b5ea898205c1ad>`_
- Add support for include_repos `265683b78 <https://github.com/ralphbean/bugwarrior/commit/265683b780f2831b4181f8b2bf3788fd3cc3d61c>`_
- Merge pull request #88 from pypingou/develop `c7703c4f6 <https://github.com/ralphbean/bugwarrior/commit/c7703c4f6244b7c153b68ef204eb6f1fdce914a6>`_
- Add @oracle:eval:<command> option to get the password from an external command `47d3cf189 <https://github.com/ralphbean/bugwarrior/commit/47d3cf189c339a86f210057fb815d512506a3475>`_
- Merge pull request #89 from puiterwijk/add-oracle-eval `d47f90d78 <https://github.com/ralphbean/bugwarrior/commit/d47f90d78253b8009f76dd9fe65509c88dc248b7>`_
- Use new taskw lingo. `bf1ea4ff1 <https://github.com/ralphbean/bugwarrior/commit/bf1ea4ff1ca557f56e0796cc4dee247caada87fa>`_
- Handle a bunch of contingencies for python-bugzilla>=0.9.0 `ee4df9935 <https://github.com/ralphbean/bugwarrior/commit/ee4df99353e79f2224bab266f8cbd676445f186d>`_
- Conditionalize jira inclusion. `423040cea <https://github.com/ralphbean/bugwarrior/commit/423040ceac540d476eaebf83d308f4cf0376fccd>`_
- Merge pull request #90 from ralphbean/feature/new-taskw `ce574868d <https://github.com/ralphbean/bugwarrior/commit/ce574868df09c16b70da4bc93079bcf9ed4bed84>`_
- Knock out jira-python by default for now. `b4f8112a2 <https://github.com/ralphbean/bugwarrior/commit/b4f8112a282aece5f9a4042cb6dd9fb3107def18>`_

0.6.3
-----

- Another tweak for #85. `b732b4f47 <https://github.com/ralphbean/bugwarrior/commit/b732b4f47616bd9f281a72c91bf8f17b2aaf04b1>`_

0.6.2
-----

- Issue #82: Implement mechanism for asking the user or a keyring for passwords (see: bugwarrior.config:get_service_password()). `ad0c1729d <https://github.com/ralphbean/bugwarrior/commit/ad0c1729d5e6a8d5ff5e2efe08651b8d4fa4e260>`_
- Issue #82 related: Cleanup some debug statements. `7f98990cd <https://github.com/ralphbean/bugwarrior/commit/7f98990cd4fa36c791dda61802ef065785626d56>`_
- Issue #82 related: Some pep8 cleanup. `d915515a1 <https://github.com/ralphbean/bugwarrior/commit/d915515a1459045123b342cd1e197f33eb651a38>`_
- Issue #82 related: Add example description for password lookup strategies. `2cb57e752 <https://github.com/ralphbean/bugwarrior/commit/2cb57e7528d7d336247ebcf68f69cec29c13b6c9>`_
- Merge pull request #83 from jenisys/feature/ask_password `d2a7f6695 <https://github.com/ralphbean/bugwarrior/commit/d2a7f669589e769a814a075f7bb29db4cc2f0772>`_
- Bitbucket with authorization and on requests `1b74cc0a9 <https://github.com/ralphbean/bugwarrior/commit/1b74cc0a9a3c0f9ec8e8e1495bd054c09a983abd>`_
- Bitbucket - password asking logic `c388c6b89 <https://github.com/ralphbean/bugwarrior/commit/c388c6b895051d49a0cd48f5e5bb8e40f7e5b690>`_
- Reformat by pep8 `5b2556247 <https://github.com/ralphbean/bugwarrior/commit/5b2556247ffd288e7e6c313f0827808b45349ff2>`_
- Merge pull request #84 from paulrzcz/develop `f25be82a0 <https://github.com/ralphbean/bugwarrior/commit/f25be82a05bd66318b3c296dda63c7ffc5d30258>`_
- Make bitbucket authn optional. `84a0c51b6 <https://github.com/ralphbean/bugwarrior/commit/84a0c51b68eca7df5f91125298d32c38de121ae7>`_
- Try to support older bugzilla instances. `474e61eb8 <https://github.com/ralphbean/bugwarrior/commit/474e61eb8d2204855f6496b0bfa56f0e1aede3b4>`_
- Update only_if_assigned github logic for #85. `86a0dd6c2 <https://github.com/ralphbean/bugwarrior/commit/86a0dd6c2cbb112c76d1c8c92907ff6ff69d0c79>`_

0.6.1
-----

- Make the jira service version 4 compatible `9d8347655 <https://github.com/ralphbean/bugwarrior/commit/9d83476556737f31e1689d4379ef9c6ddfe36e16>`_
- Fixes for backward compatibility `e144f5b02 <https://github.com/ralphbean/bugwarrior/commit/e144f5b02c3c73b398884154b21779ce0dc29e48>`_
- Make the multiprocessing option really optional. `3eb477c0f <https://github.com/ralphbean/bugwarrior/commit/3eb477c0f7a5e990e66877b32fd52c1ddfe34cda>`_
- Merge pull request #68 from nikolavp/jira4-fixes `9c000d8b7 <https://github.com/ralphbean/bugwarrior/commit/9c000d8b7167c56a6d98231a7f8d66e2b477c13b>`_
- Support filtering by repo for github.  Fixes #72. `5a116e1d2 <https://github.com/ralphbean/bugwarrior/commit/5a116e1d25c5dcf3b6f79fc46de4b37b87557b04>`_
- Use permalink for subtasks if provided `22e639197 <https://github.com/ralphbean/bugwarrior/commit/22e6391972207ef695d3482447b1274a1198a400>`_
- Merge pull request #73 from kostajh/develop `72a851472 <https://github.com/ralphbean/bugwarrior/commit/72a8514725582e2227b9d8f057eb779553ca071b>`_
- Make the annotation and description length configurable. `5dc896661 <https://github.com/ralphbean/bugwarrior/commit/5dc896661a9a4f8f8703ab71eaac3b882b8c43ef>`_
- Set default description and annotation lengths `9f3c5c7dd <https://github.com/ralphbean/bugwarrior/commit/9f3c5c7dde67af2301ff9eb0065bca4f8eacfb5e>`_
- Merge pull request #76 from lmacken/feature/longer `8feb6903f <https://github.com/ralphbean/bugwarrior/commit/8feb6903f33f5b500665309c894ff9ced48fdb57>`_
- Fix ticket inclusion logic for #79. `263da5657 <https://github.com/ralphbean/bugwarrior/commit/263da5657b51edce62d9a823d108236161da8654>`_

0.6.0
-----

- First run at multiprocessing.  Awesome. `59f89be81 <https://github.com/ralphbean/bugwarrior/commit/59f89be81a5bcaffd1989db7b73d713efc4d828c>`_
- Config and logging for multiprocessing. `cf7fbe9a5 <https://github.com/ralphbean/bugwarrior/commit/cf7fbe9a5c8f72dce03ec0af6259cf2421237674>`_
- Misc cleanup. `1a11898d8 <https://github.com/ralphbean/bugwarrior/commit/1a11898d82f728a96b161b0ec580f7f418cf5c23>`_
- Handle worker failure more explicitly. `2a80de244 <https://github.com/ralphbean/bugwarrior/commit/2a80de244d45c7dcd3d3b99e3481b98bf357b85f>`_
- Merge pull request #49 from ralphbean/feature/multiprocessing `3d0c8f456 <https://github.com/ralphbean/bugwarrior/commit/3d0c8f4564ef1485b6f4e70d662fd195e4b4567b>`_
- Can now define prefix to be added to project name of pulled Jira tasks `34400d761 <https://github.com/ralphbean/bugwarrior/commit/34400d761247cb5487a29f72b9125ff4bb204aa2>`_
- First pass at adding ActiveCollab3 service `251a92472 <https://github.com/ralphbean/bugwarrior/commit/251a92472aabeab758445170b7f35c44316986fa>`_
- Add notes to README `5633ca1ad <https://github.com/ralphbean/bugwarrior/commit/5633ca1ad76bf4d31df884d4c1153675e1b4d0a6>`_
- Merge pull request #50 from ubuntudroid/develop `6e08dd36f <https://github.com/ralphbean/bugwarrior/commit/6e08dd36f695055aca69e97bb8bda090bb81d934>`_
- Get the bugzilla service working again after recent API changes (#53) `506de20dc <https://github.com/ralphbean/bugwarrior/commit/506de20dc7500ffa14ceb00640b81944bdfeae91>`_
- Merge pull request #54 from lmacken/develop `eedb0f8a9 <https://github.com/ralphbean/bugwarrior/commit/eedb0f8a99937d4c3201dde2acc36593c0656966>`_
- Remove some debug statements `00b6f788b <https://github.com/ralphbean/bugwarrior/commit/00b6f788bfaf5d2258ea24f23efcafa4326a0eff>`_
- Merge pull request #56 from kostajh/activecollab3 `2e6fabc8d <https://github.com/ralphbean/bugwarrior/commit/2e6fabc8df9d3cc5dabaa98b31ceb6dd941596f8>`_
- Try using dogpile.cache to stop bitly api crises. `afbab3607 <https://github.com/ralphbean/bugwarrior/commit/afbab360793364391f5e988f1fd1728adcaf1f79>`_
- More verbose debugging. `125cbaeac <https://github.com/ralphbean/bugwarrior/commit/125cbaeac5fd8d7ff4ff32d4279b2fed48115a7b>`_
- Merge branch 'develop' into feature/cache-for-bitly `f965e1b45 <https://github.com/ralphbean/bugwarrior/commit/f965e1b45957ca9ddb8d02d38a139cf852004a9e>`_
- Some pep8. `314c16229 <https://github.com/ralphbean/bugwarrior/commit/314c16229a071e0ee257c4155a9aeffcdef0bd00>`_
- Finished pep8 pass. `8326b85c9 <https://github.com/ralphbean/bugwarrior/commit/8326b85c91db031f9df898608efbba76266d9b61>`_
- First pass at adding notifications. `8b258b39e <https://github.com/ralphbean/bugwarrior/commit/8b258b39eb501aff58fe36e9e13ea67eaa267ca6>`_
- Strip illegal(?) characters from message `740e4314d <https://github.com/ralphbean/bugwarrior/commit/740e4314d91a169a9c04cbd68344bf282a25b6ec>`_
- Merge pull request #58 from ralphbean/feature/cache-for-bitly `003438184 <https://github.com/ralphbean/bugwarrior/commit/003438184f51252af886ccaa1644bc322f641bf6>`_
- Merge pull request #57 from ralphbean/feature/pep8 `3700fbec5 <https://github.com/ralphbean/bugwarrior/commit/3700fbec5512616a4d54b989d44f4e2e53cf4670>`_
- Handle empty comments from bz. `f8ef9736c <https://github.com/ralphbean/bugwarrior/commit/f8ef9736c11e185538fe2ad5e40261952110e29c>`_
- Backwards compatibility for bugzilla annotations `1c05d2bff <https://github.com/ralphbean/bugwarrior/commit/1c05d2bff267834a814b28d9f2f1ff414e4cf334>`_
- Refactor, use growlnotify `7a0d0975f <https://github.com/ralphbean/bugwarrior/commit/7a0d0975f84c60e5ddf92c0ccd89e39a171ab411>`_
- Allow for configuring stickiness of notifications `16182e82b <https://github.com/ralphbean/bugwarrior/commit/16182e82b87ae9aefe68cbd8ed277066a8598e0d>`_
- Update readme `8d714dd92 <https://github.com/ralphbean/bugwarrior/commit/8d714dd926893907d966de0166fab3fb38949b84>`_
- Cleanup some unused imports `cc6b0f376 <https://github.com/ralphbean/bugwarrior/commit/cc6b0f376f953a7a5e42186777aa5fdc639f98fc>`_
- Change binary to "backend" `03128dda8 <https://github.com/ralphbean/bugwarrior/commit/03128dda8a66f6decb9ff0f1e0b2509745dc7593>`_
- Merge pull request #59 from kostajh/notifications `953adfe6c <https://github.com/ralphbean/bugwarrior/commit/953adfe6cf38564137cd8d0b8d8e4a1c6d48f1c3>`_
- pynotify notifications for Linux. `4513b0711 <https://github.com/ralphbean/bugwarrior/commit/4513b07117682db00078e64432f59f34b909bdad>`_
- Typofix. `3a37cde64 <https://github.com/ralphbean/bugwarrior/commit/3a37cde64d68679623fa20ce4f1ae3fb026ec167>`_
- Some bugfixes to #59. `2eaa69313 <https://github.com/ralphbean/bugwarrior/commit/2eaa69313cb5151fd07577525c4fe99fc571bf0e>`_
- Added a third "gobject" notification backend. `a7a51ae9c <https://github.com/ralphbean/bugwarrior/commit/a7a51ae9c2349d26d586b19f2ef3f6cbb2851e4c>`_
- Merge pull request #60 from ralphbean/feature/pynotify `f0f9b600f <https://github.com/ralphbean/bugwarrior/commit/f0f9b600fc6af800d923c9c9bbfe6e7dfebecea8>`_
- More notification bugfixes. `47edf0e55 <https://github.com/ralphbean/bugwarrior/commit/47edf0e552668a6621ebbbc23dc0a5867deab6f9>`_
- Mention how to use notifications under cron.  Fixes #61. `febc2128c <https://github.com/ralphbean/bugwarrior/commit/febc2128ce99974f898ef351bfeb1585a94320cb>`_
- Use project slug instead of full name, makes typing project name in TW simpler `83e45a8cd <https://github.com/ralphbean/bugwarrior/commit/83e45a8cd7d454053ab17b5c540e74f09b631dd6>`_
- PEP8. `fb9b7dfc6 <https://github.com/ralphbean/bugwarrior/commit/fb9b7dfc69d5e961cec3a716cb9a66d9a9745ada>`_
- Fixes for AC3 `a720374fb <https://github.com/ralphbean/bugwarrior/commit/a720374fb88ef0240fae6cf16987108cca92fc86>`_
- Merge branch 'develop' into active-collab3-fixes `b677b5970 <https://github.com/ralphbean/bugwarrior/commit/b677b5970f20499a55c9ff1a069afa577beed452>`_
- Merge pull request #65 from kostajh/active-collab3-fixes `306b62344 <https://github.com/ralphbean/bugwarrior/commit/306b6234408569b077ac1de4979fdc7a0abba6c1>`_
- Initial work on task merge approach `897f869b0 <https://github.com/ralphbean/bugwarrior/commit/897f869b0325bdc898fe9e2d27c77080b7dcf13a>`_
- Load correct config before merge `c4f8341b0 <https://github.com/ralphbean/bugwarrior/commit/c4f8341b09337eb1fd18c3ff93d8803e7ad5b8db>`_
- Set project name to project slug `aac7afb9b <https://github.com/ralphbean/bugwarrior/commit/aac7afb9b2f6c04f6a0f4b2759ea168d13f06c4f>`_
- Cleanup `af3599801 <https://github.com/ralphbean/bugwarrior/commit/af35998012a787619e3a1142055228aec0be0fc8>`_
- Merge branch 'develop' into task-merge `069f10c4b <https://github.com/ralphbean/bugwarrior/commit/069f10c4b1e57aff7a84a3a3584abed7674a9ea3>`_
- Ignore annotations for task updates. Call task_done in users primary TW database when completing a task, as task merge wont get them. `56bbdd388 <https://github.com/ralphbean/bugwarrior/commit/56bbdd3881b352ee68d42fce435826057729ca68>`_
- Delete completed tasks from Bugwarrior DB. This allows for assigning/reassigning tasks. `aa111cec9 <https://github.com/ralphbean/bugwarrior/commit/aa111cec94f57467caf377d708ed840b7447c234>`_
- Do not need to load only pending tasks since we are marking BW database tasks as completed at the end of each sync `903a67228 <https://github.com/ralphbean/bugwarrior/commit/903a67228a6deb8776b2020a340ec8ea48f742a1>`_
- Remove pprint `6010caa6b <https://github.com/ralphbean/bugwarrior/commit/6010caa6bceafa0856bdca9c3c8ca0b87ac40cfa>`_
- Remove slashes from project slug `ba6dce557 <https://github.com/ralphbean/bugwarrior/commit/ba6dce5577920f4916336a45fafb9b7d434d7ca6>`_
- Merge branch 'develop' into task-merge `fbb7941ee <https://github.com/ralphbean/bugwarrior/commit/fbb7941eeca2fdb1c071f82aa1fe40ba623c0913>`_
- Merge pull request #66 from kostajh/develop `d011e555f <https://github.com/ralphbean/bugwarrior/commit/d011e555fd6ed116dcf0cd54a352a12b0c24f255>`_
- Merge branch 'task-merge' of git://github.com/kostajh/bugwarrior into task-merge `3a2cd196d <https://github.com/ralphbean/bugwarrior/commit/3a2cd196d54537e1e6a13b5db30b40e44faad6b4>`_
- Crucial. `5d831bec1 <https://github.com/ralphbean/bugwarrior/commit/5d831bec1c7a7c4cfa758fac633472ac861fa6f5>`_
- Be still more careful with the way we load options. `3aa3bce81 <https://github.com/ralphbean/bugwarrior/commit/3aa3bce81bf95ba8d5e832ea925dea31c5876c77>`_
- PEP8 pass. `91e92ad77 <https://github.com/ralphbean/bugwarrior/commit/91e92ad774c2e38023c9eebe0548f292517854d1>`_
- Github supports ticket assignment these days.  Fixes #29. `3950146a0 <https://github.com/ralphbean/bugwarrior/commit/3950146a02e7f6f7d962f3f6d6f635154a8a4f83>`_
- Add notes on using Bugwarrior in experimental mode `b9122a1ca <https://github.com/ralphbean/bugwarrior/commit/b9122a1cafeb306cd74aebc4a89f629bdbb98ea7>`_
- Fix link to taskw `21e115ac1 <https://github.com/ralphbean/bugwarrior/commit/21e115ac1099e4d0e57b3248b4ea488b29d8b570>`_
- Merge pull request #69 from kostajh/develop `72bd6faf2 <https://github.com/ralphbean/bugwarrior/commit/72bd6faf2fb658a0dece620db6d126e2bc29dc83>`_
- Update AUTHORS section of the README re @kostajh. `a300aad8d <https://github.com/ralphbean/bugwarrior/commit/a300aad8db817edaf7b98a5186c7f89d863a09f0>`_
- Be more careful with this header dict. `6287a4235 <https://github.com/ralphbean/bugwarrior/commit/6287a4235247e8945c38d9658e9ac36d3a278917>`_
- Loosen version constraint on python-requests. `0f8b3690c <https://github.com/ralphbean/bugwarrior/commit/0f8b3690c5449ac96b0b3683c1f28a48d9b14506>`_
- Merge pull request #71 from ralphbean/feature/modern-requests `67fadc63d <https://github.com/ralphbean/bugwarrior/commit/67fadc63dec8df603d53f6a90b29eeeff6b78d67>`_

0.5.8
-----

- Typofix in docs. `f725ad5f9 <https://github.com/ralphbean/bugwarrior/commit/f725ad5f912bfbd85a904592b4bcf777f69889d2>`_
- Merge remote-tracking branch 'upstream/develop' into develop `9a21b33a1 <https://github.com/ralphbean/bugwarrior/commit/9a21b33a15b550c22926b3673a856ebf86ad09c3>`_
- First pass at adding priority and due date support for AC service `9e40f56f4 <https://github.com/ralphbean/bugwarrior/commit/9e40f56f41a96a90c578b90330e6f80e2d05ba35>`_
- Fix due dates and priority `3fb653258 <https://github.com/ralphbean/bugwarrior/commit/3fb653258fe2e35590ed818369dfd6b33f8dccdf>`_
- Add debug statements `30496b785 <https://github.com/ralphbean/bugwarrior/commit/30496b7850c98dc731db9447e4862050350139e1>`_
- More debug statements `38b2c832f <https://github.com/ralphbean/bugwarrior/commit/38b2c832f04f626628edeee842d6ab5008467fa7>`_
- Check if priority is set before assinging to issue `7d566463f <https://github.com/ralphbean/bugwarrior/commit/7d566463fd2e598090ea56c94e68a906fdaf92b5>`_
- Add due info only if it is present in the issue `382e8ec29 <https://github.com/ralphbean/bugwarrior/commit/382e8ec2903487471bc086b3c6956153cd1f3fec>`_
- Merge pull request #44 from kostajh/priority-and-due-activecollab `22ce01be1 <https://github.com/ralphbean/bugwarrior/commit/22ce01be1ae6a8830d22ff4a6b2c3553392cf56e>`_
- User defined JQL queries for Jira services `24b996753 <https://github.com/ralphbean/bugwarrior/commit/24b99675391ee82d02307f6c4cf6fdee26796f77>`_
- Support older python-requests.  Relates to #46. `929991954 <https://github.com/ralphbean/bugwarrior/commit/929991954c4662f0984eba781f058b0e152eda61>`_
- Pin requests<=0.14.2.  Fixes #46. `1a71117ce <https://github.com/ralphbean/bugwarrior/commit/1a71117ceb56dc3ba379a0ba947004c83002d79c>`_
- Add default for jira.query `64e18b7fb <https://github.com/ralphbean/bugwarrior/commit/64e18b7fb8dda2f4a57db697fb00c3a1849c2713>`_
- More elegant setting of jira query variable `f4f164e7c <https://github.com/ralphbean/bugwarrior/commit/f4f164e7ccfc160e30ebd881265c773888416814>`_
- Merge pull request #47 from ubuntudroid/develop `df71d745c <https://github.com/ralphbean/bugwarrior/commit/df71d745cdc958db48f95ae993f645f2df1c192a>`_

0.5.7
-----

- Added list of contributors to the bottom of the README. `726a91986 <https://github.com/ralphbean/bugwarrior/commit/726a919863744ca765871ddef5979feb77df97e2>`_
- minor: correction to annotation format `6d5fedad0 <https://github.com/ralphbean/bugwarrior/commit/6d5fedad0667f646040770adb15f66e49caab340>`_
- Merge pull request #37 from tychoish/jira-patch-1 `7e7361aa5 <https://github.com/ralphbean/bugwarrior/commit/7e7361aa5b72369801b536e9f85cb5706af28a98>`_
- Added notes about format for the .isues() method.  #39 `737d2ea82 <https://github.com/ralphbean/bugwarrior/commit/737d2ea82f0e0423c58aefd3aebcff8344345a6e>`_
- First pass at activecollab2 integration `94d5cff9c <https://github.com/ralphbean/bugwarrior/commit/94d5cff9c05cf49d685df2c5f048060da43475a7>`_
- Reformat task description, add code for stripping html `b152c3eba <https://github.com/ralphbean/bugwarrior/commit/b152c3ebae2235b91855e8462415ff7635b73c1a>`_
- Only add permalink as annotation. Comments are not useful. `78ce70cb9 <https://github.com/ralphbean/bugwarrior/commit/78ce70cb958a9a10e2a81ae1dfaf61f04707e037>`_
- Cleanup formatting. `d117667ab <https://github.com/ralphbean/bugwarrior/commit/d117667abbe144450c5ccca5ec19f7697f7f0bf2>`_
- Handle cases where user tasks data isnt returned `18494dc1e <https://github.com/ralphbean/bugwarrior/commit/18494dc1ebabacff75eff893123de993d3900680>`_
- Log task count for debugging `ae0396b8c <https://github.com/ralphbean/bugwarrior/commit/ae0396b8ceef891a73ecaa752699471c5c712454>`_
- Debug formatting. `5e2a34716 <https://github.com/ralphbean/bugwarrior/commit/5e2a34716afd9ab20586b2093ecc5d349ca7d58b>`_
- Add notes to README `06b8d0cad <https://github.com/ralphbean/bugwarrior/commit/06b8d0cadf8f92caa3124852b3532a68b877a7c8>`_
- Add more info on configuring service `0ac46e26b <https://github.com/ralphbean/bugwarrior/commit/0ac46e26bc908af0f81c10993770c552a9122a7b>`_
- Add notes on API usage, minor code cleanup `a041bc16f <https://github.com/ralphbean/bugwarrior/commit/a041bc16f0e3348816d9c1f13d00f33e01fd12b4>`_
- Add note about api compatibility `925a638b1 <https://github.com/ralphbean/bugwarrior/commit/925a638b10de9a24a203b462915e13ca46c06e73>`_
- Merge pull request #41 from kostajh/active-collab `1175c4dc3 <https://github.com/ralphbean/bugwarrior/commit/1175c4dc3f74de7a4a34fd8765ff08cbdd6bbe0c>`_

0.5.6
-----

- support for jira to complete #32 `4d2e6bf53 <https://github.com/ralphbean/bugwarrior/commit/4d2e6bf530b08cc6fd1995f2fbe54a41223a2b7e>`_
- minor: tweak query `d61083c38 <https://github.com/ralphbean/bugwarrior/commit/d61083c382bff2566ad9fe8e4e6788c0d0fa32fb>`_
- jira: correcting link and tightening display `a390609e3 <https://github.com/ralphbean/bugwarrior/commit/a390609e366bb64f3a21e25f13b066e6695da069>`_
- jira: adding docs and example config information to readme `5d3e70a3b <https://github.com/ralphbean/bugwarrior/commit/5d3e70a3bd5ea17715128382d63ed31c67d88f1f>`_
- Merge pull request #36 from tychoish/jira-service `e51bed803 <https://github.com/ralphbean/bugwarrior/commit/e51bed80357866875fc15759adedb3d2b40f8752>`_
- README tweaks. `364883c17 <https://github.com/ralphbean/bugwarrior/commit/364883c174290df7678c41bae8398f5cd9a73129>`_

0.5.5
-----

- Support for TeamLab `c81999adc <https://github.com/ralphbean/bugwarrior/commit/c81999adceb279572c0146f908b7beff3329a4fd>`_
- Support for RedMine `39aeb8b09 <https://github.com/ralphbean/bugwarrior/commit/39aeb8b098c7785b919d34d5cac64f76b70c0858>`_
- Merge pull request #34 from umonkey/develop `fe1915c85 <https://github.com/ralphbean/bugwarrior/commit/fe1915c85dcd7b2e81fa32a2b5986c91c5b6914c>`_
- Death to pygithub3. `18fc9c59e <https://github.com/ralphbean/bugwarrior/commit/18fc9c59ec2243616a14d2ecdff537310ca2655c>`_
- Protect against bitbucket repos that have no issues.  For #35 `c7b739956 <https://github.com/ralphbean/bugwarrior/commit/c7b73995641ccc7424a53140ff656501614d9193>`_
- Bugzilla comments as annotations.  Fixes #27. `5126b6a99 <https://github.com/ralphbean/bugwarrior/commit/5126b6a9904f3657515eecb952876ad1ebbed9fb>`_

0.5.4
-----

- Support for megaplan.ru `392b8c9a6 <https://github.com/ralphbean/bugwarrior/commit/392b8c9a6f202cff37b3ff463f019cf26cd14052>`_
- Support for Unicode in issue descriptions `125564ece <https://github.com/ralphbean/bugwarrior/commit/125564ece3e648d0cae0332d57a17ee71938ec41>`_
- Updated README.rst to include megaplan support `01fe88a7c <https://github.com/ralphbean/bugwarrior/commit/01fe88a7c4c56fe86bb6525a8a458d9be34c48ad>`_
- Re-import deleted tasks `15e568a84 <https://github.com/ralphbean/bugwarrior/commit/15e568a842aa156274205a4829859cb34ce9838b>`_
- Fixed bad links to megaplan issue pages `4117bd8ca <https://github.com/ralphbean/bugwarrior/commit/4117bd8ca1c254395a41877cfcbd30b05d72bdb1>`_
- Merge pull request #33 from umonkey/develop `c35f5a2c9 <https://github.com/ralphbean/bugwarrior/commit/c35f5a2c96aae019baa62ce97113c0e504179815>`_
