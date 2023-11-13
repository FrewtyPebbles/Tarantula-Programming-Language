from __future__ import annotations

from llvmlite import ir

import llvmcompiler.compiler_types as ct
from typing import TYPE_CHECKING, Union
if TYPE_CHECKING:
    from .builder_data import BuilderData
    import llvmcompiler.ir_renderers.function as fn
import llvmcompiler.ir_renderers.builder_data as bd

class Variable:
    def __init__(self, builder:BuilderData, name:str, value:Value, heap = False, function_argument = False):
        self.builder = builder
        self.name = name
        self.value = value
        self.value.parent = self.builder.function
        self.heap = heap # wether a variable is stored on the heap or not
        self.function_argument = function_argument # wether or not the variable represents a function argument
        self.type = self.value.type.cast_ptr() if self.heap else self.value.type

        # declare the variable
        if not self.function_argument:
            if self.heap:
                malloc_call = self.builder.cursor.call(self.builder.functions["allocate"].get_function().function, [bd.SIZE_T(self.value.type.size)])

                bc = self.builder.cursor.bitcast(malloc_call, self.type.value)

                self.variable = self.builder.cursor.gep(bc, [ir.IntType(32)(0)], inbounds=True, name = self.name)
                
            else:
                self.variable = self.builder.alloca(self.type.value, name = self.name)
        else:
            self.variable = self.value.value

        self.builder.declare_variable(self)

        if not self.function_argument:
            if self.value.value != None:
                self.set(self.value)
        
            
    def set(self, value:Union[Variable, Value, any]):
        self.builder.set_variable(self, value)

    def load(self):
        return self.builder.cursor.load(self.variable)
    
    def __repr__(self) -> str:
        return f"(Variable:[name:\"{self.name}\"|value:{self.value}])"
    
    @property
    def is_pointer(self):
        return self.type.value.is_pointer
    
class Value:
    def __init__(self, value_type:ct.CompilerType, raw_value:Union[str, any] = None, is_instruction = False, heap = False) -> None:
        self._builder:BuilderData = None
        self.type = value_type
        self.value = raw_value
        self.is_instruction = is_instruction
        self.heap = heap
        self._parent:fn.Function = None

    @property
    def parent(self):
        self.type.parent = self._parent
        self.type.render_template()
        return self._parent
    
    @parent.setter
    def parent(self, par):
        self._parent = par
        self.type.parent = par
        self.type.render_template()

    @property
    def builder(self):
        return self._builder

    @builder.setter
    def builder(self, value:BuilderData):
        self._builder = value
        self.type.parent = self._builder.function
        self.type.render_template()
        

    def get_value(self):
        if isinstance(self.type, ct.ArrayType):
            if isinstance(self.type.type.get_template_type(), ct.C8Type) if \
            isinstance(self.type.type, ct.Template) else \
            isinstance(self.type.type, ct.C8Type):
                return ir.Constant(self.type.value, bytearray(self.value.encode()))
            
        return self.type.value(self.value)
    
    def write(self) -> ir.AllocaInstr:
        self.type.render_template()
        if isinstance(self.value, ir.Instruction):
            return self.value
        else:
            const = self.get_value()
            ret_val = self.builder.alloca(const.type)
            self.builder.cursor.store(const, ret_val)
            return ret_val
    
    def to_ptr(self) -> ir.PointerType:
        ptr = self.type.value.as_pointer()(self.value)#self.builder.cursor.inttoptr(self.get_value(), self.type.value)
        return ptr
    
    def dbg_print(self):
        print(self.type.value)

    def __repr__(self) -> str:
        return f"(Value:[type:\"{self.type.value}\"|value:{self.value}])"

    @property
    def is_pointer(self):
        return self.type.value.is_pointer
    

class InstructionValue(Value):
    def __init__(self, value_type: ct.CompilerType, raw_value: str = None, is_instruction=False, heap=False) -> None:
        super().__init__(value_type, raw_value, is_instruction, heap)
        
    def get_value(self):
        self.value
