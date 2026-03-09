import sympy as sp
import mpmath as mp

# Set high precision
mp.mp.dps = 50

# Define symbolic variable
a = sp.symbols('a', positive=True)

# Closed-form expression from boundary condition analysis
I_expr = sp.pi/2 * (1 - sp.exp(-a))

# Convert to mpmath function for high-precision evaluation
def I_mp(a_val):
    return mp.pi/2 * (1 - mp.e**(-a_val))

# Problem parameters - using FIRST value only
parameters = [1.0]  # Using first parameter value
param_val = parameters[0]

# Evaluate at given parameter
result = I_mp(param_val)

# Print final numerical result as last line
print(f'{result}')
