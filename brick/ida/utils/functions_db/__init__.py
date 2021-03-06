from abc import abstractstaticmethod
from bip.base import *

class FunctionMatcher:
    '''
    Recognizes functions in a binary using several different tools and techniques.
    '''
    
    def __init__(self, name, is_library=False, decompiler_required=False):
        self.name = name
        self.is_library = is_library
        self.decompiler_required = decompiler_required

    def _do_match(self, f: BipFunction):
        '''
        Called when a match is detected.
        '''

        if f is not None:
            f.name = self.name
            f.is_lib = self.is_library

        return f

    @abstractstaticmethod
    def heuristic(f: BipFunction):
        pass

    def match(self):
        '''
        Recognizes a function using a caller provided heuristic function.
        '''

        # Short path, use function name as hint.
        func = BipFunction.get_by_name(self.name)
        if func and self.heuristic(func):
            return self._do_match(func)

        # Long path, perform exhaustive search.
        for func in BipFunction.iter_all():

            if self.decompiler_required and not func.can_decompile:
                # The heuristic function relies on the decompiler but for some reason decompilation failed.
                continue

            if self.heuristic(func):
                return self._do_match(func)

