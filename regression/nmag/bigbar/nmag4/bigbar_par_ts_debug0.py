import time
import nmag
from nmag import SI,mesh
import os,sys

execfile("../msat.inc")

#import ocaml
#print "DDD SPEEDTEST: ",ocaml.ddd_speedtest_lindholm(939*939*2)

time_total = -time.time()
time_writing = 0.0
time_initialising = -time.time()
mat_Py = nmag.MagMaterial(name="Py",
                          Ms=SI(M_SAT,"A/m"),
                          exchange_coupling=SI(13.0e-12, "J/m"),
                          llg_gamma_G=SI(0.2211e6, "m/A s"),
                          # llg_damping=SI(0,"")
                          )


distrib=None

if ocaml.petsc_is_mpi():
    print "MPI!"
    print "NODES: ",ocaml.petsc_mpi_nr_nodes()
    sys.stdout.flush()
    if ocaml.petsc_mpi_nr_nodes()==2:
        distrib=[1059,1058]
    else:
        error("This example can only run in single-CPU mode or on two machines!")


sim = nmag.Simulation()

meshfile = "bar_sorted.nmesh.h5"

sim.load_mesh(meshfile, [("Py", mat_Py)],unit_length=SI(1e-9,"m"),distrib=distrib)

print sim.get_timers()

import math
angle_deg = 45
angle_rad = angle_deg/360.*2*math.pi
sim.set_m([math.cos(angle_rad), 0, math.sin(angle_rad)])

sim.save_data(fields='all')

sim._fields._dependencies.make("lam_m") #make sure distributed m-vector is
                                #up-to-date as distributed timestepper
                                #initialises itself from the
                                #distributed physical primary vector(s)

ocaml.linalg_machine_initialize_timestepper(sim._lam,'timestepper',0.0,2.7e-5,2.7e-5)
ocaml.linalg_machine_advance_timestepper(sim._lam,'timestepper',10.,1000)

sim._fields._to_mbuf_copier("m")
sim._fields._dependencies.invalidate("lam_m")


sim.save_data(fields='all')




if False:

    sim.set_params(ts_rel_tol=2.7e-05 , ts_abs_tol=2.7e-05)

    dt = SI(5e-12, "s")

    time_initialising += time.time()
    time_loop = -time.time()
    for i in range(0, 61):
    #for i in range(0, 5):
        time_ = dt*i
        print "Time spent so far %g" % (time_total+time.time())
        target_time = sim.advance_time(time_)

        time_writing -= time.time()
        if i % 10 == 0:
            sim.save_data(fields='all')
        else:
            sim.save_data()
        time_writing += time.time()

    time_loop += time.time()


    time_total += time.time()
    time_simulating = time_loop - time_writing
    print "Setup took %g seconds" % time_initialising
    print "Simulation loop took %g seconds" % time_loop
    print "Writing data took: %g seconds" % time_writing
    print "Timestepper took: %g seconds" % time_simulating
    print "Total time: %g seconds" % time_total

    def out(line, header=False, file="bigbar_timings.log"):
        import os
        if header and os.path.exists(file): return
        f = open(file, "a")
        f.write(line)
        f.close()

    import commands
    host = commands.getoutput("uname -n")
    date = time.asctime()
    rev = "$Revision: 4438 $"[11:-2] #This file's version
    import nsim
    import nsim.svnversion
    rev = nsim.svnversion.svnversion #global version -> more useful
    out("# Timings for the bigbar unit test\n" \
        "# host\t Rev\t date sim\t init\t writing-data\t sim&writing-data\t total\tRev\n", header=True)
    out("%s \t%s \t%s \t%g \t%g \t%g \t%g \t%g\n" % (host, rev, date,time_simulating, time_initialising, time_writing, time_loop, time_total))

    print sim.get_timers()
