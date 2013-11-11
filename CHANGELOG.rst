Changelog
=========

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
