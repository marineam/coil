"""Text format for configurations."""

import re, copy, sys, os

from twisted.protocols import basic

from coil import struct


def pythonString(st):
    assert st[0] == '"' and st[-1] == '"'
    # strip off the quotes
    st = st[1:-1].decode("utf-8")
    for quoted, value in [
        ('\\\\', '\\'), # backslashes
        ('\\"', '"'), # quotes
        ('\\n', '\n'),
        ('\\r', '\r'),
        ('\\t', '\t'),
        ]:
        st = st.replace(quoted, value)
    return st
    

class ParseError(Exception):
    def __init__(self, filePath, line, column, reason):
        self.filePath = filePath
        self.line = line
        self.column = column
        self.reason = reason
        Exception.__init__(self, "%s (line %d, column %d)" % (reason, line, column))


atomRegex = r'[a-zA-Z]([a-zA-Z0-9_.])*'
ATOM = re.compile(atomRegex)
DELETEDATTR = re.compile("~" + atomRegex)
pathRegex = r"[@a-zA-Z_]([@a-zA-Z0-9_.])*"
ATTRIBUTE = re.compile(pathRegex + ":")
LINK = re.compile("=([.])*" + pathRegex)
REFERENCE = re.compile("(([.]+)|(@root))"  +  r"([@a-zA-Z0-9_.])*")
STRING = re.compile(r'"([^\\"]|\\.)*"')
NUMBER = re.compile(r'-?[0-9]+(\.[0-9]*)?')
whitespaceRegex = '[ \n\r\t]+'
WHITESPACE = re.compile(whitespaceRegex)


class PreStruct:

    def __init__(self):
        self.extends = None
        self.attributes = []
        self.deletedAttributes = []

    def create(self):
        return struct.Struct(self.extends, self.attributes, self.deletedAttributes)


class SymbolicExpressionReceiver(basic.LineReceiver):

    delimiter = "\n"

    # I don't ever want to buffer more than 64k of data before bailing.
    maxUnparsedBufferSize = 32 * 1024 

    def __init__(self, filePath):
        self.filePath = filePath
        self.structStack = [PreStruct()]
        self.attributeStack = []
        self.listStack = []
        self.line = 0
        self.column = 0
    
    def parseError(self, reason):
        raise ParseError(self.filePath, self.line, self.column, reason)

    def openParen(self):
        newCurrentSexp = []
        if self.listStack:
            self.listStack[-1].append(newCurrentSexp)
        self.listStack.append(newCurrentSexp)

    def closeParen(self):
        aList = self.listStack.pop()
        if not self.listStack:                
            self._valueReceived(aList)

    def openStruct(self):
        self.structStack.append(PreStruct())

    def closeStruct(self):
        if len(self.structStack) == 1:
            self.parseError("extra or unmatched }")
        pre = self.structStack.pop()
        self._valueReceived(pre.create())

    def _tokenReceived(self, tok):        
        if self.listStack:
            self.listStack[-1].append(tok)
            if not self.listStack:
                self._sexpRecv(i)
        else:
            self._valueReceived(tok)

    # special attribute/value pairs:
    def _checkForExtends(self):
        if self.structStack[-1].extends != None:
            self.parseError("Only one of @extends/@package/@file can be set per struct")

    def special_extends(self, value):
        if not isinstance(value, struct.Link):
            self.parseError("@extends must have a link as a value")
        self._checkForExtends()
        # XXX kitten killin' time
        myCopy = copy.deepcopy(self)
        for a in self.attributeStack:
            myCopy.closeStruct()
        node = struct.StructNode(myCopy.structStack[0].create())
        for a in self.attributeStack:
            node = node.get(a)
        extends = node._followLink(value)
        self.structStack[-1].extends = extends._struct

    def _setExtendsFromPath(self, path):
        self._checkForExtends()
        try:
            f = open(path, "r")
            self.structStack[-1].extends = fromSequence(f, path)
        except (OSError, IOError):
            self.parseError("Error reading file")
        f.close()
        
    def special_package(self, value):
        if not isinstance(value, unicode):
            self.parseError("@package must get string as value")
        try:
            package, path = value.split(":", 1)
        except ValueError:
            self.parseError('@package value must be "package:path"')
        parts = package.split(".")
        parts.append("__init__.py")
        fullpath = None
        for directory in sys.path:
            if not isinstance(directory, (str, unicode)):
                continue
            if os.path.exists(os.path.join(directory, *parts)):
                fullpath = os.path.join(directory, *(parts[:-1] + [path]))
                break
        if not fullpath:
            self.parseError("Couldn't find package")
        self._setExtendsFromPath(fullpath)

    def special_file(self, value):
        if not isinstance(value, unicode):
            self.parseError("@file must get string as value")
        self._setExtendsFromPath(value)
    
    def _valueReceived(self, xp):
        if not self.attributeStack:
            self.parseError("value with no attribute name")
        attribute = self.attributeStack.pop()
        if attribute.startswith("@"):
            handler = getattr(self, "special_%s" % (attribute[1:],), None)
            if not handler:
                self.parseError("Unknown special form %s" % attribute)
            handler(xp)
        else:
            self.structStack[-1].attributes.append((attribute, xp))

    def _attributeReceived(self, attribute):
        if len(self.attributeStack) != len(self.structStack) - 1:
            self.parseError("two attributes in a row without value")
        if "@" in attribute and not hasattr(self, "special_%s" % (attribute[1:],)):
            self.parseError("'@' cannot be used in standard attribute names.")
        self.attributeStack.append(attribute)

    def _deleteReceived(self, attribute):
        if len(self.attributeStack) != len(self.structStack) - 1:
            self.parseError("attribute not followed by value")
        self.structStack[-1].deletedAttributes.append(attribute)

    linkAtoms = {"@root": struct.ROOT,}

    def _parseLink(self, linkStr):
        parts = []
        m = re.match("[.]*", linkStr)
        if m:
            end = m.end()
            dots, linkStr = linkStr[:end], linkStr[end:]
            for i in range(len(dots) - 1):
                parts.append(struct.CONTAINER)
        parts.extend([self.linkAtoms.get(p, p) for p in linkStr.split(".")])
        return struct.Link(*parts)
    
    def _linkReceived(self, linkStr):    
        self._valueReceived(self._parseLink(linkStr))

    def _referenceReceived(self, symbol):
        if self.attributeStack and self.attributeStack[-1] == "@extends" and not self.listStack:
            self._valueReceived(self._parseLink(symbol))
        else:
            self.parseError("References can only be used after @extends")
    
    def _atomReceived(self, symbol):
        self._tokenReceived(self._makeAtom(symbol))
    
    def _makeAtom(self, st):
        if st == "None":
            return None
        elif st == "False":
            return False
        elif st == "True":
            return True
        else:
            self.parseError("invalid value %r" % (st,))

    def lineReceived(self, line):
        self.line += 1
        origLineLength = len(line)
        while line:
            self.column = origLineLength - len(line)
            # eat any whitespace at the beginning of the string.
            m = WHITESPACE.match(line)
            if m:
                line = line[m.end():]
                continue
            
            if line[0] == '[':
                self.openParen()
                line = line[1:]
                continue
            if line[0] == ']':
                self.closeParen()
                line = line[1:]
                continue
            if line[0] == '{':
                self.openStruct()
                line = line[1:]
                continue
            if line[0] == '}':
                self.closeStruct()
                line = line[1:]
                continue
            if line[0] == "#":
                # it's a comment
                return
            m = STRING.match(line)
            if m:
                end = m.end()
                st, line = line[:end], line[end:]
                self._tokenReceived(pythonString(st))
                continue
            m = NUMBER.match(line)
            if m:
                end = m.end()
                number, line = line[:end], line[end:]
                # If this fails, the RE is buggy.
                if '.' in number:
                    number = float(number)
                else:
                    number = int(number)
                self._tokenReceived(number)
                continue
            m = ATTRIBUTE.match(line)
            if m:
                end = m.end()
                attribute, line = line[:end-1], line[end:]
                self._attributeReceived(attribute)
                continue
            m = DELETEDATTR.match(line)
            if m:
                end = m.end()
                attribute, line = line[1:end], line[end:]
                self._deleteReceived(attribute)
                continue
            m = LINK.match(line)
            if m:
                end = m.end()
                link, line = line[1:end], line[end:]
                self._linkReceived(link)
                continue
            m = ATOM.match(line)
            if m:
                end = m.end()
                symbol, line = line[:end], line[end:]
                self._atomReceived(symbol)
                continue
            m = REFERENCE.match(line)
            if m:
                end = m.end()
                symbol, line = line[:end], line[end:]
                self._referenceReceived(symbol)
                continue
            else:
                self.parseError("invalid syntax")
        if len(line) > self.maxUnparsedBufferSize:
            self.parseError("Too much unparsed data.")

    def connectionLost(self, reason):
        if len(self.structStack) != 1:
            self.parseError("incomplete tree")
        self.result = self.structStack.pop().create()


def fromSequence(iterOfStrings, filePath="<?>"):
    f = SymbolicExpressionReceiver(filePath)
    for s in iterOfStrings:
        f.dataReceived(s)
    f.dataReceived("\n")
    f.connectionLost(None)
    return f.result

def fromString(st):    
    return fromSequence([st])
