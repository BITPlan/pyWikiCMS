"""
Created on 2022-12-03

@author: wf
"""
import frontend


class Version(object):
    """
    Version handling for pyWikiCMS
    """

    name = "pyWikiCMS"
    description = "pyWikiCMS: python implementation of a Mediawiki based Content Management System"
    version = frontend.__version__
    date = "2022-11-16"
    updated = "2023-11-05"
    authors = "Wolfgang Fahl"
    doc_url = "http://wiki.bitplan.com/index.php/PyWikiCMS"
    chat_url = "https://github.com/BITPlan/pyWikiCMS/discussions"
    cm_url = "https://github.com/BITPlan/pyWikiCMS"
    license = f"""Copyright 2022-2023 contributors. All rights reserved.
  Licensed under the Apache License 2.0
  http://www.apache.org/licenses/LICENSE-2.0
  Distributed on an "AS IS" basis without warranties
  or conditions of any kind, either express or implied."""
    longDescription = f"""{name} version {version}
{description}
  Created by {authors} on {date} last updated {updated}"""
