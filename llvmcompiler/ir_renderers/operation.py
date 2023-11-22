from __future__ import annotations
from typing import TYPE_CHECKING, Self
from enum import Enum
from typing import List, Tuple, Union
from llvmlite import ir



import llvmcompiler.compiler_types as ct
from llvmcompiler.compiler_types.types.char import C8PointerType
if TYPE_CHECKING:
    from .builder_data import BuilderData
from llvmcompiler.ir_renderers.variable import Variable, Value, HeapValue


arg_type = Self | Variable | ct.CompilerType | Value | Tuple[str, Variable]

class Operation:
    """
    All operations inherit from this operation
    """
    def __init__(self, arguments:list[arg_type] = []) -> None:
        self.builder:BuilderData = None
        self.raw_arguments = arguments
        self.arguments = arguments

    def get_variables(self, arguments: list[arg_type] = [], no_default_action = False):
        if len(arguments) == 0 and not no_default_action:
            arguments = self.arguments
        new_args = [*arguments]
        for a_n, a in enumerate(arguments):
            if isinstance(a, str):
                new_args[a_n] = self.get_variable(a)
            else:
                new_args[a_n].builder = self.builder
        
        return new_args

    def get_variable(self, var_name:str):
        return self.builder.get_variable(var_name)

    def set_arguments_parent(self):
        for a_n in range(len(self.arguments)):
            self.arguments[a_n].parent = self.builder.function
            self.arguments[a_n].module = self.builder.module

    def process_arg(self, arg:arg_type):
        if isinstance(arg, str):
            arg = self.builder.get_variable(arg)
            arg.parent = self.builder.function
            arg.module = self.builder.module
        if isinstance(arg, Variable):
            arg.parent = self.builder.function
            arg.module = self.builder.module
            if not arg.heap and not arg.function_argument:
                return arg.load()
            else:
                return arg.variable
        elif isinstance(arg, Value):
            arg.parent = self.builder.function
            arg.module = self.builder.module
            return arg.get_value()
        else:
            return arg
        
    def process_lhs_rhs_args(self):
        #process arg1
        arg1 = self.process_arg(self.arguments[0])
        
        #process arg2
        arg2 = self.process_arg(self.arguments[1])

        return arg1, arg2
    
    def write_argument(self, raw_arg: arg_type):
        if isinstance(raw_arg, Operation):
            value = self.builder.function.create_operation(raw_arg).write()
            value.parent = self.builder.function
            value.module = self.builder.function.module
            value.builder = self.builder
            return value
        elif isinstance(raw_arg, Value):
            raw_arg.parent = self.builder.function
            raw_arg.module = self.builder.module
            raw_arg.builder = self.builder
            if isinstance(raw_arg, HeapValue):
                raw_arg.render_heap()
            return raw_arg
        else:
            return raw_arg

    def write_arguments(self):
        """
        This function processes the arguments of the operation and runs any operation arguments.
        """

        # process the arguments and run any operation arguments
        for r_a_n, raw_arg in enumerate(self.raw_arguments):
            self.arguments[r_a_n] = self.write_argument(raw_arg)

        

    def _write(self) -> Value | Variable:
        """
        This should be overridden to in inheriting class.
        This function is what is called to write the ir for the operation
        """
        

    def write(self):
        self.write_arguments()
        return self._write()

    def __repr__(self) -> str:
        return f"({self.__class__.__name__} : {{arguments: {self.arguments}}})"

        

        

def dbg_llvm_print(builder:BuilderData, var):
    srcstr = "%i\n\00"
    string = builder.alloca(ir.ArrayType(ir.IntType(8), len(srcstr)))
    builder.cursor.store(ir.Constant(ir.ArrayType(ir.IntType(8), len(srcstr)), bytearray(srcstr.encode("utf8"))), string)
    builder.cursor.call(builder.functions["print"].get_function().function, [builder.cursor.bitcast(string, C8PointerType().value), var])