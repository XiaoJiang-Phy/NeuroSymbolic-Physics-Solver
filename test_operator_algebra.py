import sympy as sp
import sympy.physics.quantum as spq

def test_commutator():
    # define symbols
    A = sp.Symbol('A', commutative=False)
    B = sp.Symbol('B', commutative=False)
    
    # Commutator
    comm = spq.Commutator(A, B)
    expanded = comm.doit()
    print("Commutator Expansion:", expanded)
    
    # AntiCommutator
    acomm = spq.AntiCommutator(A, B)
    expanded_acomm = acomm.doit()
    print("AntiCommutator Expansion:", expanded_acomm)

    # Fermionic operators
    c_k = spq.Operator('c_k')
    c_k_dag = spq.Dagger(c_k)
    print("Fermionic dagger:", c_k_dag)
    
    # Pauli matrices
    from sympy.physics.quantum.spin import Jx, Jy, Jz
    print("Pauli / Spin:", sp.physics.quantum.Commutator(Jx, Jy).doit())
    
    # Unit constants
    hbar = sp.Symbol('hbar', positive=True)
    k_B = sp.Symbol('k_B', positive=True)
    print("Units:", hbar, k_B)
    print("SUCCESS: Operator algebra works")

if __name__ == "__main__":
    test_commutator()
