# Copyright 2018 EPAM Systems, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# [http://www.apache.org/licenses/LICENSE-2.0]
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
from setuptools import find_packages, setup

version = {}

default_entry_point_name = 'modular-cli'
entry_point_name = os.environ.get('MODULAR_CLI_ENTRY_POINT')
if not entry_point_name:
    entry_point_name = default_entry_point_name

with open("version.py") as fp:
    exec(fp.read(), version)

setup(
    name=entry_point_name,
    version=version['__version__'],
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'click==7.1.2',
        'tabulate==0.9.0',
        'PyYAML==6.0.1',
        'requests==2.32.0',
        'prettytable==3.9.0'
    ],
    entry_points=f'''
        [console_scripts]
        {entry_point_name}=modular_cli.modular_cli:modular_cli
    ''',
    data_files=[
        ('modular_cli',
         ['modular_cli/modular_cli_autocomplete/bash_modular_cli_complete.sh',
          'modular_cli/modular_cli_autocomplete/zsh_modular_cli_complete.sh',
          'modular_cli/modular_cli_autocomplete/modular_cli_autocomplete.py']
         ),
    ]
)
