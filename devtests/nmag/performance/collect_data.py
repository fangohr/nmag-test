import sys, os

from mesh_gen import get_meshinfo

filenames = sys.argv[1:]
ref_filename = filenames[0]
filenames.sort()

def to_num(s):
    if '.' in s:
        return float(s)
    else:
        return int(s)

def extract_data(filename):
    f = open(filename, "r")
    lines = f.read().splitlines()
    table = [[to_num(x) for x in l.split()]
             for l in lines[1:]]
    f.close()
    return table

def extract_header(filename):
    f = open(filename, "r")
    h = f.read().splitlines()[0]
    f.close()
    return h

def write_data(filename, data, header=""):
    f = open(filename, "w")
    f.write(header +
            "\n".join([" ".join([str(c) for c in cols]) for cols in data]))
    f.close()

ref_data = extract_data(ref_filename)
header = extract_header(ref_filename) + "\n"

whole_data = [] # whole_data[nr_cpus][mesh_nr][simulation_section_nr]

for filename in filenames:
    data = extract_data(filename)
    out_data = [[float(x)/ref_x for x, ref_x in zip(row, ref_row)]
                for row, ref_row in zip(data, ref_data)]
    whole_data.append(out_data)
    write_data("rel_" + filename, out_data, header=header)

meshinfo = get_meshinfo()

heading = header.split()
nr_meshes = len(whole_data[0])
nr_sects = len(whole_data[0][0])
nr_cpus = len(whole_data)

for sec in range(nr_sects):
    h = heading[sec]
    if h.startswith("num"): continue

    f = open("sec-%s.dat" % h, "w")
    for mesh in range(nr_meshes):
        for cpu in range(nr_cpus):
            nr_nodes = meshinfo[mesh]
            speedup = 1.0/whole_data[cpu][mesh][sec]
            f.write("%s %s %s %s\n" % (mesh, nr_nodes, cpu + 1, speedup))
        f.write("\n")
    f.close()

# Generate tables
f = open("tables.txt", "w")
tab = ""
for sec in range(nr_sects):
    h = heading[sec]
    if h.startswith("num"): continue

    tab = "|    "
    for mesh in range(nr_meshes):
        nr_nodes = meshinfo[mesh]
        tab += "|_.%6s" % nr_nodes
    tab += "|\n"

    for cpu in range(nr_cpus):
        tab += "|_.%2d" % (cpu + 1)
        for mesh in range(nr_meshes):
            speedup = 1.0/whole_data[cpu][mesh][sec]
            tab += "|%8.2f" % speedup
        tab += "|\n"

    f.write("Table for %s:\n\n" % h)
    f.write(tab + "\n")
f.close()
