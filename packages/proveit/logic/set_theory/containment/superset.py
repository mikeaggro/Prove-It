from proveit import Literal, BinaryOperation, USE_DEFAULTS
from proveit._common_ import A, B, C, x
from containment_relation import ContainmentRelation, ContainmentSequence

class SupersetRelation(ContainmentRelation):
    def __init__(self, operator, superset, subset):
        ContainmentRelation.__init__(self, operator, superset, subset)
        self.superset = self.operands[0]
        self.subset = self.operands[1]
    
    @staticmethod
    def WeakRelationClass():
        return SupersetEq 

    @staticmethod
    def StrongRelationClass():
        return Superset
    
    @staticmethod
    def SequenceClass():
        return SupersetSequence

class SupersetSequence(ContainmentSequence):
    def __init__(self, operators, operands):
        ContainmentSequence.__init__(self, operators, operands)
    
    @staticmethod
    def RelationClass():
        return SupersetRelation

class Superset(SupersetRelation):
    # operator of the Superset operation
    _operator_ = Literal(stringFormat='supset', latexFormat=r'\supset', context=__file__)    

    # map left-hand-sides to Superset KnownTruths
    #   (populated in TransitivityRelation.deriveSideEffects)
    knownLeftSides = dict()    
    # map right-hand-sides to Superset KnownTruths
    #   (populated in TransitivityRelation.deriveSideEffects)
    knownRightSides = dict() 
            
    def __init__(self, superset, subset):
        SupersetRelation.__init__(self, Superset._operator_, superset, subset)

    def deriveSideEffects(self, knownTruth):
        '''
        Derive the relaxed supseteq form as a side-effect.
        '''
        SupersetRelation.deriveSideEffects(self, knownTruth)
        self.derivedRelaxed(assumptions=knownTruth.assumptions)

    def deriveReversed(self, assumptions=USE_DEFAULTS):
        '''
        From A subset B, derive B supset A.
        '''
        from _theorems_ import reverseSupset
        return reverseSupset.specialize({A:self.superset, B:self.subset}, assumptions=assumptions)

    def deriveRelaxed(self, assumptions=USE_DEFAULTS):
        '''
        From A supset B, derive A supseteq B.
        '''
        from _theorems_ import relaxSupset
        return relaxSupset.specialize({A:self.superset, B:self.subset}, assumptions=assumptions)

    def applyTransitivity(self, other, assumptions=USE_DEFAULTS):
        '''
        Apply a transitivity rule to derive from this A superset B expression 
        and something of the form B supseteq C, B supset C, or B=C to 
        obtain A supset B as appropriate.
        '''
        from proveit.logic import Equals
        from _theorems_ import transitivitySupsetSupset, transitivitySupsetSupsetEq
        from superset import Subset, SubsetEq
        if isinstance(other, Equals):
            return ContainmentRelation.applyTransitivity(other, assumptions) # handles this special case
        if isinstance(other,Subset) or isinstance(other,SubsetEq):
            other = other.deriveReversed(assumptions)
        elif other.lhs == self.rhs:
            if isinstance(other,Superset):
                result = transitivitySupsetSupset.specialize({A:self.lhs, B:self.rhs, C:other.rhs}, assumptions=assumptions)
                return result.checked({self})
            elif isinstance(other,SupersetEq):
                result = transitivitySupsetSupsetEq.specialize({A:self.lhs, B:self.rhs, C:other.rhs}, assumptions=assumptions)
                return result
        elif other.rhs == self.lhs:
            if isinstance(other,Superset):
                result = transitivitySupsetSupset.specialize({A:self.lhs, B:self.rhs, C:other.lhs}, assumptions=assumptions)
                return result
            elif isinstance(other,SupersetEq):
                result = transitivitySupsetSupsetEq.specialize({A:self.lhs, B:self.rhs, C:other.lhs}, assumptions=assumptions)
                return result
        else:
            raise ValueError("Cannot perform transitivity with %s and %s!"%(self, other))
                
class SupersetEq(SupersetRelation):
    # operator of the SupersetEq operation
    _operator_ = Literal(stringFormat='supseteq', latexFormat=r'\supseteq', context=__file__)    
    
    # map left-hand-sides to SupersetEq KnownTruths
    #   (populated in TransitivityRelation.deriveSideEffects)
    knownLeftSides = dict()    
    # map right-hand-sides to SupersetEq KnownTruths
    #   (populated in TransitivityRelation.deriveSideEffects)
    knownRightSides = dict() 
    
    def __init__(self, superset, subset):
        SupersetRelation.__init__(self, SupersetEq._operator_, superset, subset)

    def deriveReversed(self, assumptions=USE_DEFAULTS):
        '''
        From A supseteq B, derive B subseteq A.
        '''
        from _theorems_ import reverseSupsetEq
        return reverseSupsetEq.specialize({A:self.superset, B:self.subset}, assumptions=assumptions)
        
    def conclude(self, assumptions):
        from _theorems_ import supersetEqViaEquality        
        from proveit._generic_ import TransitiveRelation
        from proveit import ProofFailure
        
        try:
            # first attempt a transitivity search
            return TransitiveRelation.conclude(self, assumptions)
        except ProofFailure:
            pass # transitivity search failed
        
        # any set is a superset of itself
        if self.operands[0] == self.operands[1]:
            return supersetEqViaEquality.specialize({A:self.operands[0], B:self.operands[1]})

    def unfold(self, elemInstanceVar=x, assumptions=USE_DEFAULTS):
        '''
        From A superseteq B, derive and return (forall_{x in B} x in A).
        x will be relabeled if an elemInstanceVar is supplied.
        '''
        from _theorems_ import unfoldSupsetEq
        return unfoldSupsetEq.specialize({A:self.leftOperand, B:self.rightOperand}, relabelMap={x:elemInstanceVar}, assumptions=assumptions)
    
    def deriveSupsersetMembership(self, element, assumptions=USE_DEFAULTS):
        '''
        From A superseteq B and x in B, derive x in A.
        '''
        from _theorems_ import unfoldSupsetEq
        return unfoldSupsetEq.specialize({A:self.leftOperand, B:self.rightOperand, x:element}, assumptions=assumptions)
    
    def concludeAsFolded(self, elemInstanceVar=x, assumptions=USE_DEFAULTS):
        '''
        Derive this folded version, A superset B, from the unfolded version,
        (forall_{x in B} x in A).
        '''
        from _theorems_ import foldSupsetEq
        return foldSupsetEq.specialize({A:self.leftOperand, B:self.rightOperand}, relabelMap={x:elemInstanceVar}, assumptions=assumptions).deriveConsequent(assumptions)
        
    def applyTransitivity(self, other, assumptions=USE_DEFAULTS):
        '''
        Apply a transitivity rule to derive from this A superseteq B expression 
        and something of the form B supseteq C, B supset C, or B=C to 
        obtain A supset B or A supseteq B as appropriate.
        '''
        from proveit.logic import Equals
        from _theorems_ import transitivitySupsetEqSupset, transitivitySupsetEqSupsetEq
        from superset import Subset, SubsetEq
        if isinstance(other, Equals):
            return ContainmentRelation.applyTransitivity(other, assumptions) # handles this special case
        if isinstance(other,Subset) or isinstance(other,SubsetEq):
            other = other.deriveReversed(assumptions)
        elif other.lhs == self.rhs:
            if isinstance(other,Superset):
                result = transitivitySupsetEqSupset.specialize({A:self.lhs, B:self.rhs, C:other.rhs}, assumptions=assumptions)
                return result.checked({self})
            elif isinstance(other,SupersetEq):
                result = transitivitySupsetEqSupsetEq.specialize({A:self.lhs, B:self.rhs, C:other.rhs}, assumptions=assumptions)
                return result
        elif other.rhs == self.lhs:
            if isinstance(other,Superset):
                result = transitivitySupsetEqSupset.specialize({A:self.lhs, B:self.rhs, C:other.lhs}, assumptions=assumptions)
                return result
            elif isinstance(other,SupersetEq):
                result = transitivitySupsetEqSupsetEq.specialize({A:self.lhs, B:self.rhs, C:other.lhs}, assumptions=assumptions)
                return result
        else:
            raise ValueError("Cannot perform transitivity with %s and %s!"%(self, other))

class NotSupersetEq(BinaryOperation):
    # operator of the NotSupersetEq operation
    _operator_ = Literal(stringFormat='nsupseteq', latexFormat=r'\nsupseteq', context=__file__)    

    def __init__(self, subset, superset):
        BinaryOperation.__init__(self, NotSupersetEq._operator_, A, B)
    
    def deriveSideEffects(self, knownTruth):
        self.unfold(knownTruth.assumptions) # unfold as an automatic side-effect

    def conclude(self, assumptions):
        return self.concludeAsFolded(assumptions)
        
    def unfold(self, assumptions=USE_DEFAULTS):
        '''
        From A nsupseteq B, derive and return not(supseteq(A, B)).
        '''
        from _theorems_ import unfoldNotSupsetEq
        return unfoldNotSupsetEq.specialize({A:self.operands[0], B:self.operands[1]}, assumptions=assumptions)

    def concludeAsFolded(self, assumptions=USE_DEFAULTS):
        '''
        Derive this folded version, A nsupset B, from the unfolded version,
        not(A supset B).
        '''
        from _theorems_ import foldNotSupsetEq
        return foldNotSupsetEq.specialize({A:self.operands[0], B:self.operands[1]}, assumptions=assumptions)
