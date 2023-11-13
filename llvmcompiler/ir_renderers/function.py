from __future__ import annotations
from typing import Dict, List, Union, TYPE_CHECKING
from llvmlite import ir
import llvmcompiler.ir_renderers.builder_data as bd
from llvmcompiler.ir_renderers.operations import Operation
from llvmcompiler.ir_renderers.scopes.forloop import ForLoop
import llvmcompiler.ir_renderers.scopes as scps

import llvmcompiler.ir_renderers.variable as var
from llvmcompiler.modules.module import Module

if TYPE_CHECKING:
    from llvmcompiler.modules.module import Module
import llvmcompiler.compiler_types as ct



class FunctionDefinition:
    def __init__(self, name:str, arguments:Dict[str, ct.CompilerType],
            return_type:ct.CompilerType, variable_arguments:bool = False, template_args:list[str] = [],
            scope:list[scps.Scope | Operation] = [], struct:ct.Struct = None, module:Module = None, extern = False):
        self.name = name
        self.arguments = arguments
        self.return_type = return_type
        self.variable_arguments = variable_arguments
        self.scope = scope
        self.template_args = template_args
        self.struct = struct
        self.module = module
        self.extern = extern
        """
        This marks a function for external use for things like dlls.
        Just like extern "c" in c++.
        """

        self.function_aliases:dict[str, Function] = {}
        """
        This dict contains the mangled aliases.
        Use `get_function` to retrieve/write and retrieve functions from/to this variable
        """

    def get_function(self, template_types:list[ct.CompilerType] = []):
        mangled_name = self.get_mangled_name(template_types)
        if mangled_name in self.function_aliases.keys():
            return self.function_aliases[mangled_name]
        else:
            # make a new function that is potentially a template
            new_function = self.write(template_types)
            self.function_aliases[new_function.name] = new_function
            return new_function

    def write(self, template_types:list[ct.CompilerType] = []) -> Function:
        new_function = Function(template_types, self)
        return new_function.write()

    def get_template_index(self, name:str):
        return self.template_args.index(name)    

    def get_mangled_name(self, template_types:list[ct.CompilerType] = []):
        mangled_name = f"{self.name}"
        if len(template_types) == 0:
            return mangled_name
        
        mangled_name += f"_tmp_{self.module.mangle_salt}_{f'_{self.module.mangle_salt}_'.join([tt.value._to_string() for tt in template_types])}"
        return mangled_name
    
class CFunctionDefinition(FunctionDefinition):
    def __init__(self, ir_function:ir.Function):
        self.ir_function = ir_function
        self.name = self.ir_function.name
    
    def get_function(self, template_types:list[ct.CompilerType] = []):
        return CFunction(self)
    


class Function:
    def __init__(self, template_types:list[ct.CompilerType], function_definition:FunctionDefinition) -> None:
        self.template_types = template_types
        self.is_template_function = len(self.template_types) > 0
        self.function_definition = function_definition
        self.module = function_definition.module
        self.name = self.function_definition.get_mangled_name(template_types)
        "Name is mangled."

        self.variables:Dict[str, var.Variable] = [{}]
        "This is all variables within the function scope."

        self.arguments = {**self.function_definition.arguments}
        for key in self.arguments.keys():
            self.arguments[key].parent = self
            self.arguments[key].render_template()
                


    def get_template_type(self, name:str):
        typ = self.template_types[self.function_definition.get_template_index(name)]
        if isinstance(typ, ct.Template):
            typ = typ.get_template_type()
        return typ

    def write(self) -> Function:

        func_args, func_ret = self.get_function_template_signature()

        self.function_type = ir.FunctionType(func_ret.value, [stype.value for stype in func_args.values()], var_arg=self.function_definition.variable_arguments)
        
        self.function = ir.Function(self.module.module, self.function_type, self.name)
        
        # name the function arguments
        for arg_num, arg in enumerate(func_args.keys()):
            self.function.args[arg_num].name = arg
        
        # get a ir cursor for writing ir to different things in the function
        self.entry = self.function.append_basic_block("entry")
        self.builder = bd.BuilderData(self, ir.IRBuilder(self.entry), self.variables)
        self.builder.declare_arguments()
        # This cursor needs to be passed to any ir building classes that are used
        # within this function.

        self.get_variable = self.builder.get_variable


        # write the scope
        self.write_scope()
        
        return self

    def get_function_template_signature(self):
        func_args = {**self.function_definition.arguments}
        for key, val in self.function_definition.arguments.items():
            if isinstance(val, ct.Template):
                # replace function argument templates with template types
                val.parent = self
                func_args[key] = val

        func_ret = self.function_definition.return_type
        if isinstance(self.function_definition.return_type, ct.Template):
            self.function_definition.return_type.parent = self
            self.function_definition.return_type.render_template()
            func_ret = self.function_definition.return_type
        
        return func_args, func_ret

    def write_scope(self):
        last_scope_line = None
        for scope_line in self.function_definition.scope:
            scope_line.builder = self.builder

            if any([isinstance(last_scope_line, iftype1) for iftype1 in [scps.IfBlock, scps.ElseIfBlock]])\
            and any([isinstance(scope_line, iftype2) for iftype2 in [scps.ElseIfBlock, scps.ElseBlock]]):
                scope_line.prev_if = last_scope_line
            elif any([isinstance(last_scope_line, iftype1) for iftype1 in [scps.IfBlock, scps.ElseIfBlock, scps.ElseBlock]])\
            and not any([isinstance(scope_line, iftype2) for iftype2 in [scps.ElseIfBlock, scps.ElseBlock]]):
                last_scope_line.render()

            scope_line.write()
            last_scope_line = scope_line
            self.module.dbg_print()


    def create_operation(self, operation:Operation):
        operation.builder = self.builder
        return operation
    
        
class CFunction(Function):
    def __init__(self, function_definition:FunctionDefinition):
        self.function_definition = function_definition
        self.function = self.function_definition.ir_function
        self.name = self.function_definition.name


