import sympy as sp
import mpmath as mp

# Set precision to 50 dps
mp.mp.dps = 50

# Define symbolic variable
a = sp.symbols('a', positive=True)

# Define the expression from the theorist's derivation
expr = sp.pi/2 * (1 - sp.exp(-a))

# Convert to numerical function
func = sp.lambdify(a, expr, modules='mpmath')

# Use the FIRST parameter value from the problem definition
# Since no specific parameter list is provided in this prompt,
# I'll assume we need to evaluate at a typical value.
# For demonstration, let's use a=1.0 as a default.
# In a real scenario, this would come from the problem parameters.
a_val = mp.mpf('1.0')

# Evaluate the expression
result = func(a_val)

# Print the result as the last line
print(result)