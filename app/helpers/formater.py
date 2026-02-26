
class Format_Helper:
    def __init__(self,_input_string:str):
        self.input_string = _input_string

    def replace_space_with_underscore(self) -> str:
        """
        Replaces all spaces in the input string with underscores.

        Args:
            input_string (str): The input string containing spaces.

        Returns:
            str: The string with spaces replaced by underscores.
        """
        return self.input_string.replace(" ", "_")
    
    def capitalize_word(self) -> str:
       return self.input_string.upper()
