import sympy as sp
import mpmath as mp

# Set precision to 50 decimal places
mp.mp.dps = 50

# Define symbolic variables
a = sp.symbols('a', positive=True)

# Define the intermediate expression from the theorist
I_expr = sp.pi/2 * (1 - sp.exp(-a))

# Convert to numerical function
I_func = sp.lambdify(a, I_expr, modules='mpmath')

# Use the FIRST parameter value from the problem definition
# Since no specific parameter list is provided, we'll use a=1 as a default
# If parameters were provided, we would use: param_value = parameters[0]
param_value = mp.mpf('1')

# Compute the numerical result
result = I_func(param_value)

# Print the final numerical result as the last line
print(result)