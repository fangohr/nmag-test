import math
from nsim.model import *
import nmesh
from nmag import MagMaterial

mu0 = 4e-7*math.pi

# Constants and fields
def m0(r):
    x, y, z = [xi*1e9 for xi in r]
    v = [x, y + 10, z + 25.0]
    nv = sum([xi*xi for xi in v])**0.5
    return [xi/nv for xi in v]
m = SpaceField("m", [3], subfields=True, value=Value(m0, 1.0))
M_sat = Constant("M_sat", subfields=True, value=Value(0.86e6))
gamma_GG = Constant("gamma_GG", subfields=True, value=Value(2.210173e5))
alpha = Constant("alpha", subfields=True, value=Value(0.2))
norm_coeff = Constant("norm_coeff", subfields=True, value=Value(0.1e12))
A = 13e-12 # Exchange coupling constant
C = Constant("C", subfields=True, value=Value(-2*A/(mu0*0.86e6) * 1e18))
H_ext = SpaceField("H_ext", [3], value=Value([0, 0, 1.0e5]))
dmdt = SpaceField("dmdt", [3], subfields=True)
H_exch = SpaceField("H_exch", [3], subfields=True)
H_tot = SpaceField("H_tot", [3], subfields=True)

# Operators
op_exch = Operator("exch", "C*<d/dxj H_exch(k)||d/dxj m(k)>, j:3,  k:3")

# Equation for the effective field H_tot
eq_H_tot = Equation("H_tot", "%range i:3; H_tot(i) <- H_ext(i) + H_exch(i);")

# Equation of motion
llg = Equation("llg", """
%range i:3, j:3, k:3, p:3, q:3;
dmdt(i) <- (-gamma_GG/(1 + alpha*alpha))*(eps(i,j,k)*m(j)*H_tot(k) +
           alpha*eps(i,j,k)*m(j)*eps(k,p,q)*m(p)*H_tot(q)) +
           norm_coeff*(1.0 - m(j)*m(j))*m(i);""")

# Equation for the Jacobian: we omit the third term on the RHS
llg_jacobi = Equation("llg-jacobi", """
%range i:3, j:3, k:3, p:3, q:3;
dmdt(i) <- (-gamma_GG/(1 + alpha*alpha))*(eps(i,j,k)*m(j)*H_tot(k) +
           alpha*eps(i,j,k)*m(j)*eps(k,p,q)*m(p)*H_tot(q));""")

# Timestepper
ts = Timestepper("ts_llg", x='m', dxdt='dmdt',
                 eq_for_jacobian=llg_jacobi, derivatives=[(H_tot, op_exch)])

ts.pc_rtol = 1e-2
ts.pc_atol = 1e-7
ts.rtol = 1e-6
ts.atol = 1e-6

# Put everything together in a physical model
mesh = nmesh.load("mesh.nmesh.h5")
region_materials = [[], ["Py"]]
p = Model("mumag", mesh, 1e-9, region_materials)
p.add_quantity([alpha, gamma_GG, C, norm_coeff,
                m, H_exch, H_ext, H_tot, dmdt])
p.add_computation([op_exch, llg, eq_H_tot])
p.add_timestepper(ts)
p.build()

ts.initialise(rtol=ts.rtol, atol=ts.atol)
# Now we can use the model
f = open("model.dat", "w")
f.write("%g " % 0 + "%g %g %g\n" % tuple(m.compute_average().as_float()))
for i in range(1, 101):
  t = i*10e-12
  ts.advance_time(t)
  f.write("%g " % t + "%g %g %g\n" % tuple(m.compute_average().as_float()))
  vm = m.compute_average().as_float()
  print sum([mi*mi for mi in vm])**0.5

print "Number of steps", ts.get_num_steps()
f.close()
