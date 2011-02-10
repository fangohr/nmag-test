import os
import sys
import math

import nmag
from nmag import SI, every, at
from nsim.si_units.si import Oe, degrees_per_ns

ps = SI(1e-12, "s")
Hz = 1/SI("s")
GHz = 1e9*Hz

args = sys.argv

H_strength = 10100*Oe
m0 = [1, 0, 0]

if "par" in args:
  prefix = "par-"
  bias_H = [H_strength, 0*Oe, 0*Oe]
  pulse = [0.0, 1.0, 0.0]

elif "orty" in args:
  prefix = "orty-"
  bias_H = [0*Oe, H_strength, 0*Oe]
  pulse = [1.0, 0.0, 0.0]

elif "ortz" in args:
  prefix = "ortz-"
  bias_H = [0*Oe, 0*Oe, H_strength]
  pulse = [1.0, 0.0, 0.0]

else:
  print("Usage:\n"
        "  nsim a.py --clean par\n"
        "  nsim a.py --clean orty\n"
        "  nsim a.py --clean ortz\n")
  sys.exit(1)

gaussian_amplitude = 100*Oe
gaussian_FWHM = 10*ps
gaussian_sigma = gaussian_FWHM/(2.0*math.sqrt(2.0*math.log(2.0)))
gaussian_t0 = 5*gaussian_sigma
gaussian_x0 = 500.0e-9

sinc_t0 = 0*ps
sinc_omega = 250*GHz * 2*math.pi

relaxed_start_file=prefix+'relaxed.h5'

def setup_simulation(name, damping, demag_tol=1.0, pc_tol=1.0, use_hlib=False):
    mat_Py = nmag.MagMaterial(name="Py",
                              Ms=SI(0.8e6,"A/m"),
                              exchange_coupling=SI(13.0e-12, "J/m"),
                              llg_damping=damping,
                              llg_gamma_G=SI(0.221e6, "m/A s")) #1.846730172e7*Hz/Oe)
    ksp_tols = {"DBC.rtol":1e-5*demag_tol,
                "DBC.atol":1e-5*demag_tol,
                "DBC.maxits":1000000,
                "NBC.rtol":1e-5*demag_tol,
                "NBC.atol":1e-5*demag_tol,
                "NBC.maxits":1000000,
                "PC.rtol":1e-2*pc_tol,
                "PC.atol":1e-7*pc_tol,
                "PC.maxits":1000000}
    phi_BEM = nmag.default_hmatrix_setup if use_hlib else None
    sim = nmag.Simulation(prefix+name, ksp_tolerances=ksp_tols,
                          phi_BEM=phi_BEM)

    sim.load_mesh("nanowire.nmesh.h5",
                  [("Py", mat_Py)],
                  unit_length=SI(1e-9, "m"))

    sim.set_H_ext(bias_H)
    return sim

# Relaxation
if not os.path.exists(relaxed_start_file):
    sim = setup_simulation("relax", 1.0)
    sim.set_m(m0)
    sim.set_params(stopping_dm_dt=0.01*degrees_per_ns,
                   ts_rel_tol=1e-7, ts_abs_tol=1e-7)
    sim.relax()
    sim.save_data(fields='all')
    sim.save_restart_file(relaxed_start_file)
    sys.exit(0)

# Dynamics
sim = setup_simulation("dyn", 0.0)
sim.load_m_from_h5file(relaxed_start_file)

# Here we update the time dependent field
def update_H_ext(t_su):
    t = ps*t_su
    ut = float(sinc_omega*(t - sinc_t0))
    #amplitude = math.exp(-0.5*float((t - gaussian_t0)/gaussian_sigma)**2)
    amplitude = math.sin(ut)/ut if abs(ut) > 1e-10 else 1.0
    amp = [amplitude*pi for pi in pulse]

    H = [float(Hi/gaussian_amplitude) for Hi in bias_H]
    # ^^^ this is a technicality: functions have to return pure numbers.
    #     H_setter returns the field in units of gaussian_amplitude.
    #     We then compute H, the float components in such units.

    def H_setter(r):
        x, y, z = r
        return ([H[0] + amp[0], H[1] + amp[1], H[2] + amp[2]]
                if abs(x - gaussian_x0) < 5.0e-9 else H)
        # ^^^ apply the pulse only to the first dot

    H_value = H_setter if abs(amplitude) > 1e-4 else H
    # ^^^ to speed up things

    fieldname = 'H_ext'
    sim._fields.set_subfield(None, # subfieldname
                             H_value,
                             gaussian_amplitude,
                             fieldname=fieldname,
                             auto_normalise=False)
    (mwe, field) = sim._master_mwes_and_fields_by_name[fieldname]
    ocaml.lam_set_field(sim._lam, field, "v_" + fieldname)
    print "*",

sim.pre_rhs_funs.append(update_H_ext)

sim.set_params(stopping_dm_dt=0) # Never stop for convergence
sim.relax(save=[#('averages', every('time', 2.5*ps)),
                ('field_m', every('time', 2*ps))],
          do=[('exit', at('stage_time', 5000*ps))])
