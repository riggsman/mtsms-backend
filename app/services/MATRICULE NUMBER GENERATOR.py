from datetime import datetime

class MatriculeGenerator:
    def __init__(self, tenant_initial=None, branch_initial=None, program_initial=None, year=None, last_generated=0):
        self.tenant_initial = tenant_initial
        self.branch_initial = branch_initial
        self.program_initial = program_initial
        self.year = year if year else datetime.now().year
        self.last_generated = last_generated

    def _format_year(self):
        """Return last two digits of year"""
        return str(self.year)[-2:]

    def _next_value(self):
        """Increment and return next value"""
        self.last_generated += 1
        return str(self.last_generated).zfill(4)  # padded like 0001

    def generate(self):
        parts = []

        if self.tenant_initial:
            parts.append(self.tenant_initial.upper())

        if self.branch_initial:
            parts.append(self.branch_initial.upper())

        parts.append(self._format_year())

        if self.program_initial:
            parts.append(self.program_initial.upper())

        parts.append(self._next_value())

        return "-".join(parts)


# # =====================
# # Example Usage
# # =====================
# if __name__ == "__main__":
#     generator = MatriculeGenerator(
#         tenant_initial="RUI",
#         branch_initial="K",
#         program_initial="E",
#         year=2026,
#         last_generated=15
#     )

#     for _ in range(5):
#         print(generator.generate())