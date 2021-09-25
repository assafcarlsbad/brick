from ..base_module import BaseModule

from bip.base import *
from bip.hexrays import *


from ..smi_nested_pointers.smi import CommBufferSmiHandler
from ...utils import bip_utils

class SmramOverlapModule(BaseModule):
    '''
    Scans for SMI handlers that don't properly validate the size of the communication buffer.
    Malicious actors can place the communication buffer just below the SMRAM range,
    such that any attempt to write to the communication buffer will result in overwriting SMRAM.
    '''

    def __init__(self) -> None:
        super().__init__()

    @staticmethod
    def _checks_comm_buff_size(handler: BipFunction):

        def deref_comm_buffer_size(node):
            # Does the node correspond to a dereference operation on CommBufferSize? (i.e. *CommBufferSize)
            deref = node.ops[0].ignore_cast
            return isinstance(deref, CNodeExprVar) and (deref.lvar_name == 'CommBufferSize')

        return bip_utils.collect_cnode_filterlist(handler.hxcfunc, deref_comm_buffer_size, [CNodeExprPtr])

    def run(self):
        for handler in CommBufferSmiHandler.iter_all():
            if not self._checks_comm_buff_size(handler):
                self.res = False
                self.logger.error(f'SMI {handler.name} does not check the size of the comm buffer, check for potential overlap with SMRAM')

        if self.res:
            self.logger.success('No SMI that omits checking CommBufferSize was found')