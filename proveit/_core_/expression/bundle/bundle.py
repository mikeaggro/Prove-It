'''
bundleExpr.py

Etcetera and Block are the two kinds of Bundle Expressions.  These have
special substitution rules.  When an expr_list is substituted for
a Bundle expression that is an element of an expr_list, these elements
are absorbed into the parent expr_list.  When an expr_tensor is
substituted for a Block that is an element of an expr_tensor, its
elements are absorbed into the parent expr_tensor.
'''

from proveit._core_.expression.operation import Operation
from proveit._core_.expression.expr import Expression
from proveit._core_.expression.label import Variable, MultiVariable
from proveit._core_.expression.composite import ExpressionList, ExpressionTensor

class Bundle(Expression):
    def __init__(self, multiExprType, bundledExpr, maker, extraCoreInfo = tuple()):
        assert multiExprType == ExpressionList or multiExprType == ExpressionTensor, "Unrecognized multi-expr type for Bundle"
        coreInfo = ['Etcetera'] if multiExprType == ExpressionList else ['Block']
        coreInfo += list(extraCoreInfo)
        self.multiExprType = multiExprType
        self.bundledExpr = bundledExpr
        if not isinstance(self.bundledExpr, Expression):
            raise TypeError("The 'bundled' expression should be an expr")
        self.maker = maker
        Expression.__init__(self, coreInfo, [self.bundledExpr])

    def substituted(self, exprMap, relabelMap = None, reservedVars = None):
        '''
        Returns this expression with the substitutions made 
        according to exprMap and/or relabeled according to relabelMap.
        If the substituted bundledExpr is of the multiExprType, it will be extracted 
        from the Bundle wrapping and incorporated into the multi-expr which contains it.
        '''
        if (exprMap is not None) and (self in exprMap):
            return exprMap[self]._restrictionChecked(reservedVars)
        freeBundleVars = [multiVar.variable for multiVar in self.bundledExpr.freeMultiVars()]
        bundleVarCandidates = [var for var in freeBundleVars if (var in exprMap and isinstance(exprMap[var], self.multiExprType)) or
                                (var in relabelMap and isinstance(relabelMap[var], self.multiExprType))]
        if len(bundleVarCandidates) > 1:
            raise Exception("Multiple Bundle variable expansion is unsupported due to ambiguity")
        if len(bundleVarCandidates) == 1:
            # performing a bundle expansion substitution
            bundleVar = bundleVarCandidates[0]
            subExprMap, subRelabelMap = exprMap, relabelMap
            if bundleVar in exprMap:
                subExprMap = subBundleVarMap = dict(exprMap)
            elif bundleVar in relabelMap:
                subRelabelMap = subBundleVarMap = dict(relabelMap)
            else:
                assert False, "shouldn't happen"
            bundleVarSub = subBundleVarMap[bundleVar]
            def substituteForElem(subElem):
                subBundleVarMap[bundleVar] = subElem
                return self.bundledExpr.substituted(subExprMap, subRelabelMap, reservedVars)
            if self.multiExprType == ExpressionList:
                # expr_list bundle expansion
                return ExpressionList(substituteForElem(subElem) for subElem in bundleVarSub)
            elif self.multiExprType == ExpressionTensor:
                # expr_tensor bundle expansion
                return ExpressionTensor({key:substituteForElem(subElem) for key, subElem in bundleVarSub})
        # default when not performing a bundle expansion substitution
        return self.maker(self.bundledExpr.substituted(exprMap, relabelMap, reservedVars))

    def usedVars(self):
        '''
        Returns the union of the used Variables of the bundledExpr.
        '''
        return self.bundledExpr.usedVars()
        
    def freeVars(self):
        '''
        Returns the union of the free Variables of the bundledExpr.
        '''
        return self.bundledExpr.freeVars()

    def innerFreeMultiVars(self):
        '''
        No free MultiVariables within a bundle.
        '''
        return set()
    

def isBundledVar(expr):
    # Is the expression a Bundled multivar (multivar wrapped in Bundle)?
    return isinstance(expr, Bundle) and isinstance(expr.bundledExpr, MultiVariable)

def isBundledVarOrVar(expr):
    # Is the expression either a var a Bundled var (var wrapped in Bundle)?
    return isinstance(expr, Variable) or isBundledVar(expr)

def extractVar(expr):
    # Return expr if it is a var, extract the var out of a Bundled var
    # if it is one, or return None.
    return expr.bundledExpr if isBundledVar(expr) else (expr if isinstance(expr, Variable) else None)

def isBundledOperation(expr):
    # Is the expression a Bundled operation (operation with a multivar operator wrapped in Bundle)?
    from etcetera import Etcetera
    return isinstance(expr, Etcetera) and isinstance(expr.bundledExpr, Operation) and \
        isinstance(expr.bundledExpr.operator, MultiVariable)
        

