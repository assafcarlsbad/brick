from functools import cached_property
from typing import Iterable
from guids.guids_db import GuidsDatabase
from .efiXplorer_plugin import EfiXplorerPlugin
from pathlib import Path

from ..base_module import BaseModule
from ...utils import brick_utils
from ...utils.function_matcher import FunctionMatcher

from bip.base import *
from bip.hexrays import *

class EfiXplorerModule(BaseModule):
    '''
    Analyzes the input binary using the efiXplorer plugin for IDA Pro.
    Then, formats and propagates the results while trying to avoid some common false-positives.
    '''

    EFI_SMM_RUNTIME_SERVICES_TABLE_GUID = GuidsDatabase().name2guid['SmmRsTableGuid']

    def __init__(self) -> None:
        super().__init__()
        self.known_false_positives = set()
        self.res_dir = Path(__file__).parent / 'res'

    @cached_property
    def smi_handlers(self):
        return BipFunction.get_by_prefix(EfiXplorerPlugin.SW_SMI_PREFIX) + \
               BipFunction.get_by_prefix(EfiXplorerPlugin.CB_SMI_PREFIX)

    @staticmethod
    def format_path(addresses: Iterable):
        path = ''
        for address in addresses[:-1]:
            path += BipFunction(address).name
            path += '->'
        path += hex(addresses[-1])
        return path

    def match_known_false_positives(self):
        '''
        Initializes a database of functions that are known for generating false positives in efiXplorer.
        '''

        # See https://github.com/tianocore/edk2/blob/master/MdePkg/Library/SmmMemoryAllocationLib/MemoryAllocationLib.c
        FreePool_matcher = FunctionMatcher('FreePool', is_library=True)
        if FreePool_func := FreePool_matcher.match_by_diaphora(self.res_dir / 'SmmMemoryAllocationLib.sqlite', 0.8):
            self.known_false_positives.add(FreePool_func.ea)

    def handle_smm_callouts(self, callouts):
        self.match_known_false_positives()

        if brick_utils.search_guid(self.EFI_SMM_RUNTIME_SERVICES_TABLE_GUID):
            self.logger.info('''Module references EFI_SMM_RUNTIME_SERVICES_TABLE_GUID,
the following call-outs are likely to be false positives''')

        for callout in callouts:
            if BipFunction(callout).ea in self.known_false_positives:
                # We hit a known false-positive, skip that.
                continue

            for handler in self.smi_handlers:
                for path in brick_utils.get_paths(handler, callout):
                    self.logger.verbose(self.format_path(path))
        
    def handle_vulnerabilities(self, vulns):
        for vuln_type in vulns:
            addresses = [ea for ea in vulns[vuln_type]]
            if vuln_type == 'smm_callout':
                self.handle_smm_callouts(addresses)
            else:
                # In JSON all integers must be written in decimal radix. Convert them to hex for enhanched readability.
                hex_addresses = [hex(ea) for ea in addresses]
                self.logger.error(f'{vuln_type} occuring at {hex_addresses}')

    def run(self):
        efiXplorer = EfiXplorerPlugin(self.input_file, self.is_64bit)
        efiXplorer.run(EfiXplorerPlugin.Args.DISABLE_UI)

        vulns = efiXplorer.get_results().get('vulns')
        if vulns:
            self.handle_vulnerabilities(vulns)
        else:
            self.logger.success("efiXplorer didn't detect any vulnerabilities")