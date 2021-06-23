#!/usr/bin/python
# -*- coding: UTF-8 -*-

try:
    set
except NameError:
    from sets import Set as set
import sys
if sys.version > '3':
    import queue as Queue
else:
    import Queue
import copy


class BinaryTrieNode(object):
    def __init__(self, parent=None, lchild=None, 
                        rchild=None,
                        nexthops=[None],
                        depth=None):
        self.parent = parent
        self.lchild = lchild
        self.rchild = rchild
        self.inheritedNexthop = None
        self.nexthopSet = set(nexthops)
        self.depth = depth

    def addLeftChild(self, node):
        self.lchild = node

    def addRightChild(self, node):
        self.rchild = node

    def hasChild(self):
        return self.lchild != None or self.rchild != None

    def isOnlyHasRightChild(self):
        return self.lchild == None and self.rchild != None

    def isOnlyHasLeftChild(self):
        return self.lchild != None and self.rchild == None

    def isNextHopNone(self):
        return list(self.nexthopSet) in [[None], []]

    def getParent(self):
        return self.parent
    
    def isRoot(self):
        return self.parent == None

    def isInheritedInNexthopSet(self):
        # print("nexthopSet: {0}   nexthopSet: {1}".format(self.nexthopSet, self.nexthopSet))
        return self.inheritedNexthop in self.nexthopSet

    # def __str__(self):
    #     return "{0} {1} {2}\n".format(self.lchild, self.rchild, self.depth)


class BinaryTrie(object):
    def __init__(self, rules):
        self.rules = rules
        # construct a binary tree according to the rules
        self.root = BinaryTrieNode(nexthops=[-2], depth=0)
        self.constructBinaryTrie()

    def constructBinaryTrie(self):
        for rule in self.rules:
            # print("\n\nrule: {0}".format(rule))
            prefix = rule.prefix
            length = rule.length
            nexthop = rule.nexthop
            currentNode = self.root

            # self.levelAccess()

            # print("lchild: {0}".format(self.root.lchild))
            # print("rchild: {0}".format(self.root.rchild))

            # count = 0
            for idx in range(1, length+1):
                # print("idx: {0}".format(idx))
                if idx == length:
                    newNodeNexthop = nexthop
                else:
                    newNodeNexthop = None
                newNode = BinaryTrieNode(parent=currentNode,
                                            nexthops=[newNodeNexthop],
                                            depth=idx)

                binary = self._getBinaryFromBin(prefix, length-idx)
                # print(binary)
                # print("currentNode: {0}".format(currentNode))
                if binary == 0:
                    if currentNode.lchild == None:
                        # print("add left count :{0}".format(count))
                        # count += 1
                        currentNode.lchild = newNode
                    elif (currentNode.lchild != None
                            and newNodeNexthop != None
                            and list(currentNode.lchild.nexthopSet) == [None]):
                        # print("modify")
                        currentNode.lchild.nexthopSet = set([newNodeNexthop])
                    currentNode = currentNode.lchild
                else:
                    if currentNode.rchild == None:
                        # print("add right count :{0}".format(count))
                        # count += 1
                        currentNode.rchild = newNode
                    elif (currentNode.rchild != None
                            and newNodeNexthop != None
                            and list(currentNode.rchild.nexthopSet) == [None]):
                        # print("modify")
                        currentNode.rchild.nexthopSet = set([newNodeNexthop])
                    currentNode = currentNode.rchild

    # the lowest bit's idx is 0
    def _getBinaryFromBin(self, prefix, idx):
        return (prefix & (0x1 << idx)) >> idx

    def getRoot(self):
        return self.root

    def countRules(self):
        self.nexthopCount = 0
        self.preOrderTraversalToCountNextHop(self.root)
        return self.nexthopCount

    def preOrderTraversalToCountNextHop(self, node):
        # Do Something with node
        if list(node.nexthopSet) not in [[None], [-2]]:
            self.nexthopCount += 1
        if node.lchild != None:
            self.preOrderTraversalToCountNextHop(node.lchild)
        if node.rchild != None:
            self.preOrderTraversalToCountNextHop(node.rchild)

    def countTrieNodes(self):
        self.trieNodeCount = 0
        self.preOrderTraversalToCountTrieNode(self.root)
        return self.trieNodeCount

    def preOrderTraversalToCountTrieNode(self, node):
        # Do Something with node
        self.trieNodeCount += 1
        if node.lchild != None:
            self.preOrderTraversalToCountTrieNode(node.lchild)
        if node.rchild != None:
            self.preOrderTraversalToCountTrieNode(node.rchild)

    def getInherited(self, node):
        parent = node.getParent()
        if parent != None:
            if list(parent.nexthopSet) != [None]:
                return list(parent.nexthopSet)[0]
            else:
                return self.getInherited(parent)
        else:
            print("current node is root")

    def levelAccess(self):
        q = Queue.Queue()
        q.put(self.root)
        while not q.empty():
            currentNode = q.get()
            print("depth: {0}\t" \
                # " current node: {1}\t" \
                # " parent: {2}\t" \
                # " lchild: {3}\t" \
                # " rchild: {4}\t" \
                " nexthopSet: {5}".format(currentNode.depth, currentNode, currentNode.parent, currentNode.lchild, currentNode.rchild, currentNode.nexthopSet))
            if currentNode.lchild != None:
                q.put(currentNode.lchild)
            if currentNode.rchild != None:
                q.put(currentNode.rchild)
