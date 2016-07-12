import hashlib, os

class Defaults:
    def __init__(self):
        self.assumptions = frozenset()

defaults = Defaults()

class Storage:
    def __init__(self):
        self.directory = ''
        
        # For retrieved pv_it files that represent Prove-It object (Expressions, KnownTruths, and Proofs),
        # this maps the object to the pv_it file so we
        # can recall this without searching the hard drive again.
        self._proveItObjects = dict()
        
    def _retrieve_png(self, proveItObj, pngGenFn, distinction=''):
        '''
        Find the .png file for the stored Expression, KnownTruth, or Proof.
        If distinction is provided, this is an extra string that decorates
        the filename to distinguish it from the basic png of an Expression
        ['info' for exprInfo() png, 'details' for exprInfo(details=True) png].
        Create it if it did not previously exist using pngGenFn.
        If it existed or was generated, read the .png file; otherwise return None.
        '''
        if self.directory is None:
            return pngGenFn() # don't do any storage
        pv_it_filename = self._retrieve(proveItObj)
        # generate the png file, including path, from pv_it_filename and the distinction 
        png_path = os.path.join(self.directory, '.pv_it', pv_it_filename[:-6] + distinction + '.png')
        if os.path.isfile(png_path):
            # png file exists.  read and return the data.
            with open(png_path) as f:
                return f.read()
        # png file does not exist.  generate it, store it, and return it.
        png = pngGenFn()
        with open(png_path, 'w') as f:
            f.write(png)
        return png
    
    def _proveItObjId(self, proveItObject):
        '''
        Retrieve a unique id for the Prove-It object based upon its pv_it filename from calling _retrieve.
        '''
        # Retrieve pv_it files for the list of objects
        pv_it_filename = self._retrieve(proveItObject)
        # (replace os.path.sep within pv_it file paths with ':' to make this OS neutral just in case)
        return ':'.join(pv_it_filename.split(os.path.sep))
    
    def _proveItObjUniqueRep(self, proveItObject):
        '''
        Generate a unique representation string for the given Prove-It object.
        '''
        from proveit import Expression, KnownTruth, Proof
        if isinstance(proveItObject, KnownTruth):
            # To uniquely identify a KnownTruth for displaying purposes, we need its Expression and list of assumptions
            knownTruth = proveItObject
            assumptions = knownTruth.assumptions
            return 'KnownTruth:' + self._proveItObjId(knownTruth.expr) + '[' + ','.join(self._proveItObjId(assumption) for assumption in assumptions) + ']'          
        elif isinstance(proveItObject, Expression):
            # This unique_rep differs from expr._unique_rep because it is designed to avoid
            # collisions in storage which may differ from in-memory collisions (collisions are unlikely, but let's stay safe).
            expr = proveItObject
            return str(expr.__class__) + '[' + ','.join(expr._coreInfo) + '];[' + ','.join(self._proveItObjId(subExpr) for subExpr in expr.subExprIter()) + ']'
        elif isinstance(proveItObject, Proof):
            # The Proof is uniquely identified by its provenTruth and its requiredProofs (recursively)
            proof = proveItObject
            return 'Proof:' + self._proveItObjId(proof.provenTruth) + '[' + ','.join(self._proveItObjId(requiredProof) for requiredProof in proof.requiredProofs) + ']'
        else:
            raise NotImplementedError('Strorage only implemented for Expressions, Statements (effectively), and Proofs')
        
    
    def _retrieve(self, proveItObject):
        '''
        Find the .pv_it file for the stored Expression, KnownTruth, or Proof.
        Create it if it did not previously exist.  Return the .pv_it filename, relative to
        the .pv_it directory.
        '''
        if proveItObject in self._proveItObjects:
            return self._proveItObjects[proveItObject]
        pv_it_dir = os.path.join(self.directory, '.pv_it')
        unique_rep = self._proveItObjUniqueRep(proveItObject)
        # hash the unique representation and make a sub-directory of this hash value
        rep_hash = hashlib.sha1(unique_rep).hexdigest()
        if not os.path.exists(pv_it_dir):
            os.mkdir(pv_it_dir)
        hash_path = os.path.join(pv_it_dir, rep_hash)
        if not os.path.exists(hash_path):
            os.mkdir(hash_path)
        # check for existing files in this hash value sub-directory to see if the right one is there
        for expr_file in os.listdir(hash_path):
            if expr_file[-6:] == '.pv_it':
                pv_it_filename = os.path.join(rep_hash, expr_file)
                with open(os.path.join(pv_it_dir, pv_it_filename), 'r') as f:
                    if f.read() == unique_rep:
                        # an existing file contains the exported expression
                        self._pv_it_filename = pv_it_filename
                        return pv_it_filename
        # does not exist, create a new file (checking against an unlikely collision)
        index = 0
        while os.path.exists(os.path.join(hash_path, str(index) + '.pv_it')):
            index += 1
        pv_it_filename = os.path.join(rep_hash, str(index) + '.pv_it')
        with open(os.path.join(pv_it_dir, pv_it_filename), 'w') as f:
            f.write(unique_rep) # write the unique representation to a file
        # remember this for next time
        self._proveItObjects[proveItObject] = pv_it_filename
        return pv_it_filename
        
    
    def clear(self):
        '''
        Clear the .pvit subdirectory of the storage directory.
        The effect is that expression images will need to be
        regenerated.
        '''
        self._proveItObjects.clear()
        pv_it_dir = os.path.join(self.directory, '.pv_it')
        if not os.path.isdir(pv_it_dir): return
        for hash_dir in os.listdir(pv_it_dir):
            hash_path = os.path.join(pv_it_dir, hash_dir)
            for pv_it_file in os.listdir(hash_path):
                os.remove(os.path.join(hash_path, pv_it_file))
            os.rmdir(hash_path)
        os.rmdir(pv_it_dir)
    
    def __setattribute__(self, item, value):
        if item == 'storage' and value != self.storage:
            # if the storage is change, _expr_pv_its becomes obsolete
            self._expr_pv_its.clear() # start fresh
        self.__setattr__(item, value)
    
storage = Storage()


# USE_DEFAULTS is used to indicate that default assumptions
# should be used.  This value is simply None, but with
# USE_DEFAULTS, it is more explicit in the code.
USE_DEFAULTS = None