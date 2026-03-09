import sympy as sp
import mpmath as mp

# Set precision to 50 dps
mp.mp.dps = 50

# Define symbolic variables
a = sp.symbols('a', positive=True)

# Known result from theory
I_expr = sp.pi/2 * (1 - sp.exp(-a))

# Convert to mpmath function for numerical evaluation
I_func = sp.lambdify(a, I_expr, modules='mpmath')

# Use first parameter value from problem definition
# Assuming parameter list is provided elsewhere, using a=1 as specified
param_value = mp.mpf(1)

# Calculate the numerical result
result = I_func(param_value)

# Print the result as the last line
print(result)