import sympy as sp
import mpmath as mp

# Set precision to 50 dps
mp.mp.dps = 50

# Define the symbolic expression
pi = sp.pi
a = sp.symbols('a', real=True)
expr = pi/2 * (1 - sp.exp(-a))

# Convert to mpmath function for high-precision evaluation
expr_mp = sp.lambdify(a, expr, modules='mpmath')

# Use the FIRST parameter value from the problem definition
parameter_value = 0.0

# Evaluate at a = 0
result = expr_mp(parameter_value)

# Print the final numerical result as the last line
print(result)