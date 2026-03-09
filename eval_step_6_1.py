import sympy as sp
import mpmath as mp

# Set precision to 50 dps
mp.mp.dps = 50

# Define symbolic variable
a = sp.symbols('a', positive=True)

# Define the closed-form expression from the algebraic substitution
I_expr = sp.pi/2 - sp.pi*sp.exp(-a)/2

# Convert to mpmath function for high-precision evaluation
I_func = sp.lambdify(a, I_expr, modules='mpmath')

# Use the FIRST parameter value from the problem definition
# Assuming the problem provides a list like [1.0, 2.0, 3.0]
# We'll use 1.0 as the first parameter
parameter_value = 1.0

# Evaluate at the parameter value
result = I_func(parameter_value)

# Print the final numerical result as the last line
print(result)