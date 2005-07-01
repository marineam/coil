"""Text format for configurations."""

import re, copy

from twisted.protocols import basic

from coil import struct


def pythonString(st):
    assert st[0] == '"' and st[-1] == '"'
    # strip off the quotes
    st = st[1:-1]
    # unescape backslashes
    st = st.replace('\\\\', '\\')
    # unescape quotes
    st = st.replace('\\"', '"')
    return st
    

class ParseError(Exception):
    def __init__(self, linenumber, reason):
        self.line = linenumber
        self.reason = reason
        Exception.__init__(self, "%s (line %d)" % (reason, linenumber))


atomRegex = r'[a-zA-Z]([a-zA-Z0-9_.])*'
ATOM = re.compile(atomRegex)
ATTRIBUTE = re.compile(atomRegex + ":")
DELETEDATTR = re.compile("~" + atomRegex)
pathRegex = r"[@a-zA-Z]([@a-zA-Z0-9_.])*"
LINK = re.compile("=" + pathRegex)
STRING = re.compile(r'"([^\\"]|\\.)*"')
NUMBER = re.compile(r'-?[0-9]+(\.[0-9]*)?')
whitespaceRegex = '[ \n\r\t]+'
WHITESPACE = re.compile(whitespaceRegex)
EXTENDSATTR = re.compile("%s%sextends%s%s:%s{"
                         % (atomRegex, whitespaceRegex, whitespaceRegex, pathRegex, whitespaceRegex))

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

    def __init__(self):
        self.structStack = [PreStruct()]
        self.attributeStack = []
        self.listStack = []
        self.line = 0
    
    def parseError(self, reason):
        raise ParseError(self.line, reason)

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

    def _valueReceived(self, xp):
        if not self.attributeStack:
            self.parseError("value with no attribute name")
        attribute = self.attributeStack.pop()
        self.structStack[-1].attributes.append((attribute, xp))

    def _attributeReceived(self, attribute):
        if len(self.attributeStack) != len(self.structStack) - 1:
            self.parseError("two attributes in a row without value")
        self.attributeStack.append(attribute)

    def _deleteReceived(self, attribute):
        if len(self.attributeStack) != len(self.structStack) - 1:
            self.parseError("attribute not followed by value")
        self.structStack[-1].deletedAttributes.append(attribute)

    def _parseExtends(self, s):
        s = s.split()
        assert s[1] == "extends"
        assert s[3] == "{"
        # XXX kitten killin' time
        myCopy = copy.deepcopy(self)
        for a in myCopy.attributeStack:
            myCopy.closeStruct()
        node = struct.StructNode(myCopy.structStack[0].create())
        for a in self.attributeStack:
            node = node.get(a)
        link = self._parseLink(s[2][:-1]) # drop the ':' at the end
        extends = node._followLink(link)
        self._attributeReceived(s[0])
        self.openStruct()
        self.structStack[-1].extends = extends._struct

    linkAtoms = {"@CONTAINER": struct.CONTAINER,
                 "@ROOT": struct.ROOT,
                 }

    def _parseLink(self, linkStr):
        parts = [self.linkAtoms.get(p, p) for p in linkStr.split(".")]
        return struct.Link(*parts)
    
    def _linkReceived(self, linkStr):    
        self._valueReceived(self._parseLink(linkStr))
    
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
        while line:            
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
            m = EXTENDSATTR.match(line)
            if m:
                end = m.end()
                extendsbit, line = line[:end], line[end:]
                self._parseExtends(extendsbit)
                continue
            m = ATOM.match(line)
            if m:
                end = m.end()
                symbol, line = line[:end], line[end:]
                self._tokenReceived(self._makeAtom(symbol))
                continue
            else:
                self.parseError("invalid syntax")
        if len(line) > self.maxUnparsedBufferSize:
            self.parseError("Too much unparsed data.")

    def connectionLost(self, reason):
        if len(self.structStack) != 1:
            self.parseError("incomplete tree")
        self.result = self.structStack.pop().create()


def fromSequence(iterOfStrings):
    f = SymbolicExpressionReceiver()
    for s in iterOfStrings:
        f.dataReceived(s)
    f.dataReceived("\n")
    f.connectionLost(None)
    return f.result

def fromString(st):    
    return fromSequence([st])
