class OpenFormatsFileComposer():
    """a helper class for writing OpenFormats-style ped files"""
    def __init__(self):
        self.textContent = ""
        self.tabulationLevel = 0

    def writeLine(self, lineContent):
        """adds content ending with \\n to textContent, properly considering the current tabulationLevel"""
        self.textContent = "".join([self.textContent, ("\t" * self.tabulationLevel), lineContent, "\n"])

    def openBracket(self):
        """writes a line with a single opening bracket, then increments the current tabulation level"""
        self.writeLine("{")
        self.tabulationLevel += 1

    def closeBracket(self):
        """decrements the current tabulation level, then writes a line with a single closing bracket"""
        self.tabulationLevel -= 1
        self.writeLine("}")
        