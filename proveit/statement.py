"""
This is the statement module.
"""

from proveit.expression import Expression, Variable, Operation, Lambda
from proveit.multiExpression import ExpressionDict, ExpressionList, Etcetera, isEtcVar, isEtcVarOrVar, isEtcOperation, multiExpression, singleOrMultiExpression
from proveit.impliesLiteral import IMPLIES
from proveit.forallLiteral import FORALL
from proveit.inLiteral import IN
from proveit.everythingLiteral import EVERYTHING
            
def asStatement(statementOrExpression):
    '''
    Given an expression, returns the corresponding statement (made in the current prover).
    Given a statement, returns what was given.
    '''
    if isinstance(statementOrExpression, Statement):
        return statementOrExpression
    return Statement.state(statementOrExpression).statement

class Statement:
    # All Statements, mapped by "generic" Expression representation.
    statements = dict()

    ProofCount = 0 # counter to number each proof
    utilizedProofNumbers = set() #  don't remove from _assumptionSetsForWhichProven of a ProofStepInfo unless it's proofnumber is not utilized
    
    def __init__(self, expression, _group=None, _name=None, _isAxiom=False, _isNamedTheorem=False):
        '''
        Do not use the Statement constructor externally.  Instead, do so indirectly;
        via the state method of an Expression or other Expression methods that
        generate new Statements from old Statements.
        '''
        self._expression = expression
        self._group = _group
        self._name = _name
        self._hypothesisOfImplication = None
        self._conclusionOfImplication = None
        self._implicationsOfHypothesis = set()
        self._implicators = set()
        self._specializers = set()
        self._generalizers = set()
        self._specializations = set()
        self._generalizations = set()
        self._isAxiom = _isAxiom
        self._isNamedTheorem = _isNamedTheorem
        self.proofNumber = float("inf") # number each proof for statements proven with no assumptions necessary
        self._prover = None # a Prover that proves this statement if it has no free variables and has been proven (theorem)

    @staticmethod
    def state(expression, _group=None, _name=None, _isAxiom=False, _isNamedTheorem=False):
        '''
        Make a Statement from the given Expression and return the Expression.
        '''
        from prover import Prover
        
        statement = Statement(expression, _group, _name)
        statement = Statement.statements.setdefault(repr(expression), statement)
        expression.statement = statement
        
        if _group is not None:
            assert expression == _group[_name], "A named statement is not consistently contained in its group of " + str(_group.__class__)
        if _isAxiom:
            assert isinstance(_group, Axioms), "An axiom may only be defined in within an Axioms statement group"
            statement._isAxiom = True
        if _isNamedTheorem:
            assert isinstance(_group, Theorems), "A theorem may only be defined in within an Theorems statement group"
            statement._isNamedTheorem = True
        
        if _isAxiom or _isNamedTheorem:
            # Mark as proven up to axioms and theorems. The proof won't be really complete until required
            # theorems are completely proven, but the proof steps will be in place in any case. 
            Prover._markAsProven(statement, Prover(statement, []))
            
        # When stating an implication, link together the implication, hypothesis and conclusion
        if isinstance(expression, Operation) and expression.operator == IMPLIES and len(expression.operands) == 2:
            implication = statement
            hypothesis = Statement.state(expression.operands[0]).statement
            conclusion = Statement.state(expression.operands[1]).statement
            conclusion.addImplicator(hypothesis, implication)
        
        expression.statement = statement
        return expression
            
    """
    @staticmethod
    def _makeStatement(expression):
        # find/add the statement and return it.
        varAssignments = []
        genericExpression = expression.makeGeneric(varAssignments)
        rep = repr(genericExpression)
        statement = Statement.statements.setdefault(rep, Statement(genericExpression))
        statement._manifestations.add(expression)
        if statement._defaultManifestation == None:
            statement._defaultManifestation = expression
        expression.statement = statement
        return statement             
    """
             
    def __str__(self):
        return str(self.getExpression())    
        
    """
    def getManifestations(self):
        '''
        The set of Expressions that are represented by this Statement
        (may differ only in the labeling of instance Variables).
        '''
        return self._manifestations
    """
        
    """
    def getExpression(self):
        '''
        The default Expression represented by this Statement (the first one stated).
        '''
        return self._defaultManifestation
    """
    
    def getExpression(self):
        return self._expression
    
    def freeVars(self):
        return self.getExpression().freeVars()
    
    @staticmethod
    def specialize(originalExpr, subMap):
        '''
        State and return a tuple of (specialization, conditions).  The 
        specialization derives from the given original statement and its conditions
        via a specialization inference rule.  It is the specialized form of the 'original' 
        expression by substituting one or more instance variables of outer Forall operations 
        according to the given substitution map.  Remaining variables in the map may
        be included for simultaneous relabelling.  There may end up being free variables
        which can be considered to be "arbitrary" variables used in logical reasoning.  
        Eventually they should be bound again via generalization (the counterpart to 
        specialization).
        '''
        substitutingVars = set()
        operationSubMap = dict()
        # the k==v cases are implicit, so remove them
        subMap = {k:v for k, v in subMap.iteritems() if k != v}
        for subVar in subMap.keys():
            try:
                if isinstance(subVar, Operation):
                    # convert f(x):expression in subMap to f:(x->expression) in operationSubMap
                    # for substituting an operation via a variable operator
                    operation = subVar
                    subVar = operation.operator
                    lambdaExpr = singleOrMultiExpression(subMap[operation])
                    if isinstance(lambdaExpr, ExpressionList):
                        raise ImproperSpecialization('Only Etcetera operations may be specialized to lists of expressions')
                    operationSubMap[subVar] = Lambda(operation.operands, lambdaExpr)
                elif isEtcOperation(subVar):
                    # convert ..Q(..x..)..:expressions in subMap to ..Q..:(..x..->expressions) in operationSubMap
                    # for substituting an etcetera operation via a variable operator
                    operation = subVar.etcExpr
                    lambdaExpr = multiExpression(subMap[subVar])
                    subVar = Etcetera(operation.operator)
                    operationSubMap[subVar] = Lambda(operation.operands, lambdaExpr)
            except TypeError as e:
                raise ImproperSpecialization("Improper Operation substitution, error transforming to Lambda: " + e.message)
            except ValueError as e:
                raise ImproperSpecialization("Improper Operation substitution, error transforming to Lambda: " + e.message)
            if not isinstance(subVar, Variable) and not isEtcVar(subVar):
                raise ImproperSpecialization("Substitution map must map either Variable types or Operations that have Variable operators or Etcetera-wrapped versions of these")
            substitutingVars.add(subVar)
        varSubMap = {var:singleOrMultiExpression(expr) for var, expr in subMap.iteritems() if isEtcVarOrVar(var)}
        for var,sub in varSubMap.iteritems():
            if not isEtcVar(var) and isinstance(sub, ExpressionList):
                raise ImproperSpecialization('May only specialize an Etcetera-wrapped Variable to a list of Expressions')
        assert originalExpr.operator == FORALL, "May only specialize a FORALL expression"
        expr = originalExpr.operands
        lambdaExpr = expr['instance_mapping']
        domain = expr['domain']
        assert isinstance(lambdaExpr, Lambda), "FORALL Operation etcExpr must be a Lambda function, or a dictionary mapping 'lambda' to a Lambda function"
        # extract the instance expression and instance variables from the lambda expression        
        instanceVars, expr, conditions  = lambdaExpr.arguments, lambdaExpr.expression['instance_expression'], list(lambdaExpr.expression['conditions'])
        if domain != EVERYTHING:
            conditions += [IN.operationMaker((var, domain)) for var in instanceVars]
        for arg in lambdaExpr.arguments:
            if isinstance(arg, Variable) and arg in substitutingVars and isinstance(substitutingVars, ExpressionList):
                raise ImproperSpecialization("May only specialize a Forall instance variable with an ExpressionList if it is wrapped in Etcetera")
        # any remaining variables may be used only for relabeling
        relabelVars = substitutingVars.difference(instanceVars)
        for relabelVar in relabelVars:
            if relabelVar in operationSubMap:
                raise ImproperSpecialization('May only perform Operation specialization by substituting instance variables of forall operations')
            sub = varSubMap[relabelVar]
            for v in sub if isinstance(sub, ExpressionList) else [sub]:
                if isinstance(relabelVar, Variable) and not isinstance(v, Variable):
                    raise ImproperSpecialization('May only specialize by substituting instance variables of forall operations or otherwise simply relabeling variables.  A Variable may be relabeled to another Variable.')
                elif isEtcVar(relabelVar) and not isEtcVarOrVar(v):
                    raise ImproperSpecialization('May only specialize by substituting instance variables of forall operations or otherwise simply relabeling variables.  An Etcetera-wrapped Variable may be relabeled to a list of (Etcetera-wrapped) Variables')
        relabMap = {k:v for k,v in varSubMap.items() if k in relabelVars}
        nonRelabSubMap = {k:v for k,v in varSubMap.items() if k not in relabelVars}
        # make and state the specialized expression with appropriate substitutions
        specializedExpr = Statement.state(expr.substituted(nonRelabSubMap, operationSubMap, relabelMap = relabMap))
        # make substitutions in the condition
        subbedConditions = {asStatement(condition.substituted(nonRelabSubMap, operationSubMap, relabelMap = relabMap)) for condition in conditions}
        Statement.state(originalExpr)
        # add the specializer link
        specializedExpr.statement.addSpecializer(originalExpr.statement, subMap, subbedConditions)
        # return the specialized expression and the 
        return specializedExpr, subbedConditions
                       
    @staticmethod
    def generalize(originalExpr, newForallVars, newConditions=tuple(), newDomain=EVERYTHING):
        '''
        State and return a generalization of a given original statement
        which derives from the original statement via a generalization inference
        rule.  This is the counterpart of specialization.  Where the original 
        has free variables taken to represent any particular 'arbitrary' values, 
        the  generalized form is a forall statement over some or all of these once
        free variables.  That is, it is statement applied to all values of any 
        of the once free variable(s) under the given condition(s) and/or domain.  
        Any condition/domain  restriction is allowed because it only weakens the 
        statement relative  to no condition.  The newForallVar(s) and newCondition(s) 
        may be singular or plural (iterable).
        '''
        forallMaker = FORALL.operationMaker
        generalizedExpr = Statement.state(forallMaker(instanceVars=newForallVars, instanceExpr=originalExpr, conditions=newConditions, domain=newDomain))
        Statement.state(originalExpr)
        generalizedExpr.statement.addGeneralizer(originalExpr.statement, newForallVars, newConditions, newDomain)
        # In order to be a valid tautology, we have to make sure that the expression is
        # a generalization of the original.
        Statement._checkGeneralization(generalizedExpr, originalExpr)
        return generalizedExpr
    
    @staticmethod
    def _checkGeneralization(expr, instanceExpr):
        '''
        Make sure the expr is a generalization of the instanceExpr.
        '''
        assert isinstance(expr, Operation) and expr.operator == FORALL, 'The result of a generalization must be a FORALL operation'
        expr = expr.operands
        lambdaExpr = expr['instance_mapping']
        assert isinstance(lambdaExpr, Lambda), 'A FORALL Expression must be in the proper form'
        expr = lambdaExpr.expression['instance_expression']
        assert expr == instanceExpr, 'Generalization not consistent with the original expression: ' + str(expr) + ' vs ' + str(instanceExpr)
                    
    def isAxiom(self):
        return self._isAxiom
    
    def isNamedTheorem(self):
        return self._isNamedTheorem
    
    def isProvenTheorem(self):
        '''
        A proven theorem is a proven statement without free variables (may be named or unnamed).
        '''
        return self.isProven() and len(self.getExpression().freeVars()) == 0
    
    def hasName(self):
        return not self._name is None
        
    def getGroupAndName(self):
        return self._group, self._name
        
    def addSpecializer(self, original, subMap, conditions):
        subMap = {key:singleOrMultiExpression(val) for key, val in subMap.iteritems()}
        self._specializers.add((original, tuple(subMap.items()), tuple(conditions)))
        original._specializations.add(self)

    def addGeneralizer(self, original, forallVars, conditions, domain):
        if conditions is None: conditions = tuple()
        self._generalizers.add((original, tuple(forallVars), tuple([asStatement(condition) for condition in multiExpression(conditions)]), domain))
        original._generalizations.add(self)
        
    def addImplicator(self, hypothesis, implication):
        if (hypothesis, implication) in self._implicators:
            return # already in implicators list
        self._implicators.add((hypothesis, implication))
        implication._hypothesisOfImplication = hypothesis
        implication._conclusionOfImplication = self
        hypothesis._implicationsOfHypothesis.add(implication)

    def getProver(self, assumptions=frozenset()):
        '''
        If this statement was proven under the given assumptions and this proof is to be
        remembered (i.e., not a clear temporary proof), returns the Prover that proves 
        this statement; otherwise, returns None.
        '''
        from prover import Prover
        if self._prover != None:
            return self._prover # proof requiring no assumptions
        if len(assumptions) > 0:
            assumptions = frozenset(assumptions)
            return Prover.getProver(self, assumptions)
        
    def getOrMakeProver(self, assumptions=frozenset()):
        '''
        If this statement was proven, returns the Prover that proves this statement;
        otherwise, returns a new Prover to be used to find the proof or explore the possibilities.
        '''
        from prover import Prover
        prover = self.getProver(assumptions)
        if prover != None:
            return prover
        return Prover(self, assumptions)    
    
    def isProven(self, assumptions=frozenset(), maxDepth=float("inf"), markProof=True):
        """
        Attempt to prove this statement under the given assumptions.  If a proof derivation
        is found, returns True.  If it can't be found in the number of steps indicated by
        maxDepth, returns False.
        """
        from prover import Prover
        return Prover.isProven(self, assumptions, maxDepth, markProof)
        
    def wasProven(self, assumptions=frozenset()):
        """
        Returns True iff this statement has been proven under the given assumptions
        and it is a proof that is remembered (i.e., not a clear temporary proof).
        """
        return self.getProver(assumptions) != None

    def provingAssumptions(self, assumptions=frozenset()):
        """
        Returns the subset of the assumptions that proves the statement,
        or None if no such proof was made or remembered.
        """
        prover = self.getProver(assumptions)
        if prover == None: return None
        return prover.assumptions
    
class ImproperSpecialization(Exception):
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return self.message

class StatementGroup(dict):
    def __init__(self, package, exclusions):
        assert isinstance(package, str), "The package of a StatementGroup must be a string representation of a Python package"
        self.package = package
        self.exclusions = dict(exclusions)
    
    def finish(self, defs):
        for name, expr in defs.iteritems():
            if name not in self.exclusions and isinstance(expr, Expression):
                self.__setitem__(name, expr)

class Axioms(StatementGroup):
    # maps packages to Axioms objects to ensure uniqueness by package
    AxiomGroups = dict()
    
    def __init__(self, package, exclusions):
        StatementGroup.__init__(self, package, exclusions)
        assert package not in Axioms.AxiomGroups, 'May only declay one Axioms object per package'
        Axioms.AxiomGroups[package] = self
    
    def finish(self, defs):
        StatementGroup.finish(self, defs)
        for name, expr in self.iteritems():
            Statement.state(expr, _group=self, _name=name, _isAxiom=True)

class Theorems(StatementGroup):
    # maps packages to Theorems objects to ensure uniqueness by package
    TheoremGroups = dict()
    
    def __init__(self, package, exclusions):
        StatementGroup.__init__(self, package, exclusions)
        assert package not in Theorems.TheoremGroups, 'May only declay one Theorems object per package'
        Theorems.TheoremGroups[package] = self

    def finish(self, defs):
        StatementGroup.finish(self, defs)
        for name, expr in self.iteritems():
            Statement.state(expr, _group=self, _name=name, _isNamedTheorem=True)