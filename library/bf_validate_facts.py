#!/usr/bin/python
#   Copyright 2019 The Batfish Open Source Project
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

# Note: these docs take into account the fact that the plugin handles supplying default values for some params
DOCUMENTATION = '''
---
module: bf_validate_facts
short_description: Validates facts for the current Batfish snapshot against the facts in the supplied directory 
version_added: "2.7"
description:
    - "Validates facts for the current Batfish snapshot against the facts in the C(expected_facts) directory"
options:
    nodes:
        description:
            - Nodes to extract facts for. See U(https://github.com/batfish/batfish/blob/master/questions/Parameters.md#node-specifier) for more details on node specifiers.
        required: false
    network:
        description:
            - Name of the network to validate facts for. This defaults to the value in the bf_network fact.  
        required: false
    snapshot:
        description:
            - Name of the snapshot to validate facts for. This defaults to the value in the bf_snapshot fact.  
        required: false
    session:
        description:
            - Batfish session parameters required to connect to the Batfish service. This defaults to the value in C(bf_session) fact.
        required: false
    expected_facts:
        description:
            - Directory to pull expected facts from.
        required: false
author:
    - Spencer Fraint (`@sfraint <https://github.com/sfraint>`_)
requirements:
    - "pybatfish"
'''

EXAMPLES = '''
# Validate current snapshot facts against local YAML facts
- bf_validate_facts:
    expected_facts: /path/to/local/YAML/files/
# Validate current snapshot facts for nodes whose names contain as1border against local YAML facts
- bf_validate_facts:
    nodes: /as1border/
    expected_facts: /path/to/local/YAML/files/
'''

RETURN = '''
summary:
    description: Summary of action(s) performed.
    type: str
result:
    description: Contains a map of node-name to list of failures for that node.
    returned: when validation does not pass
    type: complex
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.bf_util import (assert_dict_subset, create_session,
                                          get_facts, load_facts, set_snapshot,
                                          validate_facts)

try:
    from pybatfish.client.session import Session
except Exception as e:
    pybatfish_found = False
else:
    pybatfish_found = True

def run_module():
    # define the available arguments/parameters that a user can pass to
    # the module
    module_args = dict(
        nodes=dict(type='str', required=False, default='.*'),
        network=dict(type='str', required=True),
        snapshot=dict(type='str', required=True),
        expected_facts=dict(type='str', required=True),
        session=dict(type='dict', required=True),
        debug=dict(type='bool', required=False, default=False),
    )

    # seed the result dict in the object
    # we primarily care about changed and state
    # change is if this module effectively modified the target
    # state will include any data that you want your module to pass back
    # for consumption, for example, in a subsequent task
    result = dict(
        changed=False,
        result='',
        summary='',
    )

    # the AnsibleModule object will be our abstraction working with Ansible
    # this includes instantiation, a couple of common attr would be the
    # args/params passed to the execution, as well as if the module
    # supports check mode
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    if not pybatfish_found:
        module.fail_json(msg='Python module Pybatfish is required')

    if module.check_mode:
        return result

    nodes_spec = module.params['nodes']
    input_directory = module.params['expected_facts']
    session_params = module.params.get('session', {})
    network = module.params.get('network')
    snapshot = module.params.get('snapshot')

    session = create_session(**session_params)
    set_snapshot(session=session, network=network, snapshot=snapshot)

    actual = get_facts(session, nodes_specifier=nodes_spec)
    expected = load_facts(input_directory)
    failures = validate_facts(expected, actual)

    summary = 'Actual facts match expected facts'
    if failures:
        summary = ('Validation failed for the following nodes: {}. See task ' +
                   'output for more details.').format(list(failures.keys()))

    # Overall status of command execution
    result['summary'] = summary
    result['result'] = failures
    # Add warning that shows up in Ansible in the case of failed assert(s)
    if failures:
        result['warnings'] = [summary]

    module.exit_json(**result)

def main():
    run_module()

if __name__ == '__main__':
    main()