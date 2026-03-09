import sympy as sp
import mpmath as mp

# Set high precision
mp.mp.dps = 50

# Define the symbolic expression from the theorist's derivation
a = sp.symbols('a', positive=True)
I_expr = sp.pi/2 - sp.pi/2 * sp.exp(-a)

# Convert to mpmath function for high-precision evaluation
I_mp = sp.lambdify(a, I_expr, modules='mpmath')

# Use the first parameter value from the problem definition
# Assuming the parameter is provided as a list [a_value]
# For this example, let's assume a = 1.0 (first parameter)
a_value = mp.mpf('1.0')

# Evaluate the integral
result = I_mp(a_value)

# Print the result as the last line
print(result)