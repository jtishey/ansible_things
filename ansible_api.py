#!/usr/bin/env python

import json
from collections import namedtuple
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
from ansible.inventory.manager import InventoryManager
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.plugins.callback import CallbackBase
from ansible.module_utils._text import to_bytes
from ansible.parsing.vault import VaultSecret

class ResultCallback(CallbackBase):
    """A sample callback plugin used for performing an action as results come in

    If you want to collect all results into a single object for processing at
    the end of the execution, look into utilizing the ``json`` callback plugin
    or writing your own custom callback plugin
    """
    def v2_runner_on_ok(self, result, **kwargs):
        """Print a json representation of the result
        This method could store the result in an instance attribute for retrieval later
        """
        host = result._host
        print(json.dumps({host.name: result._result}, indent=4))

Options = namedtuple('Options', ['connection', 'module_path', 'forks', 'become', 'become_method', 'become_user', 'check', 'diff'])
# initialize nev2_runner_on_okeded objects
loader = DataLoader()
loader.set_vault_secrets([('default',VaultSecret(_bytes=to_bytes('password')))])
options = Options(connection='local', module_path='/path/to/mymodules', forks=100, become=None, become_method=None, become_user=None, check=False,
                  diff=False)
passwords = dict(vault_pass='password')

# Instantiate our ResultCallback for handling results as they come in
results_callback = ResultCallback()

# create inventory and pass to var manager
inventory = InventoryManager(loader=loader, sources=['/etc/ansible/hosts'])
variable_manager = VariableManager(loader=loader, inventory=inventory)

# create play with tasks
play_source =  dict(
        name = "Python Test",
        hosts = 'cisco-ios',
        gather_facts = 'no',
        tasks = [{'name': 'OBTAIN LOGIN CREDENTIALS',
                    'include_vars': 'vault-vars.yml'},
                 {'name': 'DEFINE PROVIDER',
                    'set_fact': {'provider': {'username': '{{ ROOT_USER }}',
                                              'host': '{{ inventory_hostname }}',
                                              'password': '{{ ROOT_PASSWORD }}'}}},
                {'name': 'BACKUP RUNNING CONFIG',
                    'ios_config': {
                        'authorize': True,
                        'backup': True,
                        'provider': '{{ provider }}'
                }}]
    )

play = Play().load(play_source, variable_manager=variable_manager, loader=loader)

# actually run it
tqm = None
try:
    tqm = TaskQueueManager(
              inventory=inventory,
              variable_manager=variable_manager,
              loader=loader,
              options=options,
              passwords=passwords,
              stdout_callback=results_callback,  # Use our custom callback instead of the ``default`` callback plugin
          )
    result = tqm.run(play)
finally:
    if tqm is not None:
        tqm.cleanup()