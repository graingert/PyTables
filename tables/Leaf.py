########################################################################
#
#       License: BSD
#       Created: October 14, 2002
#       Author:  Francesc Alted - falted@openlc.org
#
#       $Source: /home/ivan/_/programari/pytables/svn/cvs/pytables/pytables/tables/Leaf.py,v $
#       $Id: Leaf.py,v 1.28 2003/12/20 12:59:55 falted Exp $
#
########################################################################

"""Here is defined the Leaf class.

See Leaf class docstring for more info.

Classes:

    Leaf

Functions:


Misc variables:

    __version__


"""

__version__ = "$Revision: 1.28 $"

import types
from utils import checkNameValidity
from AttributeSet import AttributeSet
from hdf5Extension import _getFilters

class Leaf:
    """A class to place common functionality of all Leaf objects.

    A Leaf object is all the nodes that can hang directly from a
    Group, but that are not groups nor attributes. Right now this set
    is composed by Table and Array objects.

    Leaf objects (like Table or Array) will inherit the next methods
    and variables using the mix-in technique.

    Methods:

        close()
        flush()
        getAttr(attrname)
        rename(newname)
        remove()
        setAttr(attrname, attrvalue)

    Instance variables:

        name -- the leaf node name
        hdf5name -- the HDF5 leaf node name
        objectID -- the HDF5 object ID of the Leaf node
        title -- the leaf title
        shape -- the leaf shape
        compress -- the compression level (0 means no compression)
        complib -- the compression filter
        shuffle -- whether the shuffle filter is active or not
        byteorder -- the byteorder of the leaf
        attrs -- The associated AttributeSet instance

    """

    
    def _g_putObjectInTree(self, name, parent):
        """Given a new Leaf object (fresh or in a HDF5 file), set
        links and attributes to include it in the object tree."""
        
        # New attributes for the this Leaf instance
        parent._g_setproperties(name, self)
        self.name = self._v_name     # This is a standard attribute for Leaves
        # Call the new method in Leaf superclass 
        self._g_new(parent, self._v_hdf5name)
        # Update this instance attributes
        parent._v_leaves[self._v_name] = self
        # Update class variables
        parent._v_file.leaves[self._v_pathname] = self
        if self._v_new:
            self._create()
        else:
            self._open()
        # Attach the AttributeSet attribute
        self.attrs = AttributeSet(self)  # 1.6s/3.7s del temps
        # Once the AttributeSet instance has been created, get the title
        #self.title = self.attrs.TITLE   # 0.35s/2.7s del temps
        # Get the compression filters and levels
        self.compress, self.complib, self.shuffle = self._g_getFilters()

    # Define title as a property
    def get_title (self):
        return self.attrs.TITLE
    
    def set_title (self, title):
        self.attrs.TITLE = title

    # Define a property.  The 'delete this attribute'
    # method is defined as None, so the attribute can't be deleted.
    title = property(get_title, set_title, None,
                     "Title of this object")

    def _g_getFilters(self):
        # Default values
        complib = "zlib"
        complevel = 0
        shuffle = 0
        filters = _getFilters(self._v_parent._v_objectID, self._v_hdf5name)
        #print "Filters on %s: %s" % (self.name, filters)
        if filters:
            for name in filters:
                if name.startswith("lzo"):
                    complib = "lzo"
                    complevel = filters[name][0]
                elif name.startswith("ucl"):
                    complib = "ucl"
                    complevel = filters[name][0]
                elif name.startswith("deflate"):
                    complib = "zlib"
                    complevel = filters[name][0]
                elif name.startswith("shuffle"):
                    shuffle = 1
        return (complevel, complib, shuffle)
        
    def _g_renameObject(self, newname):
        """Rename this leaf in the object tree as well as in the HDF5 file."""

        parent = self._v_parent
        newattr = self.__dict__

        # Delete references to the oldname
        del parent._v_file.leaves[self._v_pathname]
        del parent._v_file.objects[self._v_pathname]
        del parent._v_leaves[self._v_name]
        del parent._v_childs[self._v_name]
        del parent.__dict__[self._v_name]

        # Get the alternate name (if any)
        trMap = self._v_rootgroup._v_parent.trMap
        
        # New attributes for the this Leaf instance
        newattr["_v_name"] = newname
        newattr["_v_hdf5name"] = trMap.get(newname, newname)
        newattr["_v_pathname"] = parent._g_join(newname)
        
        # Update class variables
        parent._v_file.objects[self._v_pathname] = self
        parent._v_file.leaves[self._v_pathname] = self

        # Standard attribute for Leaves
        self.name = newname
        self.hdf5name = trMap.get(newname, newname)
        
        # Call the _g_new method in Leaf superclass 
        self._g_new(parent, self._v_hdf5name)
        
        # Update this instance attributes
        parent._v_childs[newname] = self
        parent._v_leaves[newname] = self
        parent.__dict__[newname] = self
        
    def remove(self):
        "Remove a leaf"
        parent = self._v_parent
        parent._g_deleteLeaf(self._v_name)
        self.close()

    def rename(self, newname):
        """Rename a leaf"""

        # Check for name validity
        checkNameValidity(newname)
        # Check if self has a child with the same name
        if newname in self._v_parent._v_childs:
            raise RuntimeError, \
        """Another sibling (%s) already has the name '%s' """ % \
                   (self._v_parent._v_childs[newname], newname)
        # Rename all the appearances of oldname in the object tree
        oldname = self._v_name
        self._g_renameObject(newname)
        self._v_parent._g_renameNode(oldname, newname)
        
    def getAttr(self, attrname):
        """Get a leaf attribute as a string"""

        return getattr(self.attrs, attrname, None)
        
    def setAttr(self, attrname, attrvalue):
        """Set a leaf attribute as a string"""

        setattr(self.attrs, attrname, attrvalue)

    def flush(self):
        """Save whatever remaining data in buffer"""
        # This is a do-nothing fall-back method

    def close(self):
        """Flush the buffers and close this object on tree"""
        self.flush()
        parent = self._v_parent
        del parent._v_leaves[self._v_name]
        del parent.__dict__[self._v_name]
        del parent._v_childs[self._v_name]
        parent.__dict__["_v_nchilds"] -= 1
        del parent._v_file.leaves[self._v_pathname]
        del parent._v_file.objects[self._v_pathname]
        del self._v_parent
        del self._v_rootgroup
        del self._v_file
        # Detach the AttributeSet instance
        # This has to called in this manner
        #del self.__dict__["attrs"]
        # The next also work!
        # In some situations, this maybe undefined
        if hasattr(self, "attrs"): 
            self.attrs._f_close()
            del self.attrs

        # After the objects are disconnected, destroy the
        # object dictionary using the brute force ;-)
        # This should help to the garbage collector
        #self.__dict__.clear()

    def __str__(self):
        """The string reprsentation choosed for this object is its pathname
        in the HDF5 object tree.
        """
        
        # The pathname
        pathname = self._v_pathname
        # Get this class name
        classname = self.__class__.__name__
        shape = str(self.shape)
        # The title
        title = self.attrs.TITLE
        filters = ""
        if self.compress:
            filters += ", %s(%s)" % (self.complib, self.compress)
            if self.shuffle:
                filters += ", shuffled"
#         return "%s (%s%s%s) (ID: %s) %r" % \
#                (pathname, classname, shape, filters, self.objectID, title)
        return "%s (%s%s%s) %r" % \
               (pathname, classname, shape, filters, title)

