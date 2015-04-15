from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import pyqtSignal, QPoint, QSize, Qt, QCoreApplication, QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QMessageBox, QSlider, QLabel, QPushButton, QWidget, QDialog, QMainWindow, QFileDialog, QLineEdit, QSpacerItem, QListWidgetItem)

class Highlighter(QtGui.QSyntaxHighlighter):
    def __init__(self, parent=None):
        super(Highlighter, self).__init__(parent)

        self.highlightingRules = []



        numberFormat = QtGui.QTextCharFormat()
        numberFormat.setForeground(QColor(174,129,255))
        numberFormat.setFontWeight(QtGui.QFont.Bold)

        self.highlightingRules.append((QtCore.QRegExp("[0-9]+"),
                numberFormat))

        classFormat = QtGui.QTextCharFormat()
        classFormat.setFontWeight(QtGui.QFont.Bold)
        classFormat.setForeground(QtCore.Qt.magenta)
        self.highlightingRules.append((QtCore.QRegExp("\\bQ[A-Za-z]+\\b"),
                classFormat))

        singleLineCommentFormat = QtGui.QTextCharFormat()
        singleLineCommentFormat.setForeground(QtCore.Qt.red)
        self.highlightingRules.append((QtCore.QRegExp("//[^\n]*"),
                singleLineCommentFormat))

        self.multiLineCommentFormat = QtGui.QTextCharFormat()
        self.multiLineCommentFormat.setForeground(QtCore.Qt.red)

        quotationFormat = QtGui.QTextCharFormat()
        quotationFormat.setForeground( QColor(230,219,116) )
        self.highlightingRules.append((QtCore.QRegExp("\".*\""),
                quotationFormat))

        functionFormat = QtGui.QTextCharFormat()
        functionFormat.setFontItalic(True)
        functionFormat.setForeground( QColor(253,151,31) )
        self.highlightingRules.append((QtCore.QRegExp("\\b[A-Za-z0-9_]+(?=\\()"),
                functionFormat))

        keywordFormat = QtGui.QTextCharFormat()
        keywordFormat.setForeground(QColor(249,38,114))
        keywordFormat.setFontWeight(QtGui.QFont.Bold)

        keywordPatterns = ["\\bclass\\b","\\bdef\\b","\\bsuper\\b",
        "\\bNone\\b","\\bFalse\\b","\\bTrue\\b","\\bself\\b","\\breturn\\b",
        "\\blambda\\b","\\bprint\\b","\\bformat\\b",
        "\\bif\\b","\\belse\\b","\\belif\\b","\\bline\\b",
        "\\bline_to\\b","\\bcircle\\b","\\barc\\b","\\barc_to\\b",
        "\\bpocket\\b","\\bsquare\\b","\\btriangle\\b",]
        
        for pattern in keywordPatterns:
            self.highlightingRules.append( (QtCore.QRegExp(pattern), keywordFormat) )

        self.highlightingRules.append((QtCore.QRegExp("[\\-\\+=%\\/]+"),
                keywordFormat))

        self.commentStartExpression = QtCore.QRegExp("/\\*")
        self.commentEndExpression = QtCore.QRegExp("\\*/")

    def highlightBlock(self, text):
        for pattern, format in self.highlightingRules:
            expression = QtCore.QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)

        self.setCurrentBlockState(0)

        startIndex = 0
        if self.previousBlockState() != 1:
            startIndex = self.commentStartExpression.indexIn(text)

        while startIndex >= 0:
            endIndex = self.commentEndExpression.indexIn(text, startIndex)

            if endIndex == -1:
                self.setCurrentBlockState(1)
                commentLength = len(text) - startIndex
            else:
                commentLength = endIndex - startIndex + self.commentEndExpression.matchedLength()

            self.setFormat(startIndex, commentLength,
                    self.multiLineCommentFormat)
            startIndex = self.commentStartExpression.indexIn(text,
                    startIndex + commentLength);