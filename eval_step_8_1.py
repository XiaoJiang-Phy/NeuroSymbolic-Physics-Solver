import sympy as sp
import mpmath as mp

# Set high precision
mp.mp.dps = 50

# Define symbolic variables
a = sp.symbols('a', positive=True)

# The antiderivative expression from the theorist
I_expr = sp.pi/2 * (1 - sp.exp(-a))

# Convert to mpmath function for high-precision evaluation
I_func = sp.lambdify(a, I_expr, modules='mpmath')

# Use the FIRST parameter value from the problem definition
# Since no specific parameter list is provided, we'll use a=1 as a test case
# In practice, this would be replaced with the first value from the parameters list
a_val = mp.mpf('1.0')

# Evaluate the expression
result = I_func(a_val)

# Print the final numerical result as the last line
print(result)