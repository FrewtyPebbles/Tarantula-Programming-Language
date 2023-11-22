from llvmcompiler.compiler_types import CompilerType, I64Type
from ..operation import Operation
from llvmlite import ir
import llvmcompiler.ir_renderers.variable as vari

class TypeSizeOperation(Operation):
    """
    Returns the size of a type as an llvm ir constant
    """
    def _write(self):
        self.builder.cursor.comment("OP::dereference START")
        self.arguments = self.get_variables()
        self.set_arguments_parent()
        
        res = 0
        #process arg1
        if isinstance(self.arguments[0], vari.Variable):
            res = self.arguments[0].type.size
        elif isinstance(self.arguments[0], vari.Value):
            res = self.arguments[0].type.size
        elif isinstance(self.arguments[0], CompilerType):
            res = self.arguments[0].size
        
        self.builder.cursor.comment("OP::dereference END")

        return vari.Value(I64Type(), ir.IntType(64)(res), True)