'''
File: alist.py
Description: Alist class and functions


'''

from copy import deepcopy
import json


class Alist:
    def __init__(self, **kwargs):
        self.attributes = {
            Attributes.ID: kwargs[Attributes.ID] if Attributes.ID in kwargs else "0",
            Attributes.OP: kwargs[Attributes.OP] if Attributes.OP in kwargs else 'value',
            Attributes.SUBJECT: kwargs[Attributes.SUBJECT] if Attributes.SUBJECT in kwargs else '',
            Attributes.PROPERTY: kwargs[Attributes.PROPERTY] if Attributes.PROPERTY in kwargs else '',
            Attributes.OBJECT: kwargs[Attributes.OBJECT] if Attributes.OBJECT in kwargs else '',
            Attributes.OPVAR: kwargs[Attributes.OPVAR] if Attributes.OPVAR in kwargs else '',
            Attributes.COV: kwargs[Attributes.COV] if Attributes.COV in kwargs else 0.0,
            Attributes.TIME: kwargs[Attributes.TIME] if Attributes.TIME in kwargs else '',
            Attributes.EXPLAIN: kwargs[Attributes.EXPLAIN] if Attributes.EXPLAIN in kwargs else '',
            Attributes.FNPLOT: kwargs[Attributes.FNPLOT] if Attributes.FNPLOT in kwargs else '',
            Attributes.CONTEXT: kwargs[Attributes.CONTEXT] if Attributes.CONTEXT in kwargs else '',
            'meta': {
                'cost': kwargs[Attributes.COST] if Attributes.COST in kwargs else 0.0,
                'depth': 0,
                'state': States.UNEXPLORED,
                'data_sources': [],
                'branch_type': Branching.OR,
                'node_type': NodeTypes.ZNODE,
                'is_map' : 1,
                'is_frontier' : 0
            }
        }

        for k in set(kwargs) - {Attributes.OP, Attributes.SUBJECT, Attributes.PROPERTY, Attributes.OBJECT,
                                Attributes.OPVAR, Attributes.COV, Attributes.TIME, Attributes.EXPLAIN,
                                Attributes.FNPLOT, Attributes.CONTEXT}:
            self.attributes[k] = kwargs[k]
        self.children = []
        self.parent = []
        # these are for set comprehension operations when a node spawns new nodes after reducing
        self.nodes_to_enqueue_only = []
        self.nodes_to_enqueue_and_process = []
        self.parent_decomposition = ''

    @property
    def id(self):
        return self.attributes[Attributes.ID]

    @id.setter
    def id(self, value):
        self.attributes[Attributes.ID] = value

    @property
    def cost(self):
        return self.attributes['meta']['cost']

    @cost.setter
    def cost(self, value):
        self.attributes['meta']['cost'] = value

    @property
    def depth(self):
        return self.attributes['meta']['depth']

    @depth.setter
    def depth(self, value):
        self.attributes['meta']['depth'] = value

    @property
    def state(self):
        return self.attributes['meta']['state']

    @state.setter
    def state(self, value):
        self.attributes['meta']['state'] = value

    @property
    def data_sources(self):
        return self.attributes['meta']['data_sources']

    @data_sources.setter
    def data_sources(self, value):
        self.attributes['meta']['data_sources'] = value

    @property
    def branch_type(self):
        return self.attributes['meta']['branch_type']

    @branch_type.setter
    def branch_type(self, value):
        self.attributes['meta']['branch_type'] = value

    @property
    def node_type(self):
        return self.attributes['meta']['node_type']

    @node_type.setter
    def node_type(self, value):
        self.attributes['meta']['node_type'] = value

    @property
    def is_map(self):
        return self.attributes['meta']['is_map']

    @is_map.setter
    def is_map(self, value):
        self.attributes['meta']['is_map'] = value

    @property
    def is_frontier(self):
        return self.attributes['meta']['is_frontier']

    @is_map.setter
    def is_frontier(self, value):
        self.attributes['meta']['is_frontier'] = value

    def set(self, attribute, value):
        """
        Sets the value of an attribute. 
        Do not use this for instantiating a variable.
        """
        if isinstance(attribute, str):
            self.attributes[attribute] = value
        if attribute == Attributes.ID:
            self.id = value

    def get(self, attribute):
        """ 
        Returns the value assigned to the attribute, 
        not necessarily its instantiated value
        """
        if attribute in self.attributes:
            return self.attributes[attribute]
        else:
            return None

    def getOpVar(self):
        v = self.attributes[Attributes.OPVAR]
        try:
            v = json.loads(v) # if there list of vars
        except:
            pass
        if isinstance(v, list) == False:
            v = [v]
        v = [x for x in v if str(x).startswith((VarPrefix.AUXILLIARY, VarPrefix.NESTING, VarPrefix.PROJECTION))]
        return v

    def check_variables(self):
        # ensure all variables are attribute keys too
        variables = self.variable_names()
        for v in variables:
            if v not in list(self.attributes.keys()):
                self.set(v, '')

        proj_vars = self.projection_variables()
        op_vars = self.getOpVar()
        if not proj_vars and len(op_vars) > 1:
            #create a default projection variable
            def_proj_var = self.__default_projection_variable()
            self.set(def_proj_var,'')
        
        elif not proj_vars and len(op_vars) == 1:
            #create a default projection variable and assign to value of opvar
            def_proj_var = self.__default_projection_variable()
            self.set(def_proj_var, op_vars[0])

        if Attributes.OPVALUE not in self.attributes:
            self.set(Attributes.OPVALUE, '')
        
    def __default_projection_variable(self):
        return f"{Attributes.PRJVAR}"

    def has_default_projection_variable(self):
        def_proj_var = self.__default_projection_variable()
        return def_proj_var in self.attributes


    def copy(self, same_state=False, exclude_attr=[]):
        """ create a copy of the Alist"""
        new_alist_attrs = deepcopy(self.attributes)
        for excl in exclude_attr:
            del new_alist_attrs[excl]
        # remove default projection variable
        if self.__default_projection_variable() in new_alist_attrs:
            del new_alist_attrs[self.__default_projection_variable()]
        new_alist = Alist(**new_alist_attrs)
        new_alist.id = "0"
        new_alist.cost = 0
        new_alist.depth = 0
        new_alist.state = self.state if same_state else States.UNEXPLORED
        new_alist.nodes_to_enqueue_only = []
        new_alist.nodes_to_enqueue_and_process = []
        
        new_alist.data_sources = deepcopy(self.data_sources)
        return new_alist

    def get_alist_json_with_metadata(self):
        Alist = deepcopy(self.attributes)
        Alist[Attributes.ID] = self.id
        return Alist

    def is_instantiated(self, attr_name):
        """ 
        Returns FALSE if the value of the attribute is a variable
        or an empty string.
        """
        if attr_name in self.attributes and (len(str(self.attributes[attr_name]).strip()) > 0) and \
             not str(self.attributes[attr_name]).startswith((VarPrefix.AUXILLIARY, VarPrefix.NESTING, VarPrefix.PROJECTION)) and \
             isinstance(self.attributes[attr_name], str):
            return True
        elif attr_name not in self.attributes or not self.attributes[attr_name]:
            return False
        else:
            if attr_name in [Attributes.SUBJECT, Attributes.OBJECT, Attributes.PROPERTY, Attributes.TIME] or \
                str(self.attributes[attr_name]).startswith((VarPrefix.AUXILLIARY, VarPrefix.NESTING, VarPrefix.PROJECTION)):
                return self.is_instantiated(self.attributes[attr_name])
            elif isinstance(self.attributes[attr_name], dict):
                return False
            else:
                return True

    def is_all_instantiated(self):
        """ 
        Returns TRUE if all variables are instantiated.
        """
        result = True
        variable_names = self.variable_names()
        for v in variable_names:
            result = result and self.is_instantiated(v)
        return result


    def variables(self):
        """ Returns a list of all variables in the Alist"""
        variables = {x: y for (x, y) in self.attributes.items()
                     if str(x).startswith((VarPrefix.AUXILLIARY, VarPrefix.NESTING, VarPrefix.PROJECTION)) or
                     str(y).startswith((VarPrefix.AUXILLIARY,
                                        VarPrefix.NESTING, VarPrefix.PROJECTION))
                     }
        return variables

    def variable_names(self):
        """ Returns a list of all variables in the Alist"""
        variables = [x for x in list(self.attributes.keys()) + list(self.attributes.values())
                     if str(x).startswith((VarPrefix.AUXILLIARY, VarPrefix.NESTING, VarPrefix.PROJECTION))]
        return list(set(variables))
    

    def instantiated_attributes(self):
        """ Returns a dictionary of variables and their instantiations"""
        variables = {x: y for (x, y) in self.attributes.items()
                     if self.is_instantiated(x)}
        return variables

    def uninstantiated_attributes(self):
        variables = set(self.variables())
        inst_variables = set(self.instantiated_attributes())
        return {x:self.get(x) for  x in list(variables - inst_variables)}

    def instantiation_value(self, attrName):
        """
        Get the value that the attribute is instantiated with.
        For an attribute whose values is a variables, 
        find the value that the variable is instantiated to.
        """
        if attrName not in self.attributes or isinstance(self.attributes[attrName], dict):
            return None
        if str(self.attributes[attrName]).startswith((VarPrefix.AUXILLIARY, VarPrefix.NESTING, VarPrefix.PROJECTION)):
            return self.instantiation_value(self.attributes[attrName])
        else:
            return self.attributes[attrName]

    def projected_value(self):
        projection_var = self.projection_variable_names()
        proj_val = self.instantiation_value(projection_var[0])
        if proj_val and (not isinstance(proj_val, dict) and not isinstance(proj_val, list)):
            return proj_val
        else:
            return None

    def operation_variable_value(self):        
        opval =  self.get(Attributes.OPVALUE)
        if not opval and isinstance(self.get(Attributes.OPVAR), list):
            opval = []
            for v in self.get(Attributes.OPVAR):
                iv = self.instantiation_value(v)
                if iv==None:
                    return None
                else:
                    opval.append(iv)
            opval = json.dumps(opval)
        return opval



    def variable_references(self, varName):
        """ Get all attribute names that reference the variable name"""
        varRefs = {x: y for (x, y) in self.attributes.items() if y == varName}
        return varRefs

    def projection_variables(self):
        variables = {x: y for (x, y) in self.attributes.items()
                     if str(x).startswith(VarPrefix.PROJECTION)}
        if variables:
            return variables
        else:
            return None
    
    def projection_variable_names(self):
        variables = [x for x in self.attributes.keys()
                     if str(x).startswith(VarPrefix.PROJECTION)]
        if variables:
            return variables
        else:
            return None

    def nesting_variables(self):
        variables = {x: y for (x, y) in self.attributes.items()
                     if str(x).startswith(VarPrefix.NESTING) or isinstance(y, dict)
                     }
        if variables:
            return variables
        else:
            return None

    def uninstantiated_nesting_variables(self):
        variables = {x: y for (x, y) in self.attributes.items()
                     if str(x).startswith((VarPrefix.AUXILLIARY, VarPrefix.NESTING, VarPrefix.PROJECTION))
                     and isinstance(y, dict)
                     and x != Attributes.CONTEXT
                     }
        if variables:
            return variables
        else:
            return None

    def instantiated_nesting_variables(self):
        variables = {x: y for (x, y) in self.attributes.items()
                     if str(x).startswith((VarPrefix.AUXILLIARY, VarPrefix.NESTING, VarPrefix.PROJECTION)) and (isinstance(y, dict) == False)
                     }
        if variables:
            return variables
        else:
            return None

    def instantiate_variable(self, varName, varValue, insert_missing=True):
        """
        Instantiate a variable and instantiate other variables that reference it
        """

        # change all instances to the varValue except for occurence in OPVAR
        # instantiate matching variable names only, or attributes whose values
        # match the variables

        if isinstance(varName, list):
            names = [x for x in varName if x.startswith((VarPrefix.AUXILLIARY, VarPrefix.NESTING, VarPrefix.PROJECTION))]
            values = []
            if isinstance(varValue, list):
                values = varValue
            else:
                try:
                    values = json.loads(varValue)
                except: pass
            if len(names) == len(values):
                for n,v in zip(names, values):
                    self.instantiate_variable(n,v)
            else:
                return   
        else:
            if not isinstance(varName, str):
                return;

            if insert_missing or varName in self.attributes:
                self.attributes[varName] = varValue

            for (k, v) in self.attributes.items():
                if str(v) == varName and \
                        str(k).startswith((VarPrefix.AUXILLIARY, VarPrefix.NESTING, VarPrefix.PROJECTION)):
                    self.attributes[k] = varValue
                if str(v) == varName and \
                        str(v).startswith((VarPrefix.AUXILLIARY, VarPrefix.NESTING, VarPrefix.PROJECTION)):
                    if insert_missing or k in self.attributes:
                        self.attributes[v] = varValue

    def get_object_level_attributes(self):
        olattrs = {x: y for (x, y) in self.attributes.items()
                   if x not in [Attributes.OP, Attributes.OPVAR]
                   }
        return olattrs

    def __lt__(Alist1, Alist2):
        return Alist1.cost < Alist2.cost

    def __str__(self):
        return str(self.get_alist_json_with_metadata())

    def __getitem__(self, key):
        return self.get(key)
    
    def __setitem__(self, key, value):
        self.set(key, value)



# Alist States
class States:
    IGNORE = -1
    UNEXPLORED = 0
    EXPLORED = 1
    REDUCIBLE = 2
    PRUNED = 3
    EXPLORING = 4
    REDUCED = 5


# branching options
class Branching:
    OR = 'or'
    AND = 'and'


# Alist attribute names
class Attributes:
    ID = 'id'
    SUBJECT = 's'
    PROPERTY = 'p'
    OBJECT = 'o'
    TIME = 't'
    COV = 'u'
    OP = 'h'
    OPVAR = 'v'
    SOURCE = 'kb'
    COST = 'l'
    EXPLAIN = 'xp'
    FNPLOT = 'fp'
    CONTEXT = 'cx'
    VECTOR = 'vc'
    OPVALUE = "__v__"
    PRJVAR = "?__j__"


# variable prefixes
class VarPrefix:
    PROJECTION = '?'
    AUXILLIARY = '$'
    NESTING = '#'


class NodeTypes:
    ZNODE = 'znode'
    HNODE = 'hnode'
    FACT = 'fact'


class Contexts:
    # user contexts
    nationality = 'nationality'
    accuracy = 'accuracy'
    speed = 'speed'
    trust = 'trust'

    # environment contexts
    datetime = 'datetime'
    device = 'device'
    place = 'place'
