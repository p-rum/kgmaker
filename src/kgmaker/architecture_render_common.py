"""Existing bounded renderer helpers shared without a renderer import cycle."""
import math
import unicodedata
from .architecture_model import ViewDocument,ViewNode,ViewEdge
from .view_explanation import _ref

_MAX_ITEMS=100000


_MAX_CHARS=1000000


class InterfaceMarkdownError(ValueError):
    def __init__(self,code='INVALID_INTERFACE_MARKDOWN'):
        self.code=code
        super().__init__(code)


# Preserve the public exception's original import/pickle path; same class reexport.
InterfaceMarkdownError.__module__ = 'kgmaker.architecture_render'

def _fail(code='INVALID_INTERFACE_MARKDOWN'):
    raise InterfaceMarkdownError(code) from None


def _bounded(value):
    """Count occurrences before model normalization, including shared children."""
    stack=[(value,0,False)];active=set();count=chars=0
    while stack:
        item,depth,leave=stack.pop()
        if leave:active.remove(id(item));continue
        count+=1
        if count>_MAX_ITEMS or depth>40:_fail('INTERFACE_MARKDOWN_LIMIT')
        kind=type(item)
        if kind is str:
            chars+=len(item)
            if len(item)>16384 or chars>_MAX_CHARS:_fail('INTERFACE_MARKDOWN_LIMIT')
            if any(unicodedata.category(c)=='Cs' for c in item):_fail()
        elif kind is float:
            if not math.isfinite(item):_fail()
        elif kind is int:
            if item.bit_length()>128:_fail('INTERFACE_MARKDOWN_LIMIT')
        elif item is None or kind is bool:pass
        elif kind in (dict,list,tuple,ViewDocument,ViewNode,ViewEdge):
            if id(item) in active:_fail()
            active.add(id(item));stack.append((item,depth,True))
            values=vars(item) if kind in (ViewDocument,ViewNode,ViewEdge) else item
            if len(values)>10000:_fail('INTERFACE_MARKDOWN_LIMIT')
            if type(values) is dict:
                for key,child in values.items():
                    if type(key) is not str:_fail()
                    stack.extend(((key,depth+1,False),(child,depth+1,False)))
            else:stack.extend((child,depth+1,False) for child in values)
        else:_fail()


def _identity(value):
    try:return _ref(value)
    except (ValueError,TypeError,KeyError,AttributeError):_fail('UNSAFE_INTERFACE_MARKDOWN')
