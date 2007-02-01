
import os
import sys
import thread
import py

class FDCapture: 
    """ Capture IO to/from a given os-level filedescriptor. """
    
    def __init__(self, targetfd, tmpfile=None): 
        self.targetfd = targetfd
        if tmpfile is None: 
            tmpfile = self.maketmpfile()
        self.tmpfile = tmpfile 
        self._savefd = os.dup(targetfd)
        os.dup2(self.tmpfile.fileno(), targetfd) 
        self._patched = []

    def setasfile(self, name, module=sys): 
        """ patch <module>.<name> to self.tmpfile
        """
        key = (module, name)
        self._patched.append((key, getattr(module, name)))
        setattr(module, name, self.tmpfile) 

    def unsetfiles(self): 
        """ unpatch all patched items
        """
        while self._patched: 
            (module, name), value = self._patched.pop()
            setattr(module, name, value) 

    def done(self): 
        """ unpatch and clean up, returns the self.tmpfile (file object)
        """
        os.dup2(self._savefd, self.targetfd) 
        self.unsetfiles() 
        os.close(self._savefd) 
        self.tmpfile.seek(0)
        return self.tmpfile 

    def maketmpfile(self): 
        """ create a temporary file
        """
        f = os.tmpfile()
        newf = py.io.dupfile(f) 
        f.close()
        return newf 

    def writeorg(self, str):
        """ write a string to the original file descriptor
        """
        tempfp = os.tmpfile()
        try:
            os.dup2(self._savefd, tempfp.fileno())
            tempfp.write(str)
        finally:
            tempfp.close()

class OutErrCapture: 
    """ capture Stdout and Stderr both on filedescriptor 
        and sys.stdout/stderr level. 
    """
    def __init__(self, out=True, err=True, patchsys=True): 
        if out: 
            self.out = FDCapture(1) 
            if patchsys: 
                self.out.setasfile('stdout')
        if err: 
            self.err = FDCapture(2) 
            if patchsys: 
                self.err.setasfile('stderr')

    def reset(self): 
        """ reset sys.stdout and sys.stderr

            returns a tuple of file objects (out, err) for the captured
            data
        """
        out = err = ""
        if hasattr(self, 'out'): 
            outfile = self.out.done() 
            out = outfile.read()
        if hasattr(self, 'err'): 
            errfile = self.err.done() 
            err = errfile.read()
        return out, err 

    def writeorgout(self, str):
        """ write something to the original stdout
        """
        if not hasattr(self, 'out'):
            raise IOError('stdout not patched')
        self.out.writeorg(str)

    def writeorgerr(self, str):
        """ write something to the original stderr
        """
        if not hasattr(self, 'err'):
            raise IOError('stderr not patched')
        self.err.writeorg(str)

def callcapture(func, *args, **kwargs): 
    """ call the given function with args/kwargs
        and return a (res, out, err) tuple where
        out and err represent the output/error output
        during function execution. 
    """ 
    so = OutErrCapture()
    try: 
        res = func(*args, **kwargs)
    finally: 
        out, err = so.reset()
    return res, out, err 

